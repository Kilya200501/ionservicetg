import os
import re
import logging
import asyncio
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, ContentType,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)

############################
# 1. Загрузка окружения
############################
load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
YML_URL = os.getenv("YML_URL", "")
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID", "0"))
logging.basicConfig(level=logging.INFO)

############################
# 2. Глобальные данные
############################

# user_data[user_id] = {
#    "phone": str | None,
#    "selected_item": dict | None
# }
user_data: Dict[int, Dict[str, Any]] = {}

############################
# 2.1 Функция сокращения названий товара
############################
def shorten_name(original_name: str, max_length=60) -> str:
    """
    Пример «причесывания»:
    1. Удаляем "в сборе с сенсорным стеклом (тачскрин)", "(идеал)" — как пример.
    2. Убираем двойные пробелы.
    3. Если > max_length, обрезаем и ставим '...'.
    """
    text = re.sub(r'в сборе с сенсорным стеклом\s*\(тачскрин\)', '', original_name, flags=re.IGNORECASE)
    text = re.sub(r'\(идеал\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > max_length:
        text = text[:max_length-3].strip() + "..."
    return text

############################
# 2.2 Функция для парсинга YML
############################
def fetch_offers_from_yml(url: str) -> List[Dict[str, Any]]:
    """
    Пример функции, которая:
    1. Скачивает XML/YML-файл по ссылке (requests.get).
    2. Разбирает структуру YML (чаще всего <yml_catalog><shop><offers>).
    3. Возвращает список офферов в виде словарей: 
       [{"id": ..., "name": ..., "price": ..., "available": ..., "vendorCode": ...}, ...]

    Если структура вашего файла иная, скорректируйте пути .find / .findall.
    """
    response = requests.get(url, timeout=10)
    response.raise_for_status()  # Если HTTP-ошибка, выбросит исключение

    # Парсим XML/YML
    root = ET.fromstring(response.text)

    # Ищем <shop> внутри <yml_catalog>
    shop_element = root.find('shop')
    if shop_element is None:
        return []

    # Ищем <offers> внутри <shop>
    offers_element = shop_element.find('offers')
    if offers_element is None:
        return []

    offers = []
    for offer_el in offers_element.findall('offer'):
        offer_id = offer_el.get('id', '')
        available_str = offer_el.get('available', 'false')
        available = (available_str.lower() == 'true')

        price_el = offer_el.find('price')
        name_el = offer_el.find('name')
        vendorcode_el = offer_el.find('vendorCode')

        price = float(price_el.text) if (price_el is not None and price_el.text) else 0.0
        name = name_el.text if name_el is not None else "No name"
        vendor_code = vendorcode_el.text if vendorcode_el is not None else ""

        offer_dict = {
            "id": offer_id,
            "name": name,
            "price": price,
            "available": available,
            "vendorCode": vendor_code
        }
        offers.append(offer_dict)

    return offers


############################
# 3. Определение групп/подгрупп (полные списки)
############################
def build_iphone_subgroups() -> List[Dict[str, Any]]:
    """
    iPhone: от iPhone 16 Pro Max к iPhone 6/6 Plus (полный список, без сокращения).
    """
    return [
        # 16
        {
            "id": "iphone_16_pro_max",
            "name": "iPhone 16 Pro Max",
            "patterns": [r"(?i)\biphone\s*16\s*pro\s*max\b"],
            "items": []
        },
        {
            "id": "iphone_16_pro",
            "name": "iPhone 16 Pro",
            "patterns": [r"(?i)\biphone\s*16\s*pro\b(?!\s*max)"],
            "items": []
        },
        {
            "id": "iphone_16_plus",
            "name": "iPhone 16 Plus",
            "patterns": [r"(?i)\biphone\s*16\s*plus\b"],
            "items": []
        },
        {
            "id": "iphone_16",
            "name": "iPhone 16",
            "patterns": [r"(?i)\biphone\s*16\b(?!\s*pro|plus)"],
            "items": []
        },
        # 15
        {
            "id": "iphone_15_pro_max",
            "name": "iPhone 15 Pro Max",
            "patterns": [r"(?i)\biphone\s*15\s*pro\s*max\b"],
            "items": []
        },
        {
            "id": "iphone_15_pro",
            "name": "iPhone 15 Pro",
            "patterns": [r"(?i)\biphone\s*15\s*pro\b(?!\s*max)"],
            "items": []
        },
        {
            "id": "iphone_15_plus",
            "name": "iPhone 15 Plus",
            "patterns": [r"(?i)\biphone\s*15\s*plus\b"],
            "items": []
        },
        {
            "id": "iphone_15",
            "name": "iPhone 15",
            "patterns": [r"(?i)\biphone\s*15\b(?!\s*pro|plus)"],
            "items": []
        },
        # 14
        {
            "id": "iphone_14_pro_max",
            "name": "iPhone 14 Pro Max",
            "patterns": [r"(?i)\biphone\s*14\s*pro\s*max\b"],
            "items": []
        },
        {
            "id": "iphone_14_pro",
            "name": "iPhone 14 Pro",
            "patterns": [r"(?i)\biphone\s*14\s*pro\b(?!\s*max)"],
            "items": []
        },
        {
            "id": "iphone_14_plus",
            "name": "iPhone 14 Plus",
            "patterns": [r"(?i)\biphone\s*14\s*plus\b"],
            "items": []
        },
        {
            "id": "iphone_14",
            "name": "iPhone 14",
            "patterns": [r"(?i)\biphone\s*14\b(?!\s*pro|plus)"],
            "items": []
        },
        # 13
        {
            "id": "iphone_13_pro_max",
            "name": "iPhone 13 Pro Max",
            "patterns": [r"(?i)\biphone\s*13\s*pro\s*max\b"],
            "items": []
        },
        {
            "id": "iphone_13_pro",
            "name": "iPhone 13 Pro",
            "patterns": [r"(?i)\biphone\s*13\s*pro\b(?!\s*max)"],
            "items": []
        },
        {
            "id": "iphone_13_mini",
            "name": "iPhone 13 mini",
            "patterns": [r"(?i)\biphone\s*13\s*mini\b"],
            "items": []
        },
        {
            "id": "iphone_13",
            "name": "iPhone 13",
            "patterns": [r"(?i)\biphone\s*13\b(?!\s*pro|mini)"],
            "items": []
        },
        # 12
        {
            "id": "iphone_12_pro_max",
            "name": "iPhone 12 Pro Max",
            "patterns": [r"(?i)\biphone\s*12\s*pro\s*max\b"],
            "items": []
        },
        {
            "id": "iphone_12_pro",
            "name": "iPhone 12 Pro",
            "patterns": [r"(?i)\biphone\s*12\s*pro\b(?!\s*max)"],
            "items": []
        },
        {
            "id": "iphone_12_mini",
            "name": "iPhone 12 mini",
            "patterns": [r"(?i)\biphone\s*12\s*mini\b"],
            "items": []
        },
        {
            "id": "iphone_12",
            "name": "iPhone 12",
            "patterns": [r"(?i)\biphone\s*12\b(?!\s*pro|mini)"],
            "items": []
        },
        # 11
        {
            "id": "iphone_11_pro_max",
            "name": "iPhone 11 Pro Max",
            "patterns": [r"(?i)\biphone\s*11\s*pro\s*max\b"],
            "items": []
        },
        {
            "id": "iphone_11_pro",
            "name": "iPhone 11 Pro",
            "patterns": [r"(?i)\biphone\s*11\s*pro\b(?!\s*max)"],
            "items": []
        },
        {
            "id": "iphone_11",
            "name": "iPhone 11",
            "patterns": [r"(?i)\biphone\s*11\b(?!\s*pro)"],
            "items": []
        },
        # X / Xs / Xr
        {
            "id": "iphone_xs_max",
            "name": "iPhone Xs Max",
            "patterns": [r"(?i)\biphone\s*xs\s*max\b"],
            "items": []
        },
        {
            "id": "iphone_xs",
            "name": "iPhone Xs",
            "patterns": [r"(?i)\biphone\s*xs\b(?!\s*max)"],
            "items": []
        },
        {
            "id": "iphone_xr",
            "name": "iPhone Xr",
            "patterns": [r"(?i)\biphone\s*xr\b"],
            "items": []
        },
        {
            "id": "iphone_x",
            "name": "iPhone X",
            "patterns": [r"(?i)\biphone\s*x\b(?!s|r)"],
            "items": []
        },
        # SE
        {
            "id": "iphone_se_2023",
            "name": "iPhone Se 2023",
            "patterns": [r"(?i)\biphone\s*se\s*2023\b"],
            "items": []
        },
        {
            "id": "iphone_se_2022",
            "name": "iPhone Se 2022",
            "patterns": [r"(?i)\biphone\s*se\s*2022\b"],
            "items": []
        },
        {
            "id": "iphone_se_2020",
            "name": "iPhone Se 2020",
            "patterns": [r"(?i)\biphone\s*se\s*2020\b"],
            "items": []
        },
        {
            # 8/8 plus / 7/7 plus / 6/6 plus
            "id": "iphone_8_8_plus",
            "name": "iPhone 8/8 Plus",
            "patterns": [
                r"(?i)\biphone\s*8\s*\+",
                r"(?i)\biphone\s*8\s*plus\b",
                r"(?i)\biphone\s*8\b"
            ],
            "items": []
        },
        {
            "id": "iphone_7_7_plus",
            "name": "iPhone 7/7 Plus",
            "patterns": [
                r"(?i)\biphone\s*7\s*\+",
                r"(?i)\biphone\s*7\s*plus\b",
                r"(?i)\biphone\s*7\b"
            ],
            "items": []
        },
        {
            "id": "iphone_6_6_plus",
            "name": "iPhone 6/6 Plus",
            "patterns": [
                r"(?i)\biphone\s*6\s*\+",
                r"(?i)\biphone\s*6\s*plus\b",
                r"(?i)\biphone\s*6\b"
            ],
            "items": []
        }
    ]

def build_ipad_subgroups() -> List[Dict[str, Any]]:
    """
    Полный списоĸ iPad в порядке, который вы дали: iPad 10, iPad 5, iPad 6 ...
    """
    return [
        {
            "id": "ipad_10",
            "name": "IPad 10",
            "patterns": [r"(?i)\bipad\s*10\b"],
            "items": []
        },
        {
            "id": "ipad_5",
            "name": "IPad 5",
            "patterns": [r"(?i)\bipad\s*5\b"],
            "items": []
        },
        {
            "id": "ipad_6",
            "name": "IPad 6",
            "patterns": [r"(?i)\bipad\s*6\b"],
            "items": []
        },
        {
            "id": "ipad_7",
            "name": "IPad 7",
            "patterns": [r"(?i)\bipad\s*7\b"],
            "items": []
        },
        {
            "id": "ipad_8",
            "name": "IPad 8",
            "patterns": [r"(?i)\bipad\s*8\b"],
            "items": []
        },
        # ... здесь нужно продолжить заполнение подгрупп, 
        # но в примере часть пропущена, будьте аккуратны

        {
            "id": "ipad_9",
            "name": "IPad 9",
            "patterns": [r"(?i)\bipad\s*9\b"],
            "items": []
        },
        {
            "id": "ipad_air_1",
            "name": "IPad Air 1",
            "patterns": [r"(?i)\bipad\s*air\s*1\b"],
            "items": []
        },
        {
            "id": "ipad_air_2",
            "name": "IPad Air 2",
            "patterns": [r"(?i)\bipad\s*air\s*2\b"],
            "items": []
        },
        {
            "id": "ipad_air_3",
            "name": "IPad Air 3",
            "patterns": [r"(?i)\bipad\s*air\s*3\b"],
            "items": []
        },
        {
            "id": "ipad_air_4",
            "name": "IPad Air 4",
            "patterns": [r"(?i)\bipad\s*air\s*4\b"],
            "items": []
        },
        {
            "id": "ipad_air_5",
            "name": "IPad Air 5",
            "patterns": [r"(?i)\bipad\s*air\s*5\b"],
            "items": []
        },
        {
            "id": "ipad_air_m2_11",
            "name": "IPad Air (M2) 11",
            "patterns": [r"(?i)\bipad\s*air\s*\(m2\)\s*11\b"],
            "items": []
        },
        {
            "id": "ipad_air_m2_13",
            "name": "IPad Air (M2) 13",
            "patterns": [r"(?i)\bipad\s*air\s*\(m2\)\s*13\b"],
            "items": []
        },
        {
            "id": "ipad_mini_2",
            "name": "IPad mini 2",
            "patterns": [r"(?i)\bipad\s*mini\s*2\b"],
            "items": []
        },
        {
            "id": "ipad_mini_3",
            "name": "IPad mini 3",
            "patterns": [r"(?i)\bipad\s*mini\s*3\b"],
            "items": []
        },
        {
            "id": "ipad_mini_4",
            "name": "IPad mini 4",
            "patterns": [r"(?i)\bipad\s*mini\s*4\b"],
            "items": []
        },
        {
            "id": "ipad_mini_5",
            "name": "IPad mini 5",
            "patterns": [r"(?i)\bipad\s*mini\s*5\b"],
            "items": []
        },
        {
            "id": "ipad_mini_6",
            "name": "IPad mini 6",
            "patterns": [r"(?i)\bipad\s*mini\s*6\b"],
            "items": []
        },
        {
            "id": "ipad_mini_a17_pro",
            "name": "IPad mini (A17 Pro)",
            "patterns": [r"(?i)\bipad\s*mini\s*\(a17\s*pro\)"],
            "items": []
        },
        {
            "id": "ipad_pro_10_5",
            "name": "IPad Pro 10,5",
            "patterns": [r"(?i)\bipad\s*pro\s*10\.?5\b"],
            "items": []
        },
        {
            "id": "ipad_pro_11_1_gen",
            "name": "IPad Pro 11 (1 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*11\s*\(1\s*gen\)"],
            "items": []
        },
        {
            "id": "ipad_pro_11_2_gen",
            "name": "IPad Pro 11 (2 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*11\s*\(2\s*gen\)"],
            "items": []
        },
        {
            "id": "ipad_pro_11_3_gen",
            "name": "IPad Pro 11 (3 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*11\s*\(3\s*gen\)"],
            "items": []
        },
        {
            "id": "ipad_pro_11_4_gen",
            "name": "IPad Pro 11 (4 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*11\s*\(4\s*gen\)"],
            "items": []
        },
        {
            "id": "ipad_pro_12_9_1_gen",
            "name": "IPad Pro 12.9 (1 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*12\.?9\s*\(1\s*gen\)"],
            "items": []
        },
        {
            "id": "ipad_pro_12_9_2_gen",
            "name": "IPad Pro 12.9 (2 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*12\.?9\s*\(2\s*gen\)"],
            "items": []
        },
        {
            "id": "ipad_pro_12_9_3_gen",
            "name": "IPad Pro 12.9 (3 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*12\.?9\s*\(3\s*gen\)"],
            "items": []
        },
        {
            "id": "ipad_pro_12_9_4_gen",
            "name": "IPad Pro 12.9 (4 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*12\.?9\s*\(4\s*gen\)"],
            "items": []
        },
        {
            "id": "ipad_pro_12_9_5_gen",
            "name": "IPad Pro 12.9 (5 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*12\.?9\s*\(5\s*gen\)"],
            "items": []
        },
        {
            "id": "ipad_pro_12_9_6_gen",
            "name": "IPad Pro 12.9 (6 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*12\.?9\s*\(6\s*gen\)"],
            "items": []
        },
        {
            "id": "ipad_pro_9_7",
            "name": "IPad Pro 9.7",
            "patterns": [r"(?i)\bipad\s*pro\s*9\.?7\b"],
            "items": []
        },
        {
            "id": "ipad_pro_m4_11",
            "name": "IPad Pro (M4) 11",
            "patterns": [r"(?i)\bipad\s*pro\s*\(m4\)\s*11\b"],
            "items": []
        },
        {
            "id": "ipad_pro_m4_13",
            "name": "IPad Pro (M4) 13",
            "patterns": [r"(?i)\bipad\s*pro\s*\(m4\)\s*13\b"],
            "items": []
        },
    ]

