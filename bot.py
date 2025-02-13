import os
import logging
import re
import requests
import xml.etree.ElementTree as ET

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.utils import executor
from aiogram.dispatcher.filters import ContentType

from dotenv import load_dotenv

##########################
# 1. Загрузка окружения
##########################
load_dotenv()

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
YML_URL = os.getenv("YML_URL", "")
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID", "0"))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# user_data[user_id] = {
#   "phone": str или None,
#   "selected_item": dict (товар из offers) или None
# }
user_data = {}

##########################
# 2. Подгруппы iPhone
##########################
def build_iphone_subgroups():
    """
    iPhone: от iPhone 16 Pro Max к iPhone 6/6 Plus.
    Ничего не сокращаем, порядок — от новейшего к старейшему.
    """
    return [
        # --- iPhone 16 ---
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

        # --- 15 ---
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

        # --- 14 ---
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

        # --- 13 ---
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

        # --- 12 ---
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

        # --- 11 ---
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

        # --- X, Xs, Xr ---
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

        # --- SE ---
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

        # --- 8 / 7 / 6 ---
        {
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

##########################
# 2.1 Подгруппы iPad (в вашем порядке)
##########################
def build_ipad_subgroups():
    """
    Полный список iPad (в том порядке, что вы дали).
    Не сокращаем, просто используем raw.
    """
    return [
        # 1) IPad 10
        {
            "id": "ipad_10",
            "name": "IPad 10",
            "patterns": [r"(?i)\bipad\s*10\b"],
            "items": []
        },
        # 2) IPad 5
        {
            "id": "ipad_5",
            "name": "IPad 5",
            "patterns": [r"(?i)\bipad\s*5\b"],
            "items": []
        },
        # 3) IPad 6
        {
            "id": "ipad_6",
            "name": "IPad 6",
            "patterns": [r"(?i)\bipad\s*6\b"],
            "items": []
        },
        # 4) IPad 7
        {
            "id": "ipad_7",
            "name": "IPad 7",
            "patterns": [r"(?i)\bipad\s*7\b"],
            "items": []
        },
        # 5) IPad 8
        {
            "id": "ipad_8",
            "name": "IPad 8",
            "patterns": [r"(?i)\bipad\s*8\b"],
            "items": []
        },
        # 6) IPad 9
        {
            "id": "ipad_9",
            "name": "IPad 9",
            "patterns": [r"(?i)\bipad\s*9\b"],
            "items": []
        },
        # 7) IPad Air 1
        {
            "id": "ipad_air_1",
            "name": "IPad Air 1",
            "patterns": [r"(?i)\bipad\s*air\s*1\b"],
            "items": []
        },
        # 8) IPad Air 2
        {
            "id": "ipad_air_2",
            "name": "IPad Air 2",
            "patterns": [r"(?i)\bipad\s*air\s*2\b"],
            "items": []
        },
        # 9) IPad Air 3
        {
            "id": "ipad_air_3",
            "name": "IPad Air 3",
            "patterns": [r"(?i)\bipad\s*air\s*3\b"],
            "items": []
        },
        # 10) IPad Air 4
        {
            "id": "ipad_air_4",
            "name": "IPad Air 4",
            "patterns": [r"(?i)\bipad\s*air\s*4\b"],
            "items": []
        },
        # 11) IPad Air 5
        {
            "id": "ipad_air_5",
            "name": "IPad Air 5",
            "patterns": [r"(?i)\bipad\s*air\s*5\b"],
            "items": []
        },
        # 12) IPad Air (M2) 11
        {
            "id": "ipad_air_m2_11",
            "name": "IPad Air (M2) 11",
            "patterns": [r"(?i)\bipad\s*air\s*\(m2\)\s*11\b"],
            "items": []
        },
        # 13) IPad Air (M2) 13
        {
            "id": "ipad_air_m2_13",
            "name": "IPad Air (M2) 13",
            "patterns": [r"(?i)\bipad\s*air\s*\(m2\)\s*13\b"],
            "items": []
        },
        # 14) IPad mini 2
        {
            "id": "ipad_mini_2",
            "name": "IPad mini 2",
            "patterns": [r"(?i)\bipad\s*mini\s*2\b"],
            "items": []
        },
        # 15) IPad mini 3
        {
            "id": "ipad_mini_3",
            "name": "IPad mini 3",
            "patterns": [r"(?i)\bipad\s*mini\s*3\b"],
            "items": []
        },
        # 16) IPad mini 4
        {
            "id": "ipad_mini_4",
            "name": "IPad mini 4",
            "patterns": [r"(?i)\bipad\s*mini\s*4\b"],
            "items": []
        },
        # 17) IPad mini 5
        {
            "id": "ipad_mini_5",
            "name": "IPad mini 5",
            "patterns": [r"(?i)\bipad\s*mini\s*5\b"],
            "items": []
        },
        # 18) IPad mini 6
        {
            "id": "ipad_mini_6",
            "name": "IPad mini 6",
            "patterns": [r"(?i)\bipad\s*mini\s*6\b"],
            "items": []
        },
        # 19) IPad mini (A17 Pro)
        {
            "id": "ipad_mini_a17_pro",
            "name": "IPad mini (A17 Pro)",
            "patterns": [r"(?i)\bipad\s*mini\s*\(a17\s*pro\)"],
            "items": []
        },
        # 20) IPad Pro 10,5
        {
            "id": "ipad_pro_10_5",
            "name": "IPad Pro 10,5",
            "patterns": [r"(?i)\bipad\s*pro\s*10\.?5\b"],
            "items": []
        },
        # 21) IPad Pro 11 (1 Gen)
        {
            "id": "ipad_pro_11_1_gen",
            "name": "IPad Pro 11 (1 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*11\s*\(1\s*gen\)"],
            "items": []
        },
        # 22) IPad Pro 11 (2 Gen)
        {
            "id": "ipad_pro_11_2_gen",
            "name": "IPad Pro 11 (2 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*11\s*\(2\s*gen\)"],
            "items": []
        },
        # 23) IPad Pro 11 (3 Gen)
        {
            "id": "ipad_pro_11_3_gen",
            "name": "IPad Pro 11 (3 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*11\s*\(3\s*gen\)"],
            "items": []
        },
        # 24) IPad Pro 11 (4 Gen)
        {
            "id": "ipad_pro_11_4_gen",
            "name": "IPad Pro 11 (4 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*11\s*\(4\s*gen\)"],
            "items": []
        },
        # 25) IPad Pro 12.9 (1 Gen)
        {
            "id": "ipad_pro_12_9_1_gen",
            "name": "IPad Pro 12.9 (1 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*12\.?9\s*\(1\s*gen\)"],
            "items": []
        },
        # 26) IPad Pro 12.9 (2 Gen)
        {
            "id": "ipad_pro_12_9_2_gen",
            "name": "IPad Pro 12.9 (2 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*12\.?9\s*\(2\s*gen\)"],
            "items": []
        },
        # 27) IPad Pro 12.9 (3 Gen)
        {
            "id": "ipad_pro_12_9_3_gen",
            "name": "IPad Pro 12.9 (3 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*12\.?9\s*\(3\s*gen\)"],
            "items": []
        },
        # 28) IPad Pro 12.9 (4 Gen)
        {
            "id": "ipad_pro_12_9_4_gen",
            "name": "IPad Pro 12.9 (4 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*12\.?9\s*\(4\s*gen\)"],
            "items": []
        },
        # 29) IPad Pro 12.9 (5 Gen)
        {
            "id": "ipad_pro_12_9_5_gen",
            "name": "IPad Pro 12.9 (5 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*12\.?9\s*\(5\s*gen\)"],
            "items": []
        },
        # 30) IPad Pro 12.9 (6 Gen)
        {
            "id": "ipad_pro_12_9_6_gen",
            "name": "IPad Pro 12.9 (6 Gen)",
            "patterns": [r"(?i)\bipad\s*pro\s*12\.?9\s*\(6\s*gen\)"],
            "items": []
        },
        # 31) IPad Pro 9.7
        {
            "id": "ipad_pro_9_7",
            "name": "IPad Pro 9.7",
            "patterns": [r"(?i)\bipad\s*pro\s*9\.?7\b"],
            "items": []
        },
        # 32) IPad Pro (M4) 11
        {
            "id": "ipad_pro_m4_11",
            "name": "IPad Pro (M4) 11",
            "patterns": [r"(?i)\bipad\s*pro\s*\(m4\)\s*11\b"],
            "items": []
        },
        # 33) IPad Pro (M4) 13
        {
            "id": "ipad_pro_m4_13",
            "name": "IPad Pro (M4) 13",
            "patterns": [r"(?i)\bipad\s*pro\s*\(m4\)\s*13\b"],
            "items": []
        },
    ]

