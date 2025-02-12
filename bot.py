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

# ============= НАСТРОЙКИ ============
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

# --- ЗАДАННЫЙ ПОРЯДОК КОРНЕВЫХ КАТЕГОРИЙ ПО ИМЕНИ ---
# Если название в фиде совпадает, мы сортируем в указанном порядке.
# Остальные категории (не в списке) идут после, по алфавиту.
ROOT_ORDER = {
    "iPhone": 1,
    "Apple Watch": 2,
    "iPad": 3,
    "MacBook": 4,
    "Дополнения JCID": 5,  # Если в фиде точное имя "Дополнения JCID"
    "Инструменты": 6
}

async def init_session():
    global session
    if session is None:
        session = aiohttp.ClientSession()

async def close_session():
    global session
    if session:
        await session.close()
        session = None

async def fetch_feed(force: bool = False):
    global last_update_time, CATEGORIES, CAT_ROOTS, CAT_PRODUCTS
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
                    print(f"Ошибка {resp.status} при загрузке фида.")
                    return
                xml_text = await resp.text()

            data = xmltodict.parse(xml_text)
            shop = data["yml_catalog"]["shop"]

            CATEGORIES.clear()
            CAT_ROOTS.clear()
            CAT_PRODUCTS.clear()

            # Парсим категории
            raw_cats = shop["categories"]["category"]
            if isinstance(raw_cats, dict):
                raw_cats = [raw_cats]

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


def get_entries_for_category(cat_id: str):
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


