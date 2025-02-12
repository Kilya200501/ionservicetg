import asyncio
import time
import aiohttp
import xmltodict
from math import ceil

from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message, 
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command

TOKEN = "8102076873:AAHf_fPaG5n2tr5C1NnoOVJ62MnIo-YbRi8"
FEED_URL = "https://ion-master.ru/index.php?route=extension/feed/yandex_yml"
MANAGER_ID = 5300643604

CACHE_TTL = 300
ITEMS_PER_PAGE = 10

bot = Bot(token=TOKEN)
dp = Dispatcher()

CATEGORIES = {}
CAT_ROOTS = []
CAT_PRODUCTS = {}
last_update_time = 0.0
feed_lock = asyncio.Lock()
session = None

# Укажем ID категорий (в фиде), например:
IPHONE_ID = None    # <-- после загрузки фида найдём по имени
APPLEWATCH_ID = None
IPAD_ID = None
MACBOOK_ID = None
TOOL_ID = None
JCID_ID = None

# Жёсткие подгруппы для iPhone (fakeCatId):
IPHONE_SUBGROUPS = [
    {"id": "i16promax", "name": "iPhone 16 Pro Max"},
    {"id": "i16pro",    "name": "iPhone 16 Pro"},
    {"id": "i16plus",   "name": "iPhone 16 Plus"},
    {"id": "i16",       "name": "iPhone 16"},
    {"id": "i15",       "name": "iPhone 15 ..."},
    # и т.д.
]

# Пример для Apple Watch
APPLEWATCH_SUBGROUPS = [
    {"id": "aw7", "name": "Apple Watch Series 7"},
    {"id": "aw8", "name": "Apple Watch Series 8"},
    # ...
]

async def init_session():
    global session
    if session is None:
        session = aiohttp.ClientSession()

async def close_session():
    global session
    if session:
        await session.close()
        session = None

