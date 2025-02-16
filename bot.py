import os
import re
import logging
import asyncio
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

import requests
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, ContentType,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)

###############################################################################
# 1. Настройка окружения и логирования
###############################################################################
load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
YML_URL = os.getenv("YML_URL", "")  # Если пустое — не используем фид
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID", "0"))

logging.basicConfig(level=logging.INFO)

###############################################################################
# 2. Глобальные структуры: user_data и families
###############################################################################
# user_data: хранит данные по каждому пользователю:
#    user_data[user_id] = {
#       "phone": Optional[str],
#       "selected_item": Optional[Dict[str, Any]]
#    }
user_data: Dict[int, Dict[str, Any]] = {}

# families: хранит список групп (iPhone, Apple Watch и т.д.) и их подгруппы
families: List[Dict[str, Any]] = []

###############################################################################
# 2.1 Функции для парсинга YML-файла (или обращения к сайту)
###############################################################################
def fetch_offers_from_yml(url: str) -> List[Dict[str, Any]]:
    """
    Загружает и парсит YML/XML-файл:
      <yml_catalog>
        <shop>
          <offers>
            <offer id="..." available="true">
              <name>...</name>
              <price>...</price>
              <vendorCode>...</vendorCode>
            </offer>
          </offers>
        </shop>
      </yml_catalog>

    Возвращает список словарей:
      [
        {
          "id": str,
          "name": str,
          "price": float,
          "available": bool,
          "vendorCode": str
        }, ...
      ]
    """
    if not url:
        # Если URL не задан, возвращаем пустой список
        return []

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except (requests.RequestException, ValueError) as e:
        logging.error(f"Не удалось загрузить YML-фид: {e}")
        return []

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as e:
        logging.error(f"Ошибка парсинга XML: {e}")
        return []

    shop_el = root.find('shop')
    if shop_el is None:
        return []

    offers_el = shop_el.find('offers')
    if offers_el is None:
        return []

    offers = []
    for offer_el in offers_el.findall('offer'):
        offer_id = offer_el.get('id', '')
        available_str = offer_el.get('available', 'false')
        is_available = (available_str.lower() == 'true')

        price_el = offer_el.find('price')
        name_el = offer_el.find('name')
        vendor_el = offer_el.find('vendorCode')

        price_val = float(price_el.text) if (price_el is not None and price_el.text) else 0.0
        name_val = name_el.text if name_el is not None else "No name"
        vendor_val = vendor_el.text if vendor_el is not None else ""

        offers.append({
            "id": offer_id,
            "name": name_val,
            "price": price_val,
            "available": is_available,
            "vendorCode": vendor_val,
        })
    return offers

###############################################################################
# 2.2 Функции для формирования групп и подгрупп (со списком товаров)
###############################################################################
def build_iphone_subgroups() -> List[Dict[str, Any]]:
    """
    Каждая подгруппа: {"id", "name", "patterns", "items"}
    patterns: список регулярных выражений, по которым мы ищем в названии товара
    """
    return [
        {
            "id": "iphone_14",
            "name": "iPhone 14",
            "patterns": [r"(?i)\biphone\s*14\b"],
            "items": []
        },
        {
            "id": "iphone_15",
            "name": "iPhone 15",
            "patterns": [r"(?i)\biphone\s*15\b"],
            "items": []
        },
        # Добавьте при необходимости iPhone 11, 12, 13 и т.д.
    ]

def build_apple_watch_subgroups() -> List[Dict[str, Any]]:
    return [
        {
            "id": "aw_series_9",
            "name": "Apple Watch Series 9",
            "patterns": [r"(?i)\bapple\s*watch\s*series\s*9\b"],
            "items": []
        },
        {
            "id": "aw_ultra_2",
            "name": "Apple Watch Ultra 2",
            "patterns": [r"(?i)\bapple\s*watch\s*ultra\s*2\b"],
            "items": []
        },
    ]

def build_ipad_subgroups() -> List[Dict[str, Any]]:
    return [
        {
            "id": "ipad_10",
            "name": "iPad 10",
            "patterns": [r"(?i)\bipad\s*10\b"],
            "items": []
        },
        {
            "id": "ipad_air_5",
            "name": "iPad Air 5",
            "patterns": [r"(?i)\bipad\s*air\s*5\b"],
            "items": []
        },
    ]

def build_macbook_subgroups() -> List[Dict[str, Any]]:
    return [
        {
            "id": "macbook_air_m1",
            "name": "MacBook Air (M1)",
            "patterns": [r"(?i)\bmacbook\s*air\b.*\(m1\)"],
            "items": []
        },
        {
            "id": "macbook_pro_14",
            "name": "MacBook Pro 14",
            "patterns": [r"(?i)\bmacbook\s*pro\s*14\b"],
            "items": []
        },
    ]

def build_jcid_subgroups() -> List[Dict[str, Any]]:
    return [
        {
            "id": "jcid_platy",
            "name": "Платы JCID",
            "patterns": [r"(?i)\bплата\b.*\bjcid\b"],
            "items": []
        },
        {
            "id": "jcid_shleyfa",
            "name": "Шлейфа JCID",
            "patterns": [r"(?i)\bшлейф\b.*\bjcid\b"],
            "items": []
        },
    ]

def build_instrumenty_subgroups() -> List[Dict[str, Any]]:
    return [
        {
            "id": "otvertki",
            "name": "Отвертки",
            "patterns": [r"(?i)\bотвертк(а|и)\b"],
            "items": []
        },
        {
            "id": "pincety",
            "name": "Пинцеты",
            "patterns": [r"(?i)\bпинцет(ы)?\b"],
            "items": []
        },
    ]