def build_apple_watch_subgroups() -> List[Dict[str, Any]]:
    """
    Полный списоĸ Apple Watch, по вашему сообщению...
    """
    return [
        {
            "id": "aw_series_1",
            "name": "Apple Watch Series 1",
            "patterns": [r"(?i)\bapple\s*watch\s*series\s*1\b"],
            "items": []
        },
        {
            "id": "aw_series_10",
            "name": "Apple Watch Series 10",
            "patterns": [r"(?i)\bapple\s*watch\s*series\s*10\b"],
            "items": []
        },
        {
            "id": "aw_series_2",
            "name": "Apple Watch Series 2",
            "patterns": [r"(?i)\bapple\s*watch\s*series\s*2\b"],
            "items": []
        },
        {
            "id": "aw_series_3",
            "name": "Apple Watch Series 3",
            "patterns": [r"(?i)\bapple\s*watch\s*series\s*3\b"],
            "items": []
        },
        {
            "id": "aw_series_4",
            "name": "Apple Watch Series 4",
            "patterns": [r"(?i)\bapple\s*watch\s*series\s*4\b"],
            "items": []
        },
        {
            "id": "aw_series_5",
            "name": "Apple Watch Series 5",
            "patterns": [r"(?i)\bapple\s*watch\s*series\s*5\b"],
            "items": []
        },
        {
            "id": "aw_series_6",
            "name": "Apple Watch Series 6",
            "patterns": [r"(?i)\bapple\s*watch\s*series\s*6\b"],
            "items": []
        },
        {
            "id": "aw_series_7",
            "name": "Apple Watch Series 7",
            "patterns": [r"(?i)\bapple\s*watch\s*series\s*7\b"],
            "items": []
        },
        {
            "id": "aw_series_8",
            "name": "Apple Watch Series 8",
            "patterns": [r"(?i)\bapple\s*watch\s*series\s*8\b"],
            "items": []
        },
        {
            "id": "aw_series_9",
            "name": "Apple Watch Series 9",
            "patterns": [r"(?i)\bapple\s*watch\s*series\s*9\b"],
            "items": []
        },
        {
            "id": "aw_series_se_1",
            "name": "Apple Watch Series SE (1 Gen)",
            "patterns": [r"(?i)\bapple\s*watch\s*series\s*se\s*\(1\s*gen\)"],
            "items": []
        },
        {
            "id": "aw_series_se_2",
            "name": "Apple Watch Series SE (2 Gen)",
            "patterns": [r"(?i)\bapple\s*watch\s*series\s*se\s*\(2\s*gen\)"],
            "items": []
        },
        {
            "id": "aw_ultra",
            "name": "Apple Watch Ultra",
            "patterns": [r"(?i)\bapple\s*watch\s*ultra\b(?!\s*2)"],
            "items": []
        },
        {
            "id": "aw_ultra_2",
            "name": "Apple Watch Ultra 2",
            "patterns": [r"(?i)\bapple\s*watch\s*ultra\s*2\b"],
            "items": []
        }
    ]