async def fetch_feed(force=False):
    global last_update_time, CATEGORIES, CAT_ROOTS, CAT_PRODUCTS
    global IPHONE_ID, APPLEWATCH_ID, IPAD_ID, MACBOOK_ID, TOOL_ID, JCID_ID

    now = time.time()
    if not force and (now - last_update_time) < CACHE_TTL:
        return
    async with feed_lock:
        now = time.time()
        if not force and (now - last_update_time) < CACHE_TTL:
            return

        try:
            async with session.get(FEED_URL, timeout=10) as resp:
                if resp.status != 200:
                    print(f"Ошибка {resp.status} при загрузке фида")
                    return
                xml_text = await resp.text()

            data = xmltodict.parse(xml_text)
            shop = data["yml_catalog"]["shop"]

            CATEGORIES.clear()
            CAT_ROOTS.clear()
            CAT_PRODUCTS.clear()

            raw_cats = shop["categories"]["category"]
            if isinstance(raw_cats, dict):
                raw_cats = [raw_cats]

            # Парсим категории
            for c in raw_cats:
                cat_id = c["@id"]
                parent_id = c.get("@parentId")
                name = c.get("#text", "Без названия")

                CATEGORIES[cat_id] = {
                    "id": cat_id,
                    "parent": parent_id,
                    "name": name,
                    "children": []
                }

            # Связываем дерево
            for cid, cat_data in CATEGORIES.items():
                pid = cat_data["parent"]
                if pid and pid in CATEGORIES:
                    CATEGORIES[pid]["children"].append(cid)
                else:
                    CAT_ROOTS.append(cid)

            # Находим ID нужных категорий по имени:
            IPHONE_ID = next((x for x in CATEGORIES if CATEGORIES[x]["name"].lower() == "iphone"), None)
            APPLEWATCH_ID = next((x for x in CATEGORIES if CATEGORIES[x]["name"].lower() == "apple watch"), None)
            IPAD_ID = next((x for x in CATEGORIES if CATEGORIES[x]["name"].lower() == "ipad"), None)
            MACBOOK_ID = next((x for x in CATEGORIES if CATEGORIES[x]["name"].lower() == "macbook"), None)
            TOOL_ID = next((x for x in CATEGORIES if CATEGORIES[x]["name"].lower() == "инструменты"), None)
            JCID_ID = next((x for x in CATEGORIES if "jc" in CATEGORIES[x]["name"].lower()), None)

            # Парсим товары
            raw_offers = shop["offers"]["offer"]
            if isinstance(raw_offers, dict):
                raw_offers = [raw_offers]
            for off in raw_offers:
                prod_id = off.get("@id")
                cat_id = off.get("categoryId")
                name = off.get("name", "Без названия")
                price = off.get("price", "0")

                if cat_id:
                    if cat_id not in CAT_PRODUCTS:
                        CAT_PRODUCTS[cat_id] = []
                    CAT_PRODUCTS[cat_id].append({
                        "id": prod_id,
                        "name": name,
                        "price": price
                    })

            last_update_time = time.time()

        except Exception as e:
            print("Ошибка при загрузке/парсинге фида:", e)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await init_session()
    await fetch_feed()

    text = "<b>Выберите категорию:</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[])

    # Порядок: iPhone, Apple Watch, iPad, MacBook, Дополнения JCID, Инструменты
    # Дальше все остальные корневые, если есть, по алфавиту.

    # Собираем корневые в list
    root_list = []
    for r in CAT_ROOTS:
        nm = CATEGORIES[r]["name"]
        root_list.append((r, nm))

    # Жёстко упорядочим:
    forced_order = []
    def pick(cat_id):
        return any(x==cat_id for (x,_) in root_list)

    # 1) iPhone
    if IPHONE_ID and pick(IPHONE_ID):
        forced_order.append((IPHONE_ID, "iPhone"))
    # 2) Apple Watch
    if APPLEWATCH_ID and pick(APPLEWATCH_ID):
        forced_order.append((APPLEWATCH_ID, "Apple Watch"))
    # 3) iPad
    if IPAD_ID and pick(IPAD_ID):
        forced_order.append((IPAD_ID, "iPad"))
    # 4) MacBook
    if MACBOOK_ID and pick(MACBOOK_ID):
        forced_order.append((MACBOOK_ID, "MacBook"))
    # 5) Дополнения JCID
    if JCID_ID and pick(JCID_ID):
        forced_order.append((JCID_ID, CATEGORIES[JCID_ID]["name"]))
    # 6) Инструменты
    if TOOL_ID and pick(TOOL_ID):
        forced_order.append((TOOL_ID, CATEGORIES[TOOL_ID]["name"]))

    # Удаляем из root_list те, что уже пошли в forced_order
    used_ids = {x[0] for x in forced_order}
    remain = [(cid,nm) for (cid,nm) in root_list if cid not in used_ids]

    # Сортируем оставшиеся по алфавиту
    remain.sort(key=lambda x: x[1].lower())

    final_list = forced_order + remain

    # Выводим кнопки
    for (cid, nm) in final_list:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=nm,
                callback_data=f"rootcat_{cid}"
            )
        ])

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.callback_query()
async def callback_router(call: CallbackQuery):
    data = call.data

    # 1) rootcat_{cat_id} — пользователь выбрал одну из «основных» категорий
    if data.startswith("rootcat_"):
        cat_id = data.split("_",1)[1]
        # Если это iPhone_ID, показываем жёстко iPhone_subgroups
        if cat_id == IPHONE_ID:
            kb = InlineKeyboardMarkup(inline_keyboard=[])
            for sg in IPHONE_SUBGROUPS:
                kb.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=sg["name"],
                        callback_data=f"sub_iphone_{sg['id']}"
                    )
                ])
            await call.message.edit_text("<b>iPhone</b>\nВыберите подгруппу:", parse_mode="HTML", reply_markup=kb)
        elif cat_id == APPLEWATCH_ID:
            # Аналогично
            kb = InlineKeyboardMarkup(inline_keyboard=[])
            for sg in APPLEWATCH_SUBGROUPS:
                kb.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=sg["name"],
                        callback_data=f"sub_aw_{sg['id']}"
                    )
                ])
            await call.message.edit_text("<b>Apple Watch</b>\nВыберите модель:", parse_mode="HTML", reply_markup=kb)
        else:
            # Если это iPad / MacBook / Инструменты / и т.д. — идём старым путём
            # (пагинация или вложенные категории из фида)
            await show_category(cat_id, call)

    # 2) sub_iphone_{subId} — пользователь выбрал конкретную подгруппу iPhone
    elif data.startswith("sub_iphone_"):
        subId = data.split("_",2)[2]
        # Здесь у нас subId = "i16promax" и т. д.
        # Нужно определить, какие товары показывать.
        # Способ 1: Если в фиде есть отдельная cat_id="9999" для i16promax, то:
        # await show_category("9999", call)
        # Способ 2: Фильтруем товары iPhone по названию:
        await show_sub_iphone(call, subId)

    # 3) sub_aw_{subId} — пользователь выбрал подгруппу Apple Watch
    elif data.startswith("sub_aw_"):
        subId = data.split("_",2)[2]
        # Аналогично
        await show_sub_aw(call, subId)

    # 4) Все остальные варианты, например "cat_{cat_id}_{page}", "prod_{...}", "order_{...}"
    elif data.startswith("cat_"):
        # это старый путь (пагинация), например "cat_XXX_0"
        parts = data.split("_")
        cat_id = parts[1]
        page = int(parts[2]) if len(parts)>2 else 0
        await show_category_page(call, cat_id, page)
    elif data.startswith("prod_"):
        await show_product(call, data)
    elif data.startswith("order_"):
        await do_order(call, data)
    else:
        await call.answer("Неизвестная команда")

