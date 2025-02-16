import os
import re
import logging
import asyncio
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET

import requests
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    ContentType,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

###############################################################################
# 1. Загрузка окружения и настройка логов
###############################################################################
load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID", "0"))
# Ссылка на YML-фид (меняется при необходимости)
YML_URL = "https://ion-master.ru/index.php?route=extension/feed/yaoexport"

logging.basicConfig(level=logging.INFO)

###############################################################################
# 2. Глобальные структуры
###############################################################################
# Для каждого пользователя храним телефон и выбранный товар (если оформляет заказ)
#   user_data[user_id] = {
#       "phone": Optional[str],
#       "selected_item": Optional[Dict[str, Any]]
#   }
user_data: Dict[int, Dict[str, Any]] = {}

# Список корневых категорий (те, у которых нет родителя)
categories_tree: List[Dict[str, Any]] = []

# Словарь для поиска категорий по ID
cat_by_id: Dict[str, Dict[str, Any]] = {}

###############################################################################
# 3. Парсинг YML-фида
###############################################################################
def parse_yml_feed(url: str) -> None:
    """
    Скачивает и парсит YML-фид по ссылке:
      1) Читает <categories> (id, parentId, name)
      2) Читает <offers> (привязка к categoryId)
    Заполняет глобальные переменные:
      - categories_tree (список корневых категорий)
      - cat_by_id (словарь id->категория)
    """

    global categories_tree, cat_by_id

    # Очищаем структуры, чтобы не накапливать старые данные
    categories_tree = []
    cat_by_id.clear()

    # 1. Скачивание
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Ошибка загрузки YML-фида: {e}")
        return

    # 2. Парсинг XML
    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        logging.error(f"Ошибка парсинга XML: {e}")
        return

    shop_el = root.find('shop')
    if shop_el is None:
        logging.error("Не найден тег <shop> в YML.")
        return

    cats_el = shop_el.find('categories')
    offers_el = shop_el.find('offers')
    if cats_el is None or offers_el is None:
        logging.error("Не найдены <categories> или <offers> в YML.")
        return

    # 3. Считываем категории
    for cat_el in cats_el.findall('category'):
        cat_id = cat_el.get('id', '').strip()
        parent_id = cat_el.get('parentId')
        cat_name = (cat_el.text or "No name").strip()

        cat_by_id[cat_id] = {
            "id": cat_id,
            "name": cat_name,
            "parent_id": parent_id,
            "children": [],
            "items": []
        }

    # Связываем parent->children
    for c_id, cat in cat_by_id.items():
        pid = cat["parent_id"]
        if pid and pid in cat_by_id:
            cat_by_id[pid]["children"].append(cat)
        else:
            # Если нет родителя или он не найден, это корневая категория
            categories_tree.append(cat)

    # 4. Считываем товары (offers)
    for offer_el in offers_el.findall('offer'):
        off_id = offer_el.get('id', '')
        available_str = offer_el.get('available', 'false')
        is_available = (available_str.lower() == 'true')

        name_el = offer_el.find('name')
        price_el = offer_el.find('price')
        vend_el = offer_el.find('vendorCode')
        cat_id_el = offer_el.find('categoryId')

        name_val = name_el.text if (name_el is not None and name_el.text) else "No name"
        price_val = float(price_el.text) if (price_el is not None and price_el.text) else 0.0
        vendor_val = vend_el.text if (vend_el is not None and vend_el.text) else ""
        c_id = cat_id_el.text if (cat_id_el is not None and cat_id_el.text) else ""

        item = {
            "id": off_id,
            "name": name_val,
            "price": price_val,
            "available": is_available,
            "vendorCode": vendor_val
        }

        # Добавляем товар в соответствующую категорию (если она есть)
        if c_id in cat_by_id:
            cat_by_id[c_id]["items"].append(item)

###############################################################################
# 4. Вспомогательные функции
###############################################################################
def ensure_user_data(user_id: int) -> Dict[str, Any]:
    """
    Инициализирует запись для пользователя, если её нет, и возвращает словарь состояния.
    """
    if user_id not in user_data:
        user_data[user_id] = {
            "phone": None,
            "selected_item": None
        }
    return user_data[user_id]