def build_jcid_subgroups() -> List[Dict[str, Any]]:
    """
    Дополнение JCID (3 подгруппы).
    """
    return [
        {
            "id": "jcid_platy",
            "name": "Платы JCID",
            "patterns": [
                r"(?i)\bплата\b.*\bjcid\b",
                r"(?i)\bjcid\b.*\bплата\b"
            ],
            "items": []
        },
        {
            "id": "jcid_programmatory_testery",
            "name": "Программаторы/Тестеры JCID",
            "patterns": [
                r"(?i)\bпрограмматор\b.*\bjcid\b",
                r"(?i)\bjcid\b.*\bпрограмматор\b",
                r"(?i)\bтестер\b.*\bjcid\b",
                r"(?i)\bjcid\b.*\bтестер\b"
            ],
            "items": []
        },
        {
            "id": "jcid_shleyfa",
            "name": "Шлейфа JCID",
            "patterns": [
                r"(?i)\bшлейф\b.*\bjcid\b",
                r"(?i)\bjcid\b.*\bшлейф\b"
            ],
            "items": []
        }
    ]

def build_instrumenty_subgroups() -> List[Dict[str, Any]]:
    """
    Инструменты (18 подгрупп).
    """
    return [
        {
            "id": "aksessuary_dlya_payki",
            "name": "Аксессуары для пайки",
            "patterns": [r"(?i)\bаксессуар(ы)?\s*для\s*пайки\b"],
            "items": []
        },
        {
            "id": "vspomogatelnoe_kolesiko",
            "name": "Вспомогательное колесико",
            "patterns": [r"(?i)\bвспомогательное\s*колесико\b"],
            "items": []
        },
        {
            "id": "dlya_polirovki",
            "name": "Для полировки",
            "patterns": [r"(?i)\bдля\s*полировки\b"],
            "items": []
        },
        {
            "id": "kley",
            "name": "Клей",
            "patterns": [r"(?i)\bклей\b"],
            "items": []
        },
        {
            "id": "kovriki",
            "name": "Коврики",
            "patterns": [r"(?i)\bковрик(и)?\b"],
            "items": []
        },
        {
            "id": "lampy",
            "name": "Лампы",
            "patterns": [r"(?i)\бламп(а|ы)\b"],
            "items": []
        },
        {
            "id": "leski",
            "name": "Лески",
            "patterns": [r"(?i)\bлеск(а|и)?\b"],
            "items": []
        },
        {
            "id": "nozhnicy_lezviya",
            "name": "Ножницы/Лезвия",
            "patterns": [r"(?i)\bножниц(ы)?(/|\\)?\s*лезвия\b"],
            "items": []
        },
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
        {
            "id": "pistolet_dlya_nagreva",
            "name": "Пистолет для нагрева",
            "patterns": [r"(?i)\bпистолет\b.*\bдля\b.*\bнагрева\b"],
            "items": []
        },
        {
            "id": "press",
            "name": "Пресс",
            "patterns": [r"(?i)\bпресс\b"],
            "items": []
        },
        {
            "id": "stikery",
            "name": "Стикеры",
            "patterns": [r"(?i)\bстикер(ы)?\b"],
            "items": []
        },
        {
            "id": "trimmer",
            "name": "Триммер",
            "patterns": [r"(?i)\bтриммер\b"],
            "items": []
        },
        {
            "id": "tryapochki",
            "name": "Тряпочки",
            "patterns": [r"(?i)\bтряпочк(а|и)\b"],
            "items": []
        },
        {
            "id": "forma_dlya_vyravnivaniya",
            "name": "Форма для выравнивания",
            "patterns": [r"(?i)\bформа\b.*\bдля\s*выравнивания\b"],
            "items": []
        },
        {
            "id": "forma_dlya_fiksacii_ramak",
            "name": "Форма для фиксации рамок",
            "patterns": [r"(?i)\bформа\b.*\bдля\s*фиксации\s*рамак\b"],
            "items": []
        },
        {
            "id": "formy_dlya_laminirovaniya",
            "name": "Формы для ламинирования",
            "patterns": [r"(?i)\bформ(а|ы)\b.*\bдля\s*ламинирования\b"],
            "items": []
        }
    ]

