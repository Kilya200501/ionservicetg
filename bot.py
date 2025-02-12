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

# Время кэширования (в секундах) — бот не будет перезапрашивать фид, пока
# не пройдёт 5 минут.
CACHE_TTL = 300

# Создаём бота и диспетчер
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

# ---- Глобальные структуры для кэша ----
CATEGORIES = {}       # cat_id -> {id, parent, name, children: [...]}
CAT_ROOTS = []        # список корневых категорий
CAT_PRODUCTS = {}     # cat_id -> [ {id, name, price}, ... ]
last_update_time = 0.0
feed_lock = asyncio.Lock()  # для исключения параллельной загрузки

session = None  # aiohttp.ClientSession (создаём и закрываем при старте/остановке)


async def init_session():
    """Создаём глобальную aiohttp-сессию единожды."""
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
    Скачивает и парсит YML-фид, строит дерево категорий, список товаров.
    Кэшируем на 5 минут, чтобы не грузить фид при каждом запросе.
    """
    global last_update_time, CATEGORIES, CAT_ROOTS, CAT_PRODUCTS
    now = time.time()

    if not force and (now - last_update_time) < CACHE_TTL:
        # Кэш ещё актуален
        return

    async with feed_lock:
        # Пока ждали блокировку, мог другой поток обновить
        now = time.time()
        if not force and (now - last_update_time) < CACHE_TTL:
            return

        try:
            # Загружаем фид из FEED_URL
            async with session.get(FEED_URL, timeout=10) as resp:
                if resp.status != 200:
                    print(f"Ошибка {resp.status} при загрузке фида")
                    return
                xml_text = await resp.text()

            data = xmltodict.parse(xml_text)
            shop = data["yml_catalog"]["shop"]

            # Очищаем старые данные
            CATEGORIES.clear()
            CAT_ROOTS.clear()
            CAT_PRODUCTS.clear()

            # === 1) Считываем категории ===
            raw_cats = shop["categories"]["category"]
            if isinstance(raw_cats, dict):
                raw_cats = [raw_cats]

            # Сначала формируем словари
            for c in raw_cats:
                cat_id = c["@id"]
                parent_id = c.get("@parentId")  # может быть None
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
                    # корневая категория
                    CAT_ROOTS.append(cid)

            # === 2) Считываем товары (offers) ===
            raw_offers = shop["offers"]["offer"]
            if isinstance(raw_offers, dict):
                raw_offers = [raw_offers]

            for off in raw_offers:
                prod_id = off.get("@id")
                cat_id = off.get("categoryId")
                name = off.get("name", "Без названия")
                price = off.get("price", "0")
                # count = off.get("count")  # не показываем пользователю

                if not cat_id:
                    # Если почему-то нет categoryId, пропустим
                    continue

                if cat_id not in CAT_PRODUCTS:
                    CAT_PRODUCTS[cat_id] = []
                CAT_PRODUCTS[cat_id].append({
                    "id": prod_id,
                    "name": name,
                    "price": price
                })

            # Успешно обновили кэш
            last_update_time = time.time()

        except Exception as e:
            print("Ошибка при загрузке/парсинге фида:", e)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """
    При /start: загружаем (из кэша или с сервера) фид, 
    выводим корневые категории.
    """
    await init_session()
    await fetch_feed()

    if not CATEGORIES:
        await message.answer("Каталог пуст или не удалось загрузить фид.")
        return

    if not CAT_ROOTS:
        await message.answer("Нет корневых категорий.")
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

    await message.answer("Выберите категорию:", reply_markup=kb)


@dp.callback_query()
async def callback_router(call: CallbackQuery):
    data = call.data

    # --- "cat_<id>" — пользователь выбрал категорию ---
    if data.startswith("cat_"):
        cat_id = data.split("_", 1)[1]
        cat_data = CATEGORIES.get(cat_id)
        if not cat_data:
            await call.answer("Категория не найдена", show_alert=True)
            return

        # Дочерние категории
        subcats = cat_data["children"]
        # Товары в этой категории
        prods = CAT_PRODUCTS.get(cat_id, [])

        # Формируем список кнопок (сначала субкатегории, потом товары)
        kb = InlineKeyboardMarkup(inline_keyboard=[])

        # Если есть подкатегории
        if subcats:
            for scid in subcats:
                sc_name = CATEGORIES[scid]["name"]
                kb.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=sc_name,
                        callback_data=f"cat_{scid}"
                    )
                ])

        # Если есть товары
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

        # Генерируем текст
        text = f"<b>{cat_data['name']}</b>\n"
        if subcats:
            text += "\nПодкатегории:"
        if prods:
            text += "\n\nТовары:"

        if (not subcats) and (not prods):
            text += "\n\nВ этой категории нет ни подкатегорий, ни товаров."

        await call.message.edit_text(text, reply_markup=kb)

    # --- "prod_<prod_id>_<cat_id>" — пользователь выбрал товар ---
    elif data.startswith("prod_"):
        _, prod_id, cat_id = data.split("_", 2)
        products = CAT_PRODUCTS.get(cat_id, [])
        product = next((x for x in products if x["id"] == prod_id), None)
        if not product:
            await call.answer("Товар не найден", show_alert=True)
            return

        name = product["name"]
        price = product["price"]

        text = (
            f"<b>{name}</b>\n"
            f"Цена: {price}₽"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="Оформить заказ",
                    callback_data=f"order_{prod_id}_{cat_id}"
                )
            ]]
        )

        await call.message.edit_text(text, reply_markup=kb)

    # --- "order_<prod_id>_<cat_id>" — Оформить заказ ---
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

        await bot.send_message(MANAGER_ID, order_text)
        await call.answer("✅ Заказ оформлен! Менеджер свяжется с вами.", show_alert=True)

    else:
        await call.answer("Неизвестная команда.")


async def main():
    # Инициализируем aiohttp-сессию
    await init_session()
    # Сбрасываем старый webhook (если был) и очищаем очередь апдейтов
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем бота (long-polling)
    await dp.start_polling(bot)
    # При остановке (Ctrl+C) закрываем сессию
    await close_session()

if __name__ == "__main__":
    asyncio.run(main())