def build_category_page_kb(cat_id: str, page: int = 0):
    all_entries = get_entries_for_category(cat_id)
    total = len(all_entries)
    from math import ceil
    total_pages = ceil(total / ITEMS_PER_PAGE) if total else 1

    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    start_i = page * ITEMS_PER_PAGE
    end_i = start_i + ITEMS_PER_PAGE
    page_entries = all_entries[start_i:end_i]

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for e in page_entries:
        if e["type"] == "cat":
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=e["name"],
                    callback_data=f"cat_{e['id']}_0"
                )
            ])
        else:
            btn_text = f"{e['name']} - {e['price']}₽"
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"prod_{e['id']}_{cat_id}"
                )
            ])

    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"cat_{cat_id}_{page-1}"
            )
        )
    if page < total_pages - 1:
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
    await fetch_feed()

    if not CATEGORIES:
        await message.answer("Каталог пуст или не удалось загрузить фид.", parse_mode="HTML")
        return

    # Собираем список (id, name) для корневых
    root_list = []
    for r in CAT_ROOTS:
        cat_name = CATEGORIES[r]["name"]
        root_list.append({"id": r, "name": cat_name})

    # --- СОРТИРОВКА КОРНЕВЫХ КАТЕГОРИЙ ---
    # 1) Сначала те, что есть в ROOT_ORDER (по порядку 1..6),
    # 2) Затем остальные (не в списке), по алфавиту.
    def root_key(item):
        # item = {"id":..., "name":...}
        nm = item["name"]
        # Если есть в ROOT_ORDER, вернём ROOT_ORDER[nm], иначе 999 + имя
        if nm in ROOT_ORDER:
            return (0, ROOT_ORDER[nm])  # (0, приоритет)
        else:
            # Ставим (1, nm) чтобы они шли после
            return (1, nm.lower())
    
    root_list.sort(key=root_key)

    total = len(root_list)
    total_pages = ceil(total / ITEMS_PER_PAGE) if total else 1
    page = 0

    start_i = page * ITEMS_PER_PAGE
    end_i = start_i + ITEMS_PER_PAGE
    page_entries = root_list[start_i:end_i]

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for e in page_entries:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=e["name"],
                callback_data=f"cat_{e['id']}_0"
            )
        ])

    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"roots_{page-1}"
            )
        )
    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=f"roots_{page+1}"
            )
        )
    if nav_row:
        kb.inline_keyboard.append(nav_row)

    text = "<b>Выберите категорию:</b>"
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.callback_query()
async def callback_router(call: CallbackQuery):
    data = call.data

    # Пагинация по корневым: "roots_{page}"
    if data.startswith("roots_"):
        page_str = data.split("_", 1)[1]
        page = int(page_str)

        root_list = []
        for r in CAT_ROOTS:
            cat_name = CATEGORIES[r]["name"]
            root_list.append({"id": r, "name": cat_name})

        # Сортируем как выше
        def root_key(item):
            nm = item["name"]
            if nm in ROOT_ORDER:
                return (0, ROOT_ORDER[nm])
            else:
                return (1, nm.lower())
        root_list.sort(key=root_key)

        total = len(root_list)
        total_pages = ceil(total / ITEMS_PER_PAGE) if total else 1
        if page < 0:
            page = 0
        if page >= total_pages:
            page = total_pages - 1

        start_i = page * ITEMS_PER_PAGE
        end_i = start_i + ITEMS_PER_PAGE
        page_entries = root_list[start_i:end_i]

        kb = InlineKeyboardMarkup(inline_keyboard=[])
        for e in page_entries:
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=e["name"],
                    callback_data=f"cat_{e['id']}_0"
                )
            ])

        nav_row = []
        if page > 0:
            nav_row.append(
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"roots_{page-1}"
                )
            )
        if page < total_pages - 1:
            nav_row.append(
                InlineKeyboardButton(
                    text="Вперёд ➡️",
                    callback_data=f"roots_{page+1}"
                )
            )
        if nav_row:
            kb.inline_keyboard.append(nav_row)

        await call.message.edit_text("<b>Выберите категорию:</b>", reply_markup=kb, parse_mode="HTML")

    # Переход/пагинация внутри категории: "cat_{cat_id}_{page}"
    elif data.startswith("cat_"):
        parts = data.split("_")
        cat_id = parts[1]
        page = int(parts[2]) if len(parts) > 2 else 0

        kb, cur_page, total_pages = build_category_page_kb(cat_id, page)

        cat_data = CATEGORIES.get(cat_id)
        cat_name = cat_data["name"] if cat_data else "Без названия"

        entries_count = len(get_entries_for_category(cat_id))
        text = f"<b>{cat_name}</b>\n"
        if entries_count == 0:
            text += "\nВ этой категории нет ни подкатегорий, ни товаров."
        else:
            text += f"\nСтраница {cur_page+1} / {total_pages}"

        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    # Товар: "prod_{prod_id}_{cat_id}"
    elif data.startswith("prod_"):
        _, prod_id, cat_id = data.split("_", 2)
        products = CAT_PRODUCTS.get(cat_id, [])
        product = next((p for p in products if p["id"] == prod_id), None)
        if not product:
            await call.answer("Товар не найден", show_alert=True)
            return

        name = product["name"]
        price = product["price"]

        text = f"<b>{name}</b>\nЦена: {price}₽"

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="Оформить заказ",
                    callback_data=f"order_{prod_id}_{cat_id}"
                )
            ]]
        )

        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    # Оформление заказа: "order_{prod_id}_{cat_id}"
    elif data.startswith("order_"):
        _, prod_id, cat_id = data.split("_", 2)
        products = CAT_PRODUCTS.get(cat_id, [])
        product = next((p for p in products if p["id"] == prod_id), None)
        if not product:
            await call.answer("Товар не найден", show_alert=True)
            return

        user_name = call.from_user.first_name
        user_id = call.from_user.id
        name = product["name"]
        price = product["price"]

        order_text = (
            f"📦 <b>Новый заказ</b>\n\n"
            f"🔹 <b>Товар:</b> {name}\n"
            f"💰 <b>Цена:</b> {price}₽\n\n"
            f"👤 <b>Клиент:</b> {user_name}\n"
            f"🆔 <b>ID:</b> {user_id}"
        )

        await bot.send_message(MANAGER_ID, order_text, parse_mode="HTML")
        await call.answer("✅ Заказ оформлен! Менеджер свяжется с вами.", show_alert=True)

    else:
        await call.answer("Неизвестная команда")


async def main():
    await init_session()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    await close_session()

if __name__ == "__main__":
    asyncio.run(main())
