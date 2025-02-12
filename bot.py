import asyncio
import time
import aiohttp
import xmltodict

from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command

# ------------------- НАСТРОЙКИ -------------------
TOKEN = "8102076873:AAHf_fPaG5n2tr5C1NnoOVJ62MnIo-YbRi8"  # Вставьте реальный токен бота
FEED_URL = "https://ion-master.ru/index.php?route=extension/feed/yandex_yml"
MANAGER_ID = 5300643604  # ID менеджера для уведомлений о заказе

CACHE_TTL = 300  # 5 минут (время кэширования фида)

bot = Bot(token=TOKEN)  # Убрали parse_mode
dp = Dispatcher()

# Структуры для кэша (категории и товары + время последнего обновления)
CATEGORIES = {}       # cat_id -> {id, parent, name, children: [...]}
CAT_ROOTS = []        # список корневых категорий
CAT_PRODUCTS = {}     # cat_id -> [ {id, name, price}, ... ]
last_update_time = 0.0
feed_lock = asyncio.Lock()
session = None  # aiohttp.ClientSession


async def init_session():
    """Создаём глобальную aiohttp-сессию один раз при старте."""
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
    Скачивает и парсит YML-фид. Кэшируем на CACHE_TTL (5 минут).
    Если (now - last_update_time) < CACHE_TTL и force=False — не перезагружаем.
    """
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

            # === Загружаем категории ===
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

            # Связываем в дерево
            for cid, cat_data in CATEGORIES.items():
                pid = cat_data["parent"]
                if pid and pid in CATEGORIES:
                    CATEGORIES[pid]["children"].append(cid)
                else:
                    CAT_ROOTS.append(cid)

            # === Загружаем товары (offers) ===
            raw_offers = shop["offers"]["offer"]
            if isinstance(raw_offers, dict):
                raw_offers = [raw_offers]

            for off in raw_offers:
                prod_id = off.get("@id")
                cat_id = off.get("categoryId")
                name = off.get("name", "Без названия")
                price = off.get("price", "0")

                if not cat_id:
                    continue

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
    """
    При /start: подгружаем (или из кэша) фид, показываем корневые категории.
    """
    await init_session()
    await fetch_feed()

    if not CATEGORIES:
        # Здесь используем parse_mode="HTML", так как хотим bold, но не обязательно
        await message.answer("Каталог пуст или не удалось загрузить фид.", parse_mode="HTML")
        return

    if not CAT_ROOTS:
        await message.answer("Нет корневых категорий.", parse_mode="HTML")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for root_id in CAT_ROOTS:
        name = CATEGORIES[root_id]["name"]
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=name,
                callback_data=f"cat_{root_id}"
            )
        ])

    await message.answer("<b>Выберите категорию:</b>", reply_markup=kb, parse_mode="HTML")


@dp.callback_query()
async def callback_router(call: CallbackQuery):
    data = call.data

    # cat_{id} -> категория
    if data.startswith("cat_"):
        cat_id = data.split("_", 1)[1]
        cat_data = CATEGORIES.get(cat_id)
        if not cat_data:
            await call.answer("Категория не найдена", show_alert=True)
            return

        subcats = cat_data["children"]
        prods = CAT_PRODUCTS.get(cat_id, [])

        kb = InlineKeyboardMarkup(inline_keyboard=[])

        # Подкатегории
        if subcats:
            for scid in subcats:
                sc_name = CATEGORIES[scid]["name"]
                kb.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=sc_name,
                        callback_data=f"cat_{scid}"
                    )
                ])

        # Товары
        if prods:
            for p in prods:
                pid = p["id"]
                pname = p["name"]
                pprice = p["price"]
                btn_text = f"{pname} - {pprice}₽"
                kb.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=btn_text,
                        callback_data=f"prod_{pid}_{cat_id}"
                    )
                ])

        text = f"<b>{cat_data['name']}</b>\n"

        if subcats:
            text += "\nПодкатегории:"
        if prods:
            text += "\n\nТовары:"
        if (not subcats) and (not prods):
            text += "\n\nНет подкатегорий и товаров."

        # edit_text с parse_mode="HTML", т. к. используем <b> в тексте
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    # prod_{prod_id}_{cat_id} -> товар
    elif data.startswith("prod_"):
        _, prod_id, cat_id = data.split("_", 2)
        products = CAT_PRODUCTS.get(cat_id, [])
        product = next((x for x in products if x["id"] == prod_id), None)
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

    # order_{prod_id}_{cat_id} -> оформить заказ
    elif data.startswith("order_"):
        _, prod_id, cat_id = data.split("_", 2)
        products = CAT_PRODUCTS.get(cat_id, [])
        product = next((x for x in products if x["id"] == prod_id), None)
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

        # Отправляем менеджеру (с parse_mode="HTML")
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