##########################
# 2.2 Подгруппы Apple Watch (в вашем порядке)
##########################
def build_apple_watch_subgroups():
    """
    Apple Watch — ровно по списку, который вы дали.
    (Не меняем порядок, не сокращаем.)
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

##########################
# 2.3 Подгруппы JCID
##########################
def build_jcid_subgroups():
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

##########################
# 2.4 Подгруппы Инструменты
##########################
def build_instrumenty_subgroups():
    return [
        {
            "id": "aksessuary_dlya_payki",
            "name": "Аксессуары для пайки",
            "patterns": [
                r"(?i)\bаксессуар(ы)?\s*для\s*пайки\b"
            ],
            "items": []
        },
        {
            "id": "vspomogatelnoe_kolesiko",
            "name": "Вспомогательное колесико",
            "patterns": [
                r"(?i)\bвспомогательное\s*колесико\b"
            ],
            "items": []
        },
        {
            "id": "dlya_polirovki",
            "name": "Для полировки",
            "patterns": [
                r"(?i)\bдля\s*полировки\b"
            ],
            "items": []
        },
        {
            "id": "kley",
            "name": "Клей",
            "patterns": [
                r"(?i)\bклей\b"
            ],
            "items": []
        },
        {
            "id": "kovriki",
            "name": "Коврики",
            "patterns": [
                r"(?i)\bковрик(и)?\b"
            ],
            "items": []
        },
        {
            "id": "lampy",
            "name": "Лампы",
            "patterns": [
                r"(?i)\bламп(а|ы)\b"
            ],
            "items": []
        },
        {
            "id": "leski",
            "name": "Лески",
            "patterns": [
                r"(?i)\bлеск(а|и)?\b"
            ],
            "items": []
        },
        {
            "id": "nozhnicy_lezviya",
            "name": "Ножницы/Лезвия",
            "patterns": [
                r"(?i)\bножниц(ы)?(/|\\)?\s*лезвия\b"
            ],
            "items": []
        },
        {
            "id": "otvertki",
            "name": "Отвертки",
            "patterns": [
                r"(?i)\bотвертк(а|и)\b"
            ],
            "items": []
        },
        {
            "id": "pincety",
            "name": "Пинцеты",
            "patterns": [
                r"(?i)\bпинцет(ы)?\b"
            ],
            "items": []
        },
        {
            "id": "pistolet_dlya_nagreva",
            "name": "Пистолет для нагрева",
            "patterns": [
                r"(?i)\bпистолет\b.*\bдля\b.*\bнагрева\b"
            ],
            "items": []
        },
        {
            "id": "press",
            "name": "Пресс",
            "patterns": [
                r"(?i)\bпресс\b"
            ],
            "items": []
        },
        {
            "id": "stikery",
            "name": "Стикеры",
            "patterns": [
                r"(?i)\bстикер(ы)?\b"
            ],
            "items": []
        },
        {
            "id": "trimmer",
            "name": "Триммер",
            "patterns": [
                r"(?i)\bтриммер\b"
            ],
            "items": []
        },
        {
            "id": "tryapochki",
            "name": "Тряпочки",
            "patterns": [
                r"(?i)\bтряпочк(а|и)\b"
            ],
            "items": []
        },
        {
            "id": "forma_dlya_vyravnivaniya",
            "name": "Форма для выравнивания",
            "patterns": [
                r"(?i)\bформа\b.*\bдля\s*выравнивания\b"
            ],
            "items": []
        },
        {
            "id": "forma_dlya_fiksacii_ramak",
            "name": "Форма для фиксации рамок",
            "patterns": [
                r"(?i)\bформа\b.*\bдля\s*фиксации\s*рамок\b"
            ],
            "items": []
        },
        {
            "id": "formy_dlya_laminirovaniya",
            "name": "Формы для ламинирования",
            "patterns": [
                r"(?i)\bформ(а|ы)\b.*\bдля\s*ламинирования\b"
            ],
            "items": []
        }
    ]

##########################
# 2.5 Собираем все группы
##########################
def build_all_families():
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

families = build_all_families()

##########################
# 3. Парсинг YML
##########################
def fetch_offers_from_yml(url: str):
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    shop_el = root.find("shop")
    offers_el = shop_el.find("offers")

    offers = []
    for off_el in offers_el.findall("offer"):
        offer_id = off_el.attrib.get("id", "")
        available = (off_el.attrib.get("available", "false").lower() == "true")

        name_el = off_el.find("name")
        name_val = name_el.text.strip() if (name_el is not None and name_el.text) else ""

        price_el = off_el.find("price")
        price_val = 0.0
        if price_el is not None and price_el.text:
            try:
                price_val = float(price_el.text)
            except:
                price_val = 0.0

        vendor_el = off_el.find("vendorCode")
        vendor_code_val = vendor_el.text.strip() if (vendor_el and vendor_el.text) else ""

        offers.append({
            "id": offer_id,
            "name": name_val,
            "price": price_val,
            "available": available,
            "vendorCode": vendor_code_val
        })

    return offers

##########################
# 4. Распределяем товары
##########################
def distribute_offers_to_subgroups(offers, subgroups):
    for off in offers:
        title = off["name"]
        for sg in subgroups:
            # Если хоть одна регулярка совпала, товар идёт в эту подгруппу
            matched = any(re.search(p, title) for p in sg["patterns"])
            if matched:
                sg["items"].append(off)

##########################
# 5. Логика бота
##########################

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    """
    1) Загружаем товары из YML
    2) Чистим subgroups
    3) Раскладываем
    4) Показываем список групп
    """
    global families

    all_offers = fetch_offers_from_yml(YML_URL)

    for fam in families:
        for sg in fam["subgroups"]:
            sg["items"].clear()

    for fam in families:
        distribute_offers_to_subgroups(all_offers, fam["subgroups"])

    kb = InlineKeyboardMarkup(row_width=1)
    for fam in families:
        kb.add(
            InlineKeyboardButton(fam["name"], callback_data=f"fam_{fam['id']}")
        )

    text = (
        "Здравствуйте! Я ваш Telegram-помощник по запчастям Apple.\n"
        "Выберите нужную группу:"
    )
    await message.answer(text, reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith("fam_"))
async def on_family_callback(callback_query: types.CallbackQuery):
    fam_id = callback_query.data.split("_", 1)[1]

    chosen_fam = next((f for f in families if f["id"] == fam_id), None)
    if not chosen_fam:
        await callback_query.answer("Группа не найдена.")
        return

    kb = InlineKeyboardMarkup(row_width=1)
    for sg in chosen_fam["subgroups"]:
        count_items = len(sg["items"])
        btn_text = f"{sg['name']} ({count_items})"
        kb.add(
            InlineKeyboardButton(btn_text, callback_data=f"sg_{fam_id}_{sg['id']}")
        )

    await callback_query.message.edit_text(
        f"Вы выбрали: {chosen_fam['name']}\nВыберите подгруппу:",
        reply_markup=kb
    )
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("sg_"))
async def on_subgroup_callback(callback_query: types.CallbackQuery):
    parts = callback_query.data.split("_", 2)
    if len(parts) < 3:
        await callback_query.answer("Ошибка subгруппы.")
        return

    fam_id, sg_id = parts[1], parts[2]
    chosen_fam = next((f for f in families if f["id"] == fam_id), None)
    if not chosen_fam:
        await callback_query.answer("Группа не найдена.")
        return

    chosen_sg = next((s for s in chosen_fam["subgroups"] if s["id"] == sg_id), None)
    if not chosen_sg:
        await callback_query.answer("Подгруппа не найдена.")
        return

    items = chosen_sg["items"]
    if not items:
        await callback_query.message.edit_text(
            f"В подгруппе '{chosen_sg['name']}' пока нет товаров."
        )
        await callback_query.answer()
        return

    # Удалим старое сообщение
    await callback_query.message.delete()

    # Отправим товары по одному сообщению
    for off in items:
        text_msg = (
            f"<b>{off['name']}</b>\n"
            f"Цена: {off['price']:.2f}₽\n"
            f"Наличие: {'В наличии' if off['available'] else 'Нет в наличии'}\n"
            f"Код: {off['vendorCode'] or '—'}"
        )

        kb_item = InlineKeyboardMarkup()
        kb_item.add(
            InlineKeyboardButton("Заказать", callback_data=f"order_{off['id']}")
        )

        await bot.send_message(
            chat_id=callback_query.from_user.id,
            text=text_msg,
            parse_mode="HTML",
            reply_markup=kb_item
        )

    # В конце — "Связаться с менеджером"
    kb_contact = InlineKeyboardMarkup()
    kb_contact.add(InlineKeyboardButton("Связаться с менеджером", callback_data="contact_manager"))
    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=(
            f"Всего товаров: {len(items)}\n"
            "Чтобы оформить заказ, нажмите «Заказать» рядом с нужным товаром.\n"
            "Либо свяжитесь с менеджером:"
        ),
        reply_markup=kb_contact
    )

    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("order_"))
async def on_order_callback(callback_query: types.CallbackQuery):
    """
    Пользователь нажал "Заказать". Если телефон есть — отправляем заказ, иначе просим контакт.
    """
    user_id = callback_query.from_user.id
    item_id = callback_query.data.split("_", 1)[1]

    # Находим товар
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
        await callback_query.answer("Товар не найден.")
        return

    if user_id not in user_data:
        user_data[user_id] = {"phone": None, "selected_item": None}

    user_data[user_id]["selected_item"] = ordered_item

    if user_data[user_id]["phone"]:
        # Телефон уже есть => сразу оформляем
        await send_order_to_manager(user_id)
        await callback_query.answer("Ваш заказ оформлен!")
    else:
        # Просим номер
        await callback_query.answer()
        contact_btn = KeyboardButton("Отправить номер телефона", request_contact=True)
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(contact_btn)

        await bot.send_message(
            chat_id=user_id,
            text="Пожалуйста, отправьте свой номер телефона, чтобы подтвердить заказ:",
            reply_markup=kb
        )


async def send_order_to_manager(user_id: int):
    """
    Отправляем информацию о заказе менеджеру.
    """
    if user_id not in user_data:
        return

    phone = user_data[user_id]["phone"]
    item = user_data[user_id]["selected_item"]

    if not phone or not item:
        return

    text_msg = (
        f"Новый заказ!\n"
        f"Телефон: {phone}\n"
        f"Товар: {item['name']}\n"
        f"Цена: {item['price']:.2f}₽\n"
        f"Код: {item['vendorCode'] or '—'}"
    )
    await bot.send_message(MANAGER_CHAT_ID, text_msg)

    # Сбрасываем выбранный товар
    user_data[user_id]["selected_item"] = None


@dp.callback_query_handler(lambda c: c.data == "contact_manager")
async def on_contact_manager(callback_query: types.CallbackQuery):
    """
    "Связаться с менеджером" - если телефона нет, просим. Иначе говорим, что номер у нас есть.
    """
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"phone": None, "selected_item": None}

    if user_data[user_id]["phone"]:
        await callback_query.answer("У нас уже есть ваш номер, ожидайте связи!")
    else:
        await callback_query.answer()
        contact_btn = KeyboardButton("Отправить номер телефона", request_contact=True)
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(contact_btn)

        await bot.send_message(
            chat_id=user_id,
            text="Отправьте номер телефона, чтобы менеджер связался с вами:",
            reply_markup=kb
        )


@dp.message_handler(content_types=[ContentType.CONTACT])
async def on_user_contact(message: types.Message):
    """
    Пользователь отправил контакт. Если был выбран товар, завершаем заказ, иначе просто "связаться".
    """
    user_id = message.from_user.id
    phone_number = message.contact.phone_number

    if user_id not in user_data:
        user_data[user_id] = {"phone": None, "selected_item": None}

    user_data[user_id]["phone"] = phone_number

    selected_item = user_data[user_id]["selected_item"]
    if selected_item:
        # Завершаем заказ
        await message.answer("Спасибо! Телефон получен. Завершаем заказ...")
        await send_order_to_manager(user_id)
        await message.answer(
            "Заказ отправлен менеджеру. Ожидайте связи!\n"
            "Чтобы заказать что-то ещё, введите /start."
        )
    else:
        # Просто контакт (без товара)
        await message.answer(
            "Спасибо! Ваш номер получен. Менеджер свяжется с вами.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        # Уведомим менеджера
        await bot.send_message(
            chat_id=MANAGER_CHAT_ID,
            text=f"Пользователь @{message.from_user.username or '—'} ({message.from_user.full_name or '—'}) "
                 f"оставил номер: {phone_number}"
        )


##########################
# 6. Запуск бота
##########################
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