def build_all_families() -> List[Dict[str, Any]]:
    """
    Все группы (iPhone, iPad, Apple Watch, JCID, Инструменты).
    """
    return [
        {
            "id": "iphone",
            "name": "iPhone",
            "subgroups": build_iphone_subgroups()
        },
        {
            "id": "ipad",
            "name": "IPad",
            "subgroups": build_ipad_subgroups()
        },
        {
            "id": "apple_watch",
            "name": "Apple Watch",
            "subgroups": build_apple_watch_subgroups()
        },
        {
            "id": "jcid",
            "name": "Дополнение JCID",
            "subgroups": build_jcid_subgroups()
        },
        {
            "id": "instrumenty",
            "name": "Инструменты",
            "subgroups": build_instrumenty_subgroups()
        }
    ]

############################
# 5. Инициализация aiogram 3.x
############################
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

############################
# 5.1 Команда /start
############################
@dp.message(Command("start"))
async def cmd_start(message: Message):
    global families

    # 1. Парсим YML
    offers = fetch_offers_from_yml(YML_URL)  # <-- Вызов функции парсинга

    # 2. Очищаем старые items
    families = build_all_families()  # перестраиваем структуру
    for fam in families:
        for sg in fam["subgroups"]:
            sg["items"].clear()

    # 3. Распределяем товары по subgroups
    for fam in families:
        for off in offers:
            for sg in fam["subgroups"]:
                matched = any(re.search(p, off["name"]) for p in sg["patterns"])
                if matched:
                    sg["items"].append(off)

    # Выводим кнопки групп
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for fam in families:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=fam["name"],
                callback_data=f"fam_{fam['id']}"
            )
        ])
    await message.answer(
        "Здравствуйте! Я ваш Telegram-помощник по запчастям Apple.\nВыберите нужную группу:",
        reply_markup=kb
    )