def find_item_by_id(item_id: str) -> Optional[Dict[str, Any]]:
    """
    Ищет товар по всем категориям и подкатегориям по полю 'id'.
    """
    for cat_id, cat in cat_by_id.items():
        for it in cat["items"]:
            if it["id"] == item_id:
                return it
    return None

def find_category_by_id(cat_id: str) -> Optional[Dict[str, Any]]:
    """
    Быстрый доступ к категории из словаря cat_by_id.
    """
    return cat_by_id.get(cat_id)

def shorten_text(text: str, max_len: int = 60) -> str:
    """
    Сокращает строку, если она длиннее max_len, добавляя '...'.
    """
    txt = text.strip()
    return txt if len(txt) <= max_len else (txt[:max_len - 3].strip() + "...")

###############################################################################
# 5. Инициализация бота (aiogram)
###############################################################################
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

###############################################################################
# 5.1 Команда /start
###############################################################################
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """
    1) Парсим (обновляем) YML-фид,
    2) Показываем корневые категории пользователю.
    """
    parse_yml_feed(YML_URL)

    if not categories_tree:
        await message.answer("Категории недоступны или фид пуст.")
        return

    kb = InlineKeyboardMarkup()
    for cat in categories_tree:
        kb.add(InlineKeyboardButton(
            text=cat["name"],
            callback_data=f"cat_{cat['id']}"
        ))

    await message.answer(
        "Здравствуйте! Я бот-магазин. Выберите раздел:",
        reply_markup=kb
    )

###############################################################################
# 5.2 Обработка выбора категории: cat_xxx
###############################################################################
@dp.callback_query(F.data.startswith("cat_"))
async def on_category_callback(callback: CallbackQuery):
    cat_id = callback.data.split("_", 1)[1]
    category = find_category_by_id(cat_id)
    if not category:
        await callback.answer("Категория не найдена.")
        return

    # Если есть подкатегории
    if category["children"]:
        kb = InlineKeyboardMarkup()

        # Кнопки для дочерних категорий
        for child in category["children"]:
            kb.add(InlineKeyboardButton(
                text=child["name"],
                callback_data=f"cat_{child['id']}"
            ))

        # Если в самой категории есть товары, предложим кнопку «Показать товары»
        if category["items"]:
            kb.add(InlineKeyboardButton(
                text=f"Показать товары ({len(category['items'])})",
                callback_data=f"showitems_{cat_id}"
            ))

        await callback.message.edit_text(
            text=f"Раздел: {category['name']}",
            reply_markup=kb
        )
        await callback.answer()

    else:
        # Листовая категория (нет children). Покажем товары напрямую
        if not category["items"]:
            await callback.message.edit_text(f"В категории «{category['name']}» нет товаров.")
            await callback.answer()
            return

        # Удаляем предыдущий список и показываем товары
        await callback.message.delete()
        await send_items_list(callback.message.chat.id, category["items"], category["name"])
        await callback.answer()

###############################################################################
# 5.3 Обработка «Показать товары»: showitems_xxx
###############################################################################
@dp.callback_query(F.data.startswith("showitems_"))
async def on_showitems_callback(callback: CallbackQuery):
    cat_id = callback.data.split("_", 1)[1]
    category = find_category_by_id(cat_id)
    if not category:
        await callback.answer("Категория не найдена.")
        return

    if not category["items"]:
        await callback.answer("В этой категории нет товаров.", show_alert=True)
        return

    await callback.message.delete()
    await send_items_list(callback.message.chat.id, category["items"], category["name"])
    await callback.answer()

###############################################################################
# 5.4 Функция отправки списка товаров
###############################################################################
async def send_items_list(chat_id: int, items: List[Dict[str, Any]], cat_name: str):
    """
    Отправляет товары по одному сообщению на товар + кнопку «Заказать».
    В конце — кнопка «Связаться с менеджером».
    """
    for it in items:
        short_name = shorten_text(it["name"])
        price_str = f"{it['price']:.2f}"
        avail_str = "В наличии" if it["available"] else "Нет в наличии"
        vendor_str = it["vendorCode"] or "—"

        text_msg = (
            f"<b>{short_name}</b>\n"
            f"Цена: {price_str}₽\n"
            f"Наличие: {avail_str}\n"
            f"Код: {vendor_str}"
        )
        kb_item = InlineKeyboardMarkup()
        kb_item.add(InlineKeyboardButton("Заказать", callback_data=f"order_{it['id']}"))

        await bot.send_message(
            chat_id,
            text=text_msg,
            parse_mode="HTML",
            reply_markup=kb_item
        )

    kb_final = InlineKeyboardMarkup()
    kb_final.add(InlineKeyboardButton("Связаться с менеджером", callback_data="contact_manager"))

    await bot.send_message(
        chat_id,
        text=(
            f"Всего товаров в «{cat_name}»: {len(items)}\n"
            "Чтобы оформить заказ, нажмите «Заказать» под нужным товаром\n"
            "или свяжитесь с менеджером:"
        ),
        reply_markup=kb_final
    )