# ------------------- ФУНКЦИИ ДЛЯ «СТАРОГО» ПУТИ -------------------

async def show_category(cat_id, call: CallbackQuery, page=0):
    """
    Показываем категорию из фида (иерархию + товары) с пагинацией.
    """
    kb, cur_page, total_pages = build_category_page_kb(cat_id, page)
    cat_name = CATEGORIES[cat_id]["name"] if cat_id in CATEGORIES else "???"
    cnt = len(get_entries_for_category(cat_id))
    text = f"<b>{cat_name}</b>\n"
    if cnt==0:
        text += "\nПусто."
    else:
        text += f"\nСтраница {cur_page+1}/{total_pages}"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

async def show_category_page(call: CallbackQuery, cat_id: str, page: int):
    kb, cur_page, total_pages = build_category_page_kb(cat_id, page)
    cat_name = CATEGORIES[cat_id]["name"] if cat_id in CATEGORIES else "???"
    cnt = len(get_entries_for_category(cat_id))
    text = f"<b>{cat_name}</b>\n"
    if cnt==0:
        text += "\nПусто."
    else:
        text += f"\nСтраница {cur_page+1}/{total_pages}"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

async def show_product(call: CallbackQuery, data: str):
    # data = "prod_XXX_YYY"
    _, prod_id, cat_id = data.split("_",2)
    prods = CAT_PRODUCTS.get(cat_id, [])
    product = next((p for p in prods if p["id"]==prod_id), None)
    if not product:
        await call.answer("Товар не найден", show_alert=True)
        return
    text = f"<b>{product['name']}</b>\nЦена: {product['price']}₽"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Оформить заказ", callback_data=f"order_{prod_id}_{cat_id}")
    ]])
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

async def do_order(call: CallbackQuery, data: str):
    # data = "order_XXX_YYY"
    _, prod_id, cat_id = data.split("_",2)
    prods = CAT_PRODUCTS.get(cat_id, [])
    product = next((p for p in prods if p["id"]==prod_id), None)
    if not product:
        await call.answer("Товар не найден", show_alert=True)
        return
    user_name = call.from_user.first_name
    user_id = call.from_user.id
    text = (
        f"📦 <b>Новый заказ</b>\n\n"
        f"🔹 <b>Товар:</b> {product['name']}\n"
        f"💰 <b>Цена:</b> {product['price']}₽\n\n"
        f"👤 <b>Клиент:</b> {user_name}\n"
        f"🆔 <b>ID:</b> {user_id}"
    )
    await bot.send_message(MANAGER_ID, text, parse_mode="HTML")
    await call.answer("✅ Заказ оформлен!", show_alert=True)

