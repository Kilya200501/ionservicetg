import asyncio
import time
import aiohttp
from math import ceil

from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command

# ======================= НАСТРОЙКИ ========================

# 1) Токен МойСклад (Bearer), полученный под пользователем, который видит папки
BEARER_TOKEN = "8a9dee615a9199934cce481008091fcf465c98cf"

# 2) Базовый URL МойСклад
BASE_URL = "https://online.moysklad.ru/api/remap/1.2"

# 3) ID менеджера (TG user) для уведомлений о заказе
MANAGER_ID = 5300643604

# 4) Время кэширования (в сек). Пока не истечёт, бот не будет заново грузить
CACHE_TTL = 300

# 5) Макс. кол-во позиций (папки/товары) на странице в Телеграм
ITEMS_PER_PAGE = 10

# 6) Токен Телеграм-бота
TOKEN = "8102076873:AAHf_fPaG5n2tr5C1NnoOVJ62MnIo-YbRi8"

# ----------------------------------------------------------

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Глобальные структуры
CATEGORIES = {}       # cat_id -> {id, parent, name, children: [...]}
CAT_ROOTS = []        # список корневых папок
CAT_PRODUCTS = {}     # cat_id -> [ {id, name, price}, ... ]
last_update_time = 0.0
fetch_lock = asyncio.Lock()

# aiohttp.Session и заголовок для МойСклад
session = None
headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}"
}


# ====================== ФУНКЦИИ =======================

async def init_session():
    """Создаем aiohttp.ClientSession один раз."""
    global session
    if session is None:
        session = aiohttp.ClientSession()


async def close_session():
    """Закрываем при выходе."""
    global session
    if session:
        await session.close()
        session = None


async def fetch_all_productfolders():
    """
    Запрашиваем все папки (productfolder) (с пагинацией МойСклад).
    Выводим отладку: status и часть data.
    """
    rows = []
    limit = 100
    offset = 0
    while True:
        url = f"{BASE_URL}/entity/productfolder?limit={limit}&offset={offset}"
        print(f"Запрос папок: {url}")
        async with session.get(url, headers=headers) as resp:
            print("Status (folders) =", resp.status)
            data = await resp.json()
            print("Data (folder) part =", str(data)[:500])  # печатаем первые 500 символов
            chunk = data.get("rows", [])
            rows.extend(chunk)
            meta = data.get("meta", {})
            size = meta.get("size", 0)
            if offset+limit >= size:
                break
            offset+=limit
    return rows


async def fetch_all_products():
    """
    Запрашиваем все товары (product) (с пагинацией).
    Аналогично выводим отладку.
    """
    rows = []
    limit = 100
    offset = 0
    while True:
        url = f"{BASE_URL}/entity/product?limit={limit}&offset={offset}"
        print(f"Запрос товаров: {url}")
        async with session.get(url, headers=headers) as resp:
            print("Status (products) =", resp.status)
            data = await resp.json()
            print("Data (product) part =", str(data)[:500])
            chunk = data.get("rows", [])
            rows.extend(chunk)
            meta = data.get("meta", {})
            size = meta.get("size", 0)
            if offset+limit >= size:
                break
            offset+=limit
    return rows


async def fetch_data(force=False):
    """
    Кэшируем данные. Если (time - last_update_time) < CACHE_TTL, пропускаем.
    """
    global last_update_time, CATEGORIES, CAT_ROOTS, CAT_PRODUCTS
    now = time.time()
    if not force and (now - last_update_time) < CACHE_TTL:
        return

    async with fetch_lock:
        now = time.time()
        if not force and (now - last_update_time) < CACHE_TTL:
            return

        # 1) грузим папки
        folder_rows = await fetch_all_productfolders()
        # 2) грузим товары
        product_rows = await fetch_all_products()

        # Очищаем
        CATEGORIES.clear()
        CAT_ROOTS.clear()
        CAT_PRODUCTS.clear()

        # Построение дерева папок
        for f in folder_rows:
            folder_id = f["id"]  # GUID
            parent_meta = f.get("parentFolder")
            parent_id = None
            if parent_meta and "meta" in parent_meta:
                href = parent_meta["meta"]["href"]
                parent_id = href.split("/")[-1]
            name = f.get("name","Без названия")

            CATEGORIES[folder_id] = {
                "id": folder_id,
                "parent": parent_id,
                "name": name,
                "children": []
            }

        # Связываем, определяем корни
        for cid, cat_data in CATEGORIES.items():
            pid = cat_data["parent"]
            if pid and pid in CATEGORIES:
                CATEGORIES[pid]["children"].append(cid)
            else:
                CAT_ROOTS.append(cid)

        # Список товаров
        for p in product_rows:
            prod_id = p["id"]
            name = p.get("name","Без названия")
            sale_price = 0
            sale_prices = p.get("salePrices",[])
            if sale_prices:
                sale_price = sale_prices[0].get("value",0)/100
            folder_meta = p.get("productFolder")
            cat_id = None
            if folder_meta and "meta" in folder_meta:
                href = folder_meta["meta"]["href"]
                cat_id = href.split("/")[-1]
            if cat_id:
                if cat_id not in CAT_PRODUCTS:
                    CAT_PRODUCTS[cat_id] = []
                CAT_PRODUCTS[cat_id].append({
                    "id": prod_id,
                    "name": name,
                    "price": sale_price
                })

        last_update_time = time.time()
        print("Данные из МойСклад обновлены. Папок:", len(CATEGORIES), "Товаров:", sum(len(v) for v in CAT_PRODUCTS.values()))