def build_all_families() -> List[Dict[str, Any]]:
    """
    Основные группы:
      iPhone
      Apple Watch
      iPad
      MacBook
      Дополнения JCID
      Инструменты
    """
    return [
        {
            "id": "iphone",
            "name": "iPhone",
            "subgroups": build_iphone_subgroups()
        },
        {
            "id": "apple_watch",
            "name": "Apple Watch",
            "subgroups": build_apple_watch_subgroups()
        },
        {
            "id": "ipad",
            "name": "iPad",
            "subgroups": build_ipad_subgroups()
        },
        {
            "id": "macbook",
            "name": "MacBook",
            "subgroups": build_macbook_subgroups()
        },
        {
            "id": "jcid",
            "name": "Дополнения JCID",
            "subgroups": build_jcid_subgroups()
        },
        {
            "id": "instrumenty",
            "name": "Инструменты",
            "subgroups": build_instrumenty_subgroups()
        }
    ]

###############################################################################
# 2.3 Вспомогательные функции для работы с данными
###############################################################################
def shorten_name(name: str, max_length: int = 60) -> str:
    """
    Удаляем лишние пробелы, сокращаем слишком длинные строки.
    При желании можно чистить "(идеал)", "в сборе..." и т.п.
    """
    txt = re.sub(r'\s+', ' ', name).strip()
    if len(txt) > max_length:
        return txt[:max_length - 3].strip() + "..."
    return txt

def ensure_user_data(user_id: int) -> Dict[str, Any]:
    """
    Инициализирует запись в user_data, если её нет,
    и возвращает словарь с полями phone, selected_item.
    """
    if user_id not in user_data:
        user_data[user_id] = {"phone": None, "selected_item": None}
    return user_data[user_id]

def find_item_in_families(item_id: str) -> Optional[Dict[str, Any]]:
    """
    Поиск товара во всех группах/подгруппах по его ID.
    Возвращает словарь-offer или None, если не найден.
    """
    for fam in families:
        for sg in fam["subgroups"]:
            for off in sg["items"]:
                if off["id"] == item_id:
                    return off
    return None

###############################################################################
# 3. Инициализация aiogram
###############################################################################
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

###############################################################################
# 3.1 Команда /start
###############################################################################
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """
    Приветственное сообщение + формирование каталога:
    1. Загружаем товары из YML (или сайта).
    2. Распределяем их по подгруппам.
    3. Показываем кнопки основных групп.
    """
    global families

    # 1) Получаем все товары
    all_offers = fetch_offers_from_yml(YML_URL)

    # 2) Строим семейства (очищаем/инициализируем)
    families = build_all_families()
    for fam in families:
        for sg in fam["subgroups"]:
            sg["items"].clear()

    # 3) Распределяем товары по подгруппам на основе patterns
    for off in all_offers:
        for fam in families:
            for sg in fam["subgroups"]:
                if any(re.search(p, off["name"]) for p in sg["patterns"]):
                    sg["items"].append(off)

    # 4) Формируем инлайн-клавиатуру основных групп
    kb = InlineKeyboardMarkup()
    for fam in families:
        kb.add(InlineKeyboardButton(
            text=fam["name"],
            callback_data=f"fam_{fam['id']}"
        ))

    await message.answer(
        text="Здравствуйте! Я бот-каталог. Выберите нужную группу:",
        reply_markup=kb
    )

###############################################################################
# 3.2 Обработка нажатия на группу: fam_xxx
###############################################################################
@dp.callback_query(F.data.startswith("fam_"))
async def on_family_callback(callback: CallbackQuery):
    """
    Выбор одной из основных групп (iPhone, Apple Watch, и т.д.).
    Показываем подгруппы (модели/серии).
    """
    fam_id = callback.data.split("_", 1)[1]
    chosen_fam = next((f for f in families if f["id"] == fam_id), None)
    if not chosen_fam:
        await callback.answer("Группа не найдена.")
        return

    kb = InlineKeyboardMarkup()
    for sg in chosen_fam["subgroups"]:
        count_items = len(sg["items"])
        kb.add(InlineKeyboardButton(
            text=f"{sg['name']} ({count_items})",
            callback_data=f"sg_{fam_id}_{sg['id']}"
        ))

    await callback.message.edit_text(
        text=f"Вы выбрали: {chosen_fam['name']}\nВыберите подгруппу:",
        reply_markup=kb
    )
    await callback.answer()

###############################################################################
# 3.3 Обработка нажатия на подгруппу: sg_xxx
###############################################################################
@dp.callback_query(F.data.startswith("sg_"))
async def on_subgroup_callback(callback: CallbackQuery):
    """
    Выбор конкретной модели (подгруппы).
    Показываем список товаров (off['name'] ...).
    """
    parts = callback.data.split("_", 2)
    if len(parts) < 3:
        await callback.answer("Ошибка подгруппы.")
        return

    fam_id, sg_id = parts[1], parts[2]
    chosen_fam = next((f for f in families if f["id"] == fam_id), None)
    if not chosen_fam:
        await callback.answer("Группа не найдена.")
        return

    chosen_sg = next((s for s in chosen_fam["subgroups"] if s["id"] == sg_id), None)
    if not chosen_sg:
        await callback.answer("Подгруппа не найдена.")
        return

    items = chosen_sg["items"]
    if not items:
        await callback.message.edit_text(f"В подгруппе '{chosen_sg['name']}' пока нет товаров.")
        await callback.answer()
        return