###############################################################################
# 5.5 «Заказать» товар (order_xxx)
###############################################################################
@dp.callback_query(F.data.startswith("order_"))
async def on_order_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    item_id = callback.data.split("_", 1)[1]

    item = find_item_by_id(item_id)
    if not item:
        await callback.answer("Товар не найден.")
        return

    state = ensure_user_data(user_id)
    state["selected_item"] = item

    # Если телефон уже есть — оформляем заказ сразу
    if state["phone"]:
        await finalize_order(user_id, callback.message)
        await callback.answer("Ваш заказ оформлен!")
    else:
        # Просим контакт
        await callback.answer()
        contact_btn = KeyboardButton(text="Отправить номер телефона", request_contact=True)
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(contact_btn)
        await callback.message.answer(
            text="Пожалуйста, отправьте свой номер телефона, чтобы подтвердить заказ:",
            reply_markup=kb
        )

###############################################################################
# 5.6 «Связаться с менеджером» (contact_manager)
###############################################################################
@dp.callback_query(F.data == "contact_manager")
async def on_contact_manager(callback: CallbackQuery):
    user_id = callback.from_user.id
    state = ensure_user_data(user_id)

    if state["phone"]:
        await callback.answer("У нас уже есть ваш номер, ожидайте связи!")
    else:
        await callback.answer()
        contact_btn = KeyboardButton(text="Отправить номер телефона", request_contact=True)
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(contact_btn)
        await callback.message.answer(
            text="Отправьте номер телефона, чтобы менеджер мог связаться с вами:",
            reply_markup=kb
        )

###############################################################################
# 5.7 Обработка контакта (message.contact)
###############################################################################
@dp.message(F.content_type == ContentType.CONTACT)
async def on_user_contact(message: Message):
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    state = ensure_user_data(user_id)

    state["phone"] = phone_number
    if state["selected_item"]:
        # Завершаем заказ
        await message.answer("Спасибо! Телефон получен. Завершаем заказ...")
        await finalize_order(user_id, message)
    else:
        # Просто контакт (без заказа)
        await message.answer(
            "Спасибо! Ваш номер получен. Менеджер свяжется с вами.",
            reply_markup=ReplyKeyboardMarkup(remove_keyboard=True)
        )
        # Уведомим менеджера
        await bot.send_message(
            chat_id=MANAGER_CHAT_ID,
            text=(
                f"Пользователь @{message.from_user.username or '—'} "
                f"({message.from_user.full_name or '—'}) "
                f"оставил номер: {phone_number}"
            )
        )

###############################################################################
# 5.8 Завершение заказа
###############################################################################
async def finalize_order(user_id: int, msg: Message):
    """
    Формирует сообщение для менеджера, отправляет и сбрасывает выбранный товар у пользователя.
    """
    state = user_data.get(user_id)
    if not state:
        return

    phone = state.get("phone")
    item = state.get("selected_item")
    if not phone or not item:
        return

    text_msg = (
        "Новый заказ!\n"
        f"Телефон: {phone}\n"
        f"Товар: {item['name']}\n"
        f"Цена: {item['price']:.2f}₽\n"
        f"Код: {item['vendorCode'] or '—'}"
    )
    await bot.send_message(MANAGER_CHAT_ID, text_msg)
    state["selected_item"] = None

    await msg.answer(
        "Заказ отправлен менеджеру! Ожидайте связи.\n"
        "Чтобы заказать что-то ещё, введите /start.",
        reply_markup=ReplyKeyboardMarkup(remove_keyboard=True)
    )

###############################################################################
# 5.9 Запуск бота
###############################################################################
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