############################
# 5.2 Обработка выбора группы (fam_xxx)
############################
@dp.callback_query(F.data.startswith("fam_"))
async def on_family_callback(callback: CallbackQuery):
    fam_id = callback.data.split("_", 1)[1]
    chosen_fam = next((f for f in families if f["id"] == fam_id), None)
    if not chosen_fam:
        await callback.answer("Группа не найдена.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for sg in chosen_fam["subgroups"]:
        count_items = len(sg["items"])
        btn_text = f"{sg['name']} ({count_items})"
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=btn_text, callback_data=f"sg_{fam_id}_{sg['id']}")
        ])

    await callback.message.edit_text(
        f"Вы выбрали: {chosen_fam['name']}\nВыберите подгруппу:",
        reply_markup=kb
    )
    await callback.answer()

############################
# 5.3 Обработка выбора подгруппы (sg_xxx)
############################
@dp.callback_query(F.data.startswith("sg_"))
async def on_subgroup_callback(callback: CallbackQuery):
    parts = callback.data.split("_", 2)
    if len(parts) < 3:
        await callback.answer("Ошибка subгруппы.")
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

    # Удаляем старое сообщение
    await callback.message.delete()

    # Отправляем каждый товар отдельным сообщением
    for off in items:
        short_title = shorten_name(off["name"], 60)
        price_str = f"{off['price']:.2f}" if off["price"] else "0"
        available_str = "В наличии" if off["available"] else "Нет в наличии"
        code_str = off["vendorCode"] or "—"

        text_msg = (
            f"<b>{short_title}</b>\n"
            f"Цена: {price_str}₽\n"
            f"Наличие: {available_str}\n"
            f"Код: {code_str}"
        )
        kb_item = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton("Заказать", callback_data=f"order_{off['id']}")
        ]])
        await callback.message.answer(
            text_msg,
            parse_mode="HTML",
            reply_markup=kb_item
        )

    # В конце - кнопка «Связаться с менеджером»
    kb_final = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton("Связаться с менеджером", callback_data="contact_manager")
    ]])
    await callback.message.answer(
        f"Всего товаров: {len(items)}\n"
        "Чтобы оформить заказ, нажмите «Заказать» рядом с нужным товаром.\n"
        "Либо свяжитесь с менеджером:",
        reply_markup=kb_final
    )
    await callback.answer()

