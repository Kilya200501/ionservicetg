import asyncio
import time
import aiohttp
from math import ceil

from aiogram import Bot, Dispatcher
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.filters import Command

# ===================== НАСТРОЙКИ =====================

BEARER_TOKEN = "a0c97969df1cb7910b04d04e1cc8444c29985509"  # ВАШ ТОКЕН ИЗ МОЙСКЛАД
BASE_URL = "https://online.moysklad.ru/api/remap/1.2"
MANAGER_ID = 5300643604  # ID менеджера (кто получает уведомления о заказе)

CACHE_TTL = 300         # (сек) время кэширования (5 минут)
ITEMS_PER_PAGE = 10     # сколько позиций (подкатегории + товары) на странице

# Создаём бота (aiogram 3.7+), без parse_mode
TOKEN = "8102076873:AAHf_fPaG5n2tr5C1NnoOVJ62MnIo-YbRi8" 
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Глобальные структуры
CATEGORIES = {}       # cat_id -> {id, parent, name, children: [...]}
CAT_ROOTS = []        # список корневых (где parent=None)
CAT_PRODUCTS = {}     # cat_id -> [{id, name, price}, ...]
last_update_time = 0.0
fetch_lock = asyncio.Lock()

session = None  # aiohttp.ClientSession, чтобы переиспользовать
headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}"
}


# ===================== ФУНКЦИИ ДЛЯ ЗАПРОСОВ МОЙСКЛАД =====================

async def init_session():
    global session
    if session is None:
        session = aiohttp.ClientSession()


async def close_session():
    global session
    if session:
        await session.close()
        session = None


async def fetch_all_productfolders():
    """
    Запрашивает все папки (группы) товаров, с учётом пагинации МойСклад.
    Результат: суммарный список (rows).
    Документация:
    https://dev.moysklad.ru/doc/api/remap/1.2/dictionaries/#suschnosti-gruppa-towarow
    """
    rows = []
    limit = 100
    offset = 0

    while True:
        url = f"{BASE_URL}/entity/productfolder?limit={limit}&offset={offset}"
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            chunk = data.get("rows", [])
            rows.extend(chunk)
            # Проверяем, есть ли ещё
            meta = data.get("meta", {})
            size = meta.get("size", 0)  # общее число
            if offset + limit >= size:
                break
            offset += limit
    return rows


async def fetch_all_products():
    """
    Запрашивает все товары (product), с учётом пагинации.
    Документация:
    https://dev.moysklad.ru/doc/api/remap/1.2/dictionaries/#suschnosti-towar
    """
    rows = []
    limit = 100
    offset = 0

    while True:
        url = f"{BASE_URL}/entity/product?limit={limit}&offset={offset}"
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            chunk = data.get("rows", [])
            rows.extend(chunk)
            meta = data.get("meta", {})
            size = meta.get("size", 0)
            if offset + limit >= size:
                break
            offset += limit
    return rows


