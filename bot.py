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
TOKEN = "8102076873:AAHf_fPaG5n2tr5C1NnoOVJ62MnIo-YbRi8"  # Вставьте реальный токен
FEED_URL = "https://ion-master.ru/index.php?route=extension/feed/yandex_yml"
MANAGER_ID = 5300643604  # ID менеджера, который получает уведомления

# Время (в секундах) «жизни» кэша (TTL). Пока не истечёт,
# бот не будет снова скачивать/парсить фид.
CACHE_TTL = 300  # 5 минут

# Инициализация бота и диспетчера
bot = Bot(TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Глобальные переменные-кэш
CATEGORIES = {}        # cat_id -> cat_name
CATEGORY_PRODUCTS = {} # cat_id -> [ {id, name, price, count}, ... ]
last_update_time = 0.0 # timestamp последнего обновления кэша
feed_lock = asyncio.Lock()  # асинхронная блокировка для fetch_feed


async def fetch_feed(force: bool = False):
    """
    Асинхронно скачивает YML-фид и парсит его в глобальные структуры:
      - CATEGORIES
      - CATEGORY_PRODUCTS
    Если с момента последней загрузки прошло меньше CACHE_TTL (и force=False),
    повторная загрузка не выполняется (используется кэш).

    Благодаря feed_lock несколько одновременных запросов не вызовут
    двойную загрузку. Остальные будут ждать, пока загрузка завершится.
    """
    global last_update_time, CATEGORIES, CATEGORY_PRODUCTS

    # Проверяем, не актуален ли уже кэш
    now = time.time()
    if not force and (now - last_update_time) < CACHE_TTL:
        # Данные ещё актуальны — выходим
        return

    # Захватываем блокировку, чтобы избежать параллельной загрузки
    async with feed_lock:
        # Может оказаться, что пока мы ждали блокировку,
        # другой поток уже обновил кэш — проверим ещё раз
        now = time.time()
        if not force and (now - last_update_time) < CACHE_TTL:
            return

        print("[fetch_feed] -> Загрузка YML-фида...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(FEED_URL, timeout=10) as resp:
                    if resp.status != 200:
                        print(f"Ошибка {resp.status} при загрузке фида")
                        return
                    xml_text = await resp.text()

            data = xmltodict.parse(xml_text)
            shop = data["yml_catalog"]["shop"]

            # Очищаем структуры
            CATEGORIES.clear()
            CATEGORY_PRODUCTS.clear()

            # 1) Загружаем категории
            raw_cats = shop["categories"]["category"]
            if isinstance(raw_cats, dict):
                # Если в фиде только одна категория
                raw_cats = [raw_cats]
            for c in raw_cats:
                cat_id = c["@id"]
                cat_name = c.get("#text", "Без названия")
                CATEGORIES[cat_id] = cat_name

            # 2) Загружаем товары
            raw_offers = shop["offers"]["offer"]
            if isinstance(raw_offers, dict):
                raw_offers = [raw_offers]

            for offer in raw_offers:
                prod_id = offer.get("@id")
                cat_id = offer.get("categoryId", "0")
                name = offer.get("name", "Без названия")
                price = offer.get("price", "0")
                count = offer.get("count", "0")

                # Сохраняем товары в словаре, сгруппированном по cat_id
                if cat_id not in CATEGORY_PRODUCTS:
                    CATEGORY_PRODUCTS[cat_id] = []
                CATEGORY_PRODUCTS[cat_id].append({
                    "id": prod_id,
                    "name": name,
                    "price": price,
                    "count": count
                })

            last_update_time = time.time()
            print("[fetch_feed] -> Фид успешно загружен и сохранён в кэш.")

        except Exception as e:
            print("Ошибка при загрузке/парсинге фида:", e)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """
    При /start:
    1) Загружаем (или берём из кэша) список категорий
    2) Выводим их в виде кнопок
    """
    await fetch_feed()
    if not CATEGORIES:
        await message.answer("Не удалось загрузить категории (фид пуст или ошибка).")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cat_id, cat_name in CATEGORIES.items():
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=cat_name,
                callback_data=f"cat_{cat_id}"
            )
        ])

    await message.answer("Выберите категорию:", reply_markup=kb)


@dp.callback_query()
async def callback_handler(call: CallbackQuery):
    data = call.data

    # 1) Выбор категории -> "cat_{cat_id}"
    if data.startswith("cat_"):
        cat_id = data.split("_")[1]
        cat_name = CATEGORIES.get(cat_id, "Без названия")
        # Возьмём товары этой категории (или пустой список)
        products = CATEGORY_PRODUCTS.get(cat_id, [])

        if not products:
            # Нет товаров
            await call.message.edit_text(
                f"В категории <b>{cat_name}</b> нет товаров."
            )
            return

        kb = InlineKeyboardMarkup(inline_keyboard=[])
        for p in products:
            pid = p["id"]
            pname = p["name"]
            pprice = p["price"]
            pcount = p["count"]
            button_text = f"{pname} — {pprice}₽ (кол: {pcount})"
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"prod_{pid}_{cat_id}"
                )
            ])

        await call.message.edit_text(
            text=f"Товары в категории <b>{cat_name}</b>:",
            reply_markup=kb
        )

    # 2) Выбор товара -> "prod_{prod_id}_{cat_id}"
    elif data.startswith("prod_"):
        _, prod_id, cat_id = data.split("_", 2)
        products = CATEGORY_PRODUCTS.get(cat_id, [])
        product = next((x for x in products if x["id"] == prod_id), None)
        if not product:
            await call.answer("Товар не найден", show_alert=True)
            return

        name = product["name"]
        price = product["price"]
        count = product["count"]

        text = (
            f"<b>{name}</b>\n"
            f"Цена: {price}₽\n"
            f"Остаток: {count}"
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

    # 3) Оформление заказа -> "order_{prod_id}_{cat_id}"
    elif data.startswith("order_"):
        _, prod_id, cat_id = data.split("_", 2)
        products = CATEGORY_PRODUCTS.get(cat_id, [])
        product = next((x for x in products if x["id"] == prod_id), None)
        if not product:
            await call.answer("Товар не найден", show_alert=True)
            return

        user_name = call.from_user.first_name
        user_id = call.from_user.id

        order_text = (
            f"📦 <b>Новый заказ</b>\n\n"
            f"🔹 <b>Товар:</b> {product['name']}\n"
            f"💰 <b>Цена:</b> {product['price']}₽\n\n"
            f"👤 <b>Клиент:</b> {user_name}\n"
            f"🆔 <b>ID:</b> {user_id}"
        )

        # Отправляем менеджеру
        try:
            await bot.send_message(MANAGER_ID, order_text)
        except Exception as e:
            print(f"Ошибка при отправке менеджеру: {e}")

        await call.answer("✅ Заказ оформлен! Менеджер свяжется с вами.", show_alert=True)

    else:
        await call.answer("Неизвестная команда")


async def main():
    # Удаляем возможный старый webhook и очищаем апдейты
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем бота в режиме polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