############################
# 5.4 «Заказать» товар (order_xxx)
############################
@dp.callback_query(F.data.startswith("order_"))
async def on_order_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    item_id = callback.data.split("_", 1)[1]

    # Ищем товар
    ordered_item = None
    for fam in families:
        for sg in fam["subgroups"]:
            for off in sg["items"]:
                if off["id"] == item_id:
                    ordered_item = off
                    break
            if ordered_item:
                break
        if ordered_item:
            break

    if not ordered_item:
        await callback.answer("Товар не найден.")
        return

    if user_id not in user_data:
        user_data[user_id] = {"phone": None, "selected_item": None}

    user_data[user_id]["selected_item"] = ordered_item

    # Если телефон уже есть - сразу отправляем заказ
    if user_data[user_id]["phone"]:
        await send_order_to_manager(user_id)
        await callback.answer("Ваш заказ оформлен!")
    else:
        # Иначе просим телефон
        await callback.answer()
        contact_btn = KeyboardButton(text="Отправить номер телефона", request_contact=True)
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(contact_btn)
        await callback.message.answer(
            "Пожалуйста, отправьте свой номер телефона, чтобы подтвердить заказ:",
            reply_markup=kb
        )

############################
# 5.5 Отправка заказа менеджеру
############################
async def send_order_to_manager(user_id: int):
    if user_id not in user_data:
        return
    phone = user_data[user_id].get("phone")
    item = user_data[user_id].get("selected_item")
    if not phone or not item:
        return

    text_msg = (
        "Новый заказ!\n"
        f"Телефон: {phone}\n"
        f"Товар: {item['name']}\n"
        f"Цена: {item['price']:.2f}₽\n"
        f"Код: {item['vendorCode'] or '—'}"
    )
    await bot.send_message(chat_id=MANAGER_CHAT_ID, text=text_msg)
    # Сбрасываем выбранный товар
    user_data[user_id]["selected_item"] = None