async def fetch_data(force: bool = False):
    """
    Кэшируем на CACHE_TTL. Если (time - last_update_time) < CACHE_TTL,
    не загружаем повторно (если force=False).
    """
    global last_update_time, CATEGORIES, CAT_ROOTS, CAT_PRODUCTS

    now = time.time()
    if not force and (now - last_update_time) < CACHE_TTL:
        return

    async with fetch_lock:
        now = time.time()
        if not force and (now - last_update_time) < CACHE_TTL:
            return

        # Загружаем папки (productFolder)
        folders = await fetch_all_productfolders()
        # Загружаем товары (product)
        products = await fetch_all_products()

        # Очищаем локальные структуры
        CATEGORIES.clear()
        CAT_ROOTS.clear()
        CAT_PRODUCTS.clear()

        # 1) Строим словарь категорий
        for f in folders:
            # Пример f: {
            #   "id": "GUID",
            #   "name": "iPhone",
            #   "productFolder": True,
            #   "pathName": "Apple",
            #   "meta": {...},
            #   "parentFolder": {...} # может указывать на родителя
            # }
            folder_id = f["id"]  # GUID
            parent_meta = f.get("parentFolder")
            parent_id = None
            if parent_meta and "meta" in parent_meta:
                # берём GUID из href
                # обычно "href": "https://online.moysklad.ru/api/remap/1.2/entity/productfolder/xxx"
                href = parent_meta["meta"]["href"]
                parent_id = href.split("/")[-1]  # GUID
            name = f.get("name","Без названия")

            CATEGORIES[folder_id] = {
                "id": folder_id,
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

        # 2) Строим словарь товаров
        for p in products:
            # p может содержать:
            # {
            #   "id": "GUID",
            #   "name": "iPhone 16 Pro",
            #   "productFolder": { "meta": {...}, ...}  # ссылка на папку
            #   "salePrices": [ { "value": 3000000, ... } ]
            #   ...
            # }
            prod_id = p["id"]
            name = p.get("name","Без названия")
            sale_price = 0
            sale_prices = p.get("salePrices", [])
            if sale_prices:
                sale_price = sale_prices[0].get("value", 0) / 100  # в копейках

            folder_meta = p.get("productFolder")
            cat_id = None
            if folder_meta and "meta" in folder_meta:
                href = folder_meta["meta"]["href"]
                cat_id = href.split("/")[-1]  # GUID папки

            if cat_id:
                if cat_id not in CAT_PRODUCTS:
                    CAT_PRODUCTS[cat_id] = []
                CAT_PRODUCTS[cat_id].append({
                    "id": prod_id,
                    "name": name,
                    "price": sale_price
                })

        last_update_time = time.time()


# ============== ПОСТРОЕНИЕ ВЫВОДА ==============

def get_entries(cat_id: str):
    """
    Возвращает список «подкатегории + товары» для категории cat_id
    (вместе, чтобы пагинировать).
    """
    entries = []
    cat_data = CATEGORIES.get(cat_id)
    if cat_data:
        for child_id in cat_data["children"]:
            child_name = CATEGORIES[child_id]["name"]
            entries.append({
                "type": "cat",
                "id": child_id,
                "name": child_name
            })
    prods = CAT_PRODUCTS.get(cat_id, [])
    for p in prods:
        entries.append({
            "type": "prod",
            "id": p["id"],
            "name": p["name"],
            "price": p["price"]
        })
    return entries


def build_kb_for_category(cat_id: str, page=0):
    """
    Пагинация: собираем subcats+products => ITEMS_PER_PAGE на странице.
    """
    all_entries = get_entries(cat_id)
    total = len(all_entries)
    total_pages = ceil(total/ITEMS_PER_PAGE) if total else 1

    # ограничиваем page
    if page<0: page=0
    if page>=total_pages: page=total_pages-1

    start_i = page * ITEMS_PER_PAGE
    end_i = start_i + ITEMS_PER_PAGE
    page_entries = all_entries[start_i:end_i]

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for e in page_entries:
        if e["type"]=="cat":
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=e["name"],
                    callback_data=f"cat_{e['id']}_0"
                )
            ])
        else:
            # товар
            text_btn = f"{e['name']} - {e['price']}₽"
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=text_btn,
                    callback_data=f"prod_{e['id']}_{cat_id}"
                )
            ])

    nav_row = []
    if page>0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"cat_{cat_id}_{page-1}"
            )
        )
    if page<total_pages-1:
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=f"cat_{cat_id}_{page+1}"
            )
        )
    if nav_row:
        kb.inline_keyboard.append(nav_row)

    return kb, page, total_pages