def get_entries(cat_id: str):
    """
    Подкатегории + товары (вместе) => для пагинации в Telegram.
    """
    entries = []
    cat_data = CATEGORIES.get(cat_id)
    if cat_data:
        for scid in cat_data["children"]:
            sc_name = CATEGORIES[scid]["name"]
            entries.append({
                "type": "cat",
                "id": scid,
                "name": sc_name
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
    Пагинация списка (подкатегории + товары).
    """
    all_entries = get_entries(cat_id)
    total = len(all_entries)
    total_pages = ceil(total/ITEMS_PER_PAGE) if total else 1
    if page<0: page=0
    if page>=total_pages: page=total_pages-1

    start_i = page*ITEMS_PER_PAGE
    end_i = start_i+ITEMS_PER_PAGE
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
            btn_txt = f"{e['name']} - {e['price']}₽"
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=btn_txt,
                    callback_data=f"prod_{e['id']}_{cat_id}"
                )
            ])

    nav_row=[]
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

    # Покажем корневые категории
    root_list = []
    for r in CAT_ROOTS:
        nm = CATEGORIES[r]["name"]
        root_list.append((r, nm))
    # Сортируем
    root_list.sort(key=lambda x: x[1].lower())

    total = len(root_list)
    total_pages = ceil(total/ITEMS_PER_PAGE) if total else 1
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

    text = "<b>Выберите категорию (МойСклад):</b>"
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query()
async def callback_router(call: CallbackQuery):
    data = call.data

    if data.startswith("roots_"):
        # Пагинация корневых
        page_str = data.split("_",1)[1]
        page = int(page_str)

        root_list = []
        for r in CAT_ROOTS:
            nm = CATEGORIES[r]["name"]
            root_list.append((r,nm))
        root_list.sort(key=lambda x: x[1].lower())

        total = len(root_list)
        total_pages = ceil(total/ITEMS_PER_PAGE) if total else 1
        if page<0: page=0
        if page>=total_pages: page=total_pages-1

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

        await call.message.edit_text(
            "<b>Выберите категорию (МойСклад):</b>",
            parse_mode="HTML",
            reply_markup=kb
        )

    elif data.startswith("cat_"):
        # cat_{cat_id}_{page}
        parts = data.split("_")
        cat_id = parts[1]
        page = int(parts[2])
        kb, cur_page, total_pages = build_kb_for_category(cat_id, page)
        cat_name = CATEGORIES[cat_id]["name"] if cat_id in CATEGORIES else "???"
        all_ents = get_entries(cat_id)
        cnt = len(all_ents)
        text = f"<b>{cat_name}</b>\n"
        if cnt==0:
            text += "\n(Пусто.)"
        else:
            text += f"\nСтраница {cur_page+1}/{total_pages}"
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data.startswith("prod_"):
        # prod_{prod_id}_{cat_id}
        _, prod_id, cat_id = data.split("_",2)
        prods = CAT_PRODUCTS.get(cat_id,[])
        product = next((p for p in prods if p["id"]==prod_id), None)
        if not product:
            await call.answer("Товар не найден", show_alert=True)
            return
        text = f"<b>{product['name']}</b>\nЦена: {product['price']}₽"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="Оформить заказ",
                    callback_data=f"order_{prod_id}_{cat_id}"
                )
            ]]
        )
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

    elif data.startswith("order_"):
        # order_{prod_id}_{cat_id}
        _, prod_id, cat_id = data.split("_",2)
        prods = CAT_PRODUCTS.get(cat_id,[])
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

    else:
        await call.answer("Неизвестная команда")


async def main():
    await init_session()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    await close_session()

if __name__=="__main__":
    asyncio.run(main())