# --------------- ФУНКЦИИ ДЛЯ «ПОДГРУПП iPHONE / AppleWatch» ------------------

async def show_sub_iphone(call: CallbackQuery, subId: str):
    """
    Если в фиде нет отдельных категорий для "iPhone 16 Pro Max" и т.д.,
    придётся фильтровать товары из iPhone ID, скажем, IPHONE_ID,
    по названию (или model).
    """
    if not IPHONE_ID:
        await call.answer("Категория iPhone не найдена в фиде", show_alert=True)
        return

    # Получаем все товары, где categoryId = IPHONE_ID
    prods = CAT_PRODUCTS.get(IPHONE_ID, [])
    # Фильтруем по subId
    # subId == "i16promax" -> ищем "16 Pro Max" в названии?
    subName = None
    if subId == "i16promax":
        subName = "iPhone 16 Pro Max"
        wantedText = "16 Pro Max"
    elif subId == "i16pro":
        subName = "iPhone 16 Pro"
        wantedText = "16 Pro"
    elif subId == "i16plus":
        subName = "iPhone 16 Plus"
        wantedText = "16 Plus"
    elif subId == "i16":
        subName = "iPhone 16"
        wantedText = "16"
    else:
        subName = "iPhone ???"
        wantedText = ""

    # Фильтруем товары
    filtered = []
    for p in prods:
        nm = p["name"].lower()
        if wantedText.lower() in nm:
            filtered.append(p)

    # Дальше делаем пагинацию, если товаров много
    total = len(filtered)
    total_pages = ceil(total/ITEMS_PER_PAGE) if total else 1
    page = 0
    # Можно сделать data = f"subi_{subId}_{page}"
    # Но для простоты сейчас просто выведем всё одним списком, ограничив 1-2 страницы
    # (Чтобы показать логику)

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    start_i = page*ITEMS_PER_PAGE
    end_i = start_i+ITEMS_PER_PAGE
    page_items = filtered[start_i:end_i]

    for p in page_items:
        btn_text = f"{p['name']} - {p['price']}₽"
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"prod_{p['id']}_{IPHONE_ID}"
            )
        ])

    text = f"<b>{subName}</b>\n"
    if len(filtered)==0:
        text += "\nНет товаров, удовлетворяших этому подгруппе."
    else:
        text += f"\nНайдено товаров: {len(filtered)} (показаны {len(page_items)})"

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


async def show_sub_aw(call: CallbackQuery, subId: str):
    """
    Аналогичный подход для Apple Watch,
    либо, если есть в фиде отдельные cat_id, можно show_category(cat_id).
    """
    if not APPLEWATCH_ID:
        await call.answer("Категория Apple Watch не найдена", show_alert=True)
        return

    # Способ 1 (если нет отдельных cat_id):
    # Фильтруем товары AppleWatchID
    prods = CAT_PRODUCTS.get(APPLEWATCH_ID, [])
    wantedText = ""
    subName = ""
    if subId == "aw7":
        subName = "Apple Watch Series 7"
        wantedText = "series 7"
    elif subId == "aw8":
        subName = "Apple Watch Series 8"
        wantedText = "series 8"
    else:
        subName = "AW ???"
        wantedText = ""

    filtered = []
    for p in prods:
        if wantedText.lower() in p["name"].lower():
            filtered.append(p)

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for p in filtered:
        btn_text = f"{p['name']} - {p['price']}₽"
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"prod_{p['id']}_{APPLEWATCH_ID}"
            )
        ])

    text = f"<b>{subName}</b>\n"
    if len(filtered) == 0:
        text += "\nНет товаров."
    else:
        text += f"\nНайдено товаров: {len(filtered)}"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


async def main():
    await init_session()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    await close_session()

if __name__ == "__main__":
    asyncio.run(main())
