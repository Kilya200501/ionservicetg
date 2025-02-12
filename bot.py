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

# ============== НАСТРОЙКИ ==============
TOKEN = "8102076873:AAHf_fPaG5n2tr5C1NnoOVJ62MnIo-YbRi8"
FEED_URL = "https://ion-master.ru/index.php?route=extension/feed/yandex_yml"
MANAGER_ID = 5300643604  # ID менеджера (для заказов)
CACHE_TTL = 300  # 5 минут
ITEMS_PER_PAGE = 10  # Сколько позиций (подкатегорий + товаров) показывать на одной странице

bot = Bot(token=TOKEN)  # без parse_mode (т.к. aiogram 3.7+)
dp = Dispatcher()

# Глобальные структуры для кэша
CATEGORIES = {}       # cat_id -> {id, parent, name, children: [... child cat_ids ...]}
CAT_ROOTS = []        # список корневых категорий
CAT_PRODUCTS = {}     # cat_id -> [{id, name, price}, ...]
last_update_time = 0.0
feed_lock = asyncio.Lock()
session = None  # aiohttp.ClientSession


async def init_session():
    """Создаём глобальную aiohttp-сессию один раз."""
    global session
    if session is None:
        session = aiohttp.ClientSession()


async def close_session():
    """Закрываем сессию при остановке бота."""
    global session
    if session:
        await session.close()
        session = None


async def fetch_feed(force: bool = False):
    """
    Скачиваем YML-фид, кэшируем на CACHE_TTL.
    Строим дерево категорий (CATEGORIES, CAT_ROOTS) и список товаров (CAT_PRODUCTS).
    """
    global last_update_time, CATEGORIES, CAT_ROOTS, CAT_PRODUCTS
    now = time.time()

    # Если кэш актуален и force=False, не загружаем
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

            # Очищаем
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


# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================

def get_entries_for_category(cat_id: str):
    """
    Собираем единый список «подкатегории + товары» для данной категории:
    - Сначала все дочерние категории (each type='cat')
    - Потом товары (type='prod')
    Возвращаем list of dict: {type: 'cat'/'prod', 'id':..., 'name':..., 'price':...}
    """
    entries = []
    cat_data = CATEGORIES.get(cat_id)
    if cat_data:
        # Добавляем подкатегории
        for scid in cat_data["children"]:
            sc_name = CATEGORIES[scid]["name"]
            entries.append({
                "type": "cat",
                "id": scid,
                "name": sc_name
            })
    # Добавляем товары
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
    """
    Строим клавиатуру для категории cat_id, учитывая пагинацию.
    1. Получаем список «подкатегории + товары» (entries).
    2. Отображаем ITEMS_PER_PAGE штук на странице page.
    3. Кнопка «Назад» и «Вперёд» при необходимости.
    """
    entries = get_entries_for_category(cat_id)
    total = len(entries)
    total_pages = ceil(total / ITEMS_PER_PAGE) if total else 1

    # Нормализуем page
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1

    start_i = page * ITEMS_PER_PAGE
    end_i = start_i + ITEMS_PER_PAGE
    page_entries = entries[start_i:end_i]

    kb = InlineKeyboardMarkup(inline_keyboard=[])

    # Генерируем кнопки
    for e in page_entries:
        if e["type"] == "cat":
            # Подкатегория
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=e["name"],
                    callback_data=f"cat_{e['id']}_0"  # страница 0 внутри подкатегории
                )
            ])
        else:
            # Товар
            name_with_price = f"{e['name']} - {e['price']}₽"
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=name_with_price,
                    callback_data=f"prod_{e['id']}_{cat_id}"
                )
            ])

    # Строка навигации
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"cat_{cat_id}_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"cat_{cat_id}_{page+1}"))
    if nav_row:
        kb.inline_keyboard.append(nav_row)

    return kb, page, total_pages


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """
    При /start загружаем фид (из кэша или заново),
    показываем список корневых категорий (тоже с пагинацией).
    """
    await init_session()
    await fetch_feed()

    if not CATEGORIES:
        await message.answer("Каталог пуст или не удалось загрузить фид.", parse_mode="HTML")
        return

    # Будем считать «корневые» категории как entries
    root_entries = []
    for r in CAT_ROOTS:
        root_entries.append({"type": "cat", "id": r, "name": CATEGORIES[r]["name"]})

    # Пагинация по корневым
    total = len(root_entries)
    total_pages = ceil(total / ITEMS_PER_PAGE) if total > 0 else 1

    page = 0
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    start_i = page * ITEMS_PER_PAGE
    end_i = start_i + ITEMS_PER_PAGE
    page_entries = root_entries[start_i:end_i]

    # Кнопки корневых категорий
    for e in page_entries:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=e["name"],
                callback_data=f"cat_{e['id']}_0"  # 0-я страница в категории
            )
        ])

    # Навигация (если много корневых)
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"roots_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"roots_{page+1}"))
    if nav_row:
        kb.inline_keyboard.append(nav_row)

    text = "<b>Выберите категорию:</b>"
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.callback_query()
async def callback_router(call: CallbackQuery):
    data = call.data

    # 1) Пагинация по корневым
    if data.startswith("roots_"):
        page_str = data.split("_", 1)[1]
        page = int(page_str)

        # Формируем заново корневые
        root_entries = []
        for r in CAT_ROOTS:
            root_entries.append({"type": "cat", "id": r, "name": CATEGORIES[r]["name"]})

        total = len(root_entries)
        total_pages = ceil(total / ITEMS_PER_PAGE) if total else 1
        if page < 0:
            page = 0
        if page >= total_pages:
            page = total_pages - 1

        start_i = page * ITEMS_PER_PAGE
        end_i = start_i + ITEMS_PER_PAGE
        page_entries = root_entries[start_i:end_i]

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
            nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"roots_{page-1}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"roots_{page+1}"))
        if nav_row:
            kb.inline_keyboard.append(nav_row)

        await call.message.edit_text("<b>Выберите категорию:</b>", reply_markup=kb, parse_mode="HTML")

    # 2) Пагинация/переход внутри категории: "cat_{cat_id}_{page}"
    elif data.startswith("cat_"):
        # Пример: "cat_92_0"
        parts = data.split("_")
        cat_id = parts[1]
        page = int(parts[2]) if len(parts) > 2 else 0

        # Строим клавиатуру для cat_id, page
        kb, cur_page, total_pages = build_category_page_kb(cat_id, page)

        cat_data = CATEGORIES.get(cat_id)
        cat_name = cat_data["name"] if cat_data else "Без названия"
        text = f"<b>{cat_name}</b>\n"

        entries_count = len(get_entries_for_category(cat_id))
        if entries_count == 0:
            text += "\nВ этой категории нет ни подкатегорий, ни товаров."
        else:
            text += f"\nСтраница {cur_page+1} / {total_pages}"

        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    # 3) Выбор товара: "prod_{prod_id}_{cat_id}"
    elif data.startswith("prod_"):
        # Пример: "prod_700_92"
        _, prod_id, cat_id = data.split("_", 2)
        products = CAT_PRODUCTS.get(cat_id, [])
        product = next((p for p in products if p["id"] == prod_id), None)
        if not product:
            await call.answer("Товар не найден", show_alert=True)
            return

        name = product["name"]
        price = product["price"]

        text = f"<b>{name}</b>\nЦена: {price}₽"

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="Оформить заказ",
                callback_data=f"order_{prod_id}_{cat_id}"
            )
        ]])

        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    # 4) Оформление заказа: "order_{prod_id}_{cat_id}"
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

        # Отправляем менеджеру
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