# ============== ХЭНДЛЕРЫ AIROGRAM ==============

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await init_session()
    await fetch_data()

    if not CATEGORIES:
        await message.answer(
            "Каталог пуст или не удалось загрузить данные из МойСклад.",
            parse_mode="HTML"
        )
        return

    # Покажем список корневых категорий
    # (также с пагинацией, если много)
    root_list = []
    for cid in CAT_ROOTS:
        nm = CATEGORIES[cid]["name"]
        root_list.append((cid, nm))

    # Сортируем корневые категории по алфавиту
    root_list.sort(key=lambda x: x[1].lower())

    total = len(root_list)
    total_pages = ceil(total / ITEMS_PER_PAGE) if total else 1
    page = 0

    start_i = page*ITEMS_PER_PAGE
    end_i = start_i+ITEMS_PER_PAGE
    page_entries = root_list[start_i:end_i]

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for (cid,nm) in page_entries:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=nm,
                callback_data=f"cat_{cid}_0"
            )
        ])

    nav_row=[]
    if page>0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"roots_{page-1}"
            )
        )
    if page<total_pages-1:
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=f"roots_{page+1}"
            )
        )
    if nav_row:
        kb.inline_keyboard.append(nav_row)

    text = "<b>Выберите категорию (из МойСклад):</b>"
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query()
async def callback_router(call: CallbackQuery):
    data = call.data

    if data.startswith("roots_"):
        # Пагинация корневых
        page = int(data.split("_",1)[1])
        root_list = []
        for cid in CAT_ROOTS:
            nm = CATEGORIES[cid]["name"]
            root_list.append((cid,nm))
        root_list.sort(key=lambda x: x[1].lower())

        total = len(root_list)
        total_pages = ceil(total/ITEMS_PER_PAGE) if total else 1
        if page<0: page=0
        if page>=total_pages: page=total_pages-1

        start_i = page*ITEM_PER_PAGE
        end_i = start_i+ITEM_PER_PAGE
        page_entries = root_list[start_i:end_i]

        kb = InlineKeyboardMarkup(inline_keyboard=[])
        for (cid,nm) in page_entries:
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=nm,
                    callback_data=f"cat_{cid}_0"
                )
            ])
        nav_row=[]
        if page>0:
            nav_row.append(
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"roots_{page-1}"
                )
            )
        if page<total_pages-1:
            nav_row.append(
                InlineKeyboardButton(
                    text="Вперёд ➡️",
                    callback_data=f"roots_{page+1}"
                )
            )
        if nav_row:
            kb.inline_keyboard.append(nav_row)

        await call.message.edit_text(
            "<b>Выберите категорию (из МойСклад):</b>",
            parse_mode="HTML",
            reply_markup=kb
        )

    elif data.startswith("cat_"):
        # "cat_{cat_id}_{page}"
        parts = data.split("_")
        cat_id = parts[1]
        page = int(parts[2])
        kb, cur_page, total_pages = build_kb_for_category(cat_id, page)
        cat_name = CATEGORIES[cat_id]["name"]
        all_ents = get_entries(cat_id)
        cnt = len(all_ents)
        text = f"<b>{cat_name}</b>\n"
        if cnt==0:
            text+="\nПусто."
        else:
            text+=f"\nСтраница {cur_page+1}/{total_pages}"
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data.startswith("prod_"):
        # "prod_{productGUID}_{catGUID}"
        _, prod_id, cat_id = data.split("_",2)
        # Ищем товар
        prod_list = CAT_PRODUCTS.get(cat_id, [])
        product = next((p for p in prod_list if p["id"]==prod_id), None)
        if not product:
            await call.answer("Товар не найден", show_alert=True)
            return
        text = f"<b>{product['name']}</b>\nЦена: {product['price']}₽"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="Оформить заказ",
                callback_data=f"order_{prod_id}_{cat_id}"
            )
        ]])
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data.startswith("order_"):
        # "order_{productGUID}_{catGUID}"
        _, prod_id, cat_id = data.split("_",2)
        prod_list = CAT_PRODUCTS.get(cat_id, [])
        product = next((p for p in prod_list if p["id"]==prod_id), None)
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

    else:
        await call.answer("Неизвестная команда")

async def main():
    await init_session()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    await close_session()

if __name__=="__main__":
    asyncio.run(main())
