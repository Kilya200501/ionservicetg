import asyncio
import requests
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
TOKEN = "8102076873:AAHf_fPaG5n2tr5C1NnoOVJ62MnIo-YbRi8"  # <-- Вставьте реальный токен бота
FEED_URL = "https://ion-master.ru/index.php?route=extension/feed/yandex_yml"
MANAGER_ID = 5300643604  # ID менеджера для уведомлений о заказе

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Словари для хранения результата фида
CATEGORIES = {}        # cat_id -> cat_name
CATEGORY_PRODUCTS = {} # cat_id -> список товаров (dict)

def load_feed():
    """
    Скачиваем YML-фид, парсим XML и заполняем:
      - CATEGORIES (cat_id -> cat_name)
      - CATEGORY_PRODUCTS (cat_id -> [ {id, name, price, count}, ... ])
    Пропускаем фото/описание (picture/description).
    """
    global CATEGORIES, CATEGORY_PRODUCTS
    CATEGORIES.clear()
    CATEGORY_PRODUCTS.clear()

    try:
        resp = requests.get(FEED_URL, timeout=10)
        if resp.status_code != 200:
            print(f"Ошибка при загрузке фида: {resp.status_code}")
            return

        data = xmltodict.parse(resp.content)
        shop = data["yml_catalog"]["shop"]

        # 1) Считываем <categories>
        raw_cats = shop["categories"]["category"]
        if isinstance(raw_cats, dict):
            raw_cats = [raw_cats]

        for c in raw_cats:
            cat_id = c["@id"]
            cat_name = c.get("#text", "Без названия")
            CATEGORIES[cat_id] = cat_name

        # 2) Считываем <offers>
        raw_offers = shop["offers"]["offer"]
        if isinstance(raw_offers, dict):
            raw_offers = [raw_offers]

        for offer in raw_offers:
            prod_id = offer.get("@id")
            cat_id = offer.get("categoryId")
            name = offer.get("name") or "Без названия"
            price = offer.get("price") or "0"
            count = offer.get("count") or "0"

            if cat_id not in CATEGORY_PRODUCTS:
                CATEGORY_PRODUCTS[cat_id] = []
            CATEGORY_PRODUCTS[cat_id].append({
                "id": prod_id,
                "name": name,
                "price": price,
                "count": count
            })

    except Exception as e:
        print("Ошибка парсинга фида:", e)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """
    При /start загружаем фид и показываем все категории (одним списком).
    """
    load_feed()
    if not CATEGORIES:
        await message.answer("Не удалось загрузить категории (фид пуст или ошибка).")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cat_id, cat_name in CATEGORIES.items():
        # Кнопка для категории
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=cat_name, callback_data=f"cat_{cat_id}")
        ])

    await message.answer("Выберите категорию:", reply_markup=kb)

@dp.callback_query()
async def callback_handler(call: CallbackQuery):
    """
    1) cat_{id} -> показываем товары данной категории
    2) prod_{id}_{cat_id} -> показываем детали товара (только имя, цена, кол-во) + "Оформить заказ"
    3) order_{id}_{cat_id} -> оформить заказ, уведомление менеджеру
    """
    data = call.data

    # --- 1) Выбор категории ---
    if data.startswith("cat_"):
        cat_id = data.split("_")[1]
        cat_name = CATEGORIES.get(cat_id, "Без названия")

        # Получаем товары в этой категории (может быть список или пусто)
        products = CATEGORY_PRODUCTS.get(cat_id, [])
        if not products:
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
            text_btn = f"{pname} — {pprice}₽ (кол: {pcount})"
            kb.inline_keyboard.append([
                InlineKeyboardButton(text=text_btn, callback_data=f"prod_{pid}_{cat_id}")
            ])

        await call.message.edit_text(
            f"Товары в категории <b>{cat_name}</b>:",
            reply_markup=kb
        )

    # --- 2) Подробно о товаре ---
    elif data.startswith("prod_"):
        # формат: "prod_{прод_id}_{кат_id}"
        _, prod_id, cat_id = data.split("_")
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
            f"Наличие: {count} шт."
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="Оформить заказ",
                callback_data=f"order_{prod_id}_{cat_id}"
            )
        ]])

        await call.message.edit_text(text, reply_markup=kb)

    # --- 3) Оформление заказа ---
    elif data.startswith("order_"):
        _, prod_id, cat_id = data.split("_")
        products = CATEGORY_PRODUCTS.get(cat_id, [])
        product = next((x for x in products if x["id"] == prod_id), None)
        if not product:
            await call.answer("Товар не найден", show_alert=True)
            return

        name = product["name"]
        price = product["price"]
        user_name = call.from_user.first_name
        user_id = call.from_user.id

        order_text = (
            f"📦 <b>Новый заказ</b>\n\n"
            f"🔹 <b>Товар:</b> {name}\n"
            f"💰 <b>Цена:</b> {price}₽\n\n"
            f"👤 <b>Клиент:</b> {user_name}\n"
            f"🆔 <b>ID:</b> {user_id}"
        )

        # Отправляем менеджеру
        try:
            await bot.send_message(MANAGER_ID, order_text)
        except Exception as e:
            print(f"Ошибка при отправке менеджеру: {e}")

        # Уведомляем пользователя
        await call.answer("✅ Заказ оформлен! Менеджер скоро свяжется с вами.", show_alert=True)

    else:
        await call.answer("Неизвестная команда")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