############################
# 5.6 «Связаться с менеджером»
############################
@dp.callback_query(F.data == "contact_manager")
async def on_contact_manager(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"phone": None, "selected_item": None}

    if user_data[user_id]["phone"]:
        await callback.answer("У нас уже есть ваш номер, ожидайте связи!")
    else:
        await callback.answer()
        contact_btn = KeyboardButton(text="Отправить номер телефона", request_contact=True)
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(contact_btn)
        await callback.message.answer(
            "Отправьте номер телефона, чтобы менеджер связался с вами:",
            reply_markup=kb
        )

############################
# 5.7 Пришёл контакт
############################
@dp.message(F.content_type == ContentType.CONTACT)
async def on_user_contact(message: Message):
    user_id = message.from_user.id
    phone_number = message.contact.phone_number

    if user_id not in user_data:
        user_data[user_id] = {"phone": None, "selected_item": None}

    user_data[user_id]["phone"] = phone_number
    selected_item = user_data[user_id]["selected_item"]

    if selected_item:
        # Завершить заказ
        await message.answer("Спасибо! Телефон получен. Завершаем заказ...")
        await send_order_to_manager(user_id)
        await message.answer(
            "Заказ отправлен менеджеру! Ожидайте связи.\n"
            "Чтобы заказать что-то ещё, введите /start."
        )
    else:
        # Просто контакт
        await message.answer(
            "Спасибо! Ваш номер получен. Менеджер свяжется с вами.",
            reply_markup=ReplyKeyboardMarkup(remove_keyboard=True)
        )
        # Уведомим менеджера
        await bot.send_message(
            chat_id=MANAGER_CHAT_ID,
            text=f"Пользователь @{message.from_user.username or '—'} "
                 f"({message.from_user.full_name or '—'}) оставил номер: {phone_number}"
        )

############################
# 6. Запуск бота (aiogram 3.x)
############################
async def main():
    # Запускаем polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
