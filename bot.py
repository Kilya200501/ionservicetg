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


# ---------------------- НАСТРОЙКИ ----------------------
TOKEN = "8102076873:AAHf_fPaG5n2tr5C1NnoOVJ62MnIo-YbRi8"  # <-- Вставьте сюда токен вашего бота
FEED_URL = "https://ion-master.ru/index.php?route=extension/feed/yandex_yml"
MANAGER_ID = 5300643604  # ID менеджера, получающего заказы
# -------------------------------------------------------


bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()


def get_products_from_feed():
    """
    Скачиваем Yandex YML-фид, парсим XML (через xmltodict),
    возвращаем список словарей вида:
    [ {"id":..., "name":..., "price":..., "description":...}, ... ]
    """
    try:
        response = requests.get(FEED_URL, timeout=10)
        if response.status_code != 200:
            print(f"Ошибка при загрузке фида: {response.status_code}")
            return []

        data = xmltodict.parse(response.content)
        offers = data["yml_catalog"]["shop"]["offers"]["offer"]
        # Если в фиде всего один <offer>, xmltodict вернёт словарь, а не список
        if isinstance(offers, dict):
            offers = [offers]

        products = []
        for offer in offers:
            prod_id = offer.get("@id")        # <offer id="...">
            name = offer.get("name")          # <name>Название</name>
            price = offer.get("price")        # <price>12345</price>
            desc = offer.get("description")   # <description>...</description>

            products.append({
                "id": prod_id,
                "name": name,
                "price": price,
                "description": desc
            })
        return products

    except Exception as e:
        print("Ошибка при парсинге фида:", e)
        return []


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """
    Загружаем товары из фида и показываем их списком (кнопки) при команде /start.
    """
    products = get_products_from_feed()
    if not products:
        await message.answer("Не удалось загрузить товары (фид пуст или ошибка).")
        return

    # Создаём клавиатуру в формате aiogram 3.x
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for p in products:
        pid = p["id"]
        pname = p["name"] or "Без названия"
        pprice = p["price"] or "0"
        text_btn = f"{pname} - {pprice}₽"

        # Добавляем новую строку с кнопкой (list of list)
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=text_btn, callback_data=f"prod_{pid}")
        ])

    await message.answer("Список товаров (из Yandex YML фида):", reply_markup=kb)


@dp.callback_query()
async def callback_handler(call: CallbackQuery):
    data = call.data

    # --- 1) Пользователь выбрал товар (prod_<id>) ---
    if data.startswith("prod_"):
        product_id = data.split("_")[1]
        products = get_products_from_feed()
        product = next((p for p in products if p["id"] == product_id), None)
        if not product:
            await call.answer("Товар не найден", show_alert=True)
            return

        name = product["name"] or "Без названия"
        price = product["price"] or "0"
        desc = product["description"] or "Нет описания"

        text = (
            f"<b>{name}</b>\n"
            f"Цена: {price}₽\n\n"
            f"{desc}"
        )

        # Кнопка «Оформить заказ»
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="🛒 Оформить заказ",
                callback_data=f"order_{product_id}"
            )
        ]])

        await call.message.edit_text(text, reply_markup=kb)

    # --- 2) Пользователь нажал «Оформить заказ» (order_<id>) ---
    elif data.startswith("order_"):
        product_id = data.split("_")[1]
        products = get_products_from_feed()
        product = next((p for p in products if p["id"] == product_id), None)
        if not product:
            await call.answer("Товар не найден", show_alert=True)
            return

        user_name = call.from_user.first_name
        user_id = call.from_user.id
        name = product["name"]
        price = product["price"]

        # Текст для менеджера
        order_text = (
            f"📦 <b>Новый заказ</b>\n\n"
            f"🔹 <b>Товар:</b> {name}\n"
            f"💰 <b>Цена:</b> {price}₽\n\n"
            f"👤 <b>Клиент:</b> {user_name}\n"
            f"🆔 <b>ID:</b> {user_id}"
        )

        # Шлём менеджеру
        try:
            await bot.send_message(MANAGER_ID, order_text)
        except Exception as e:
            print(f"Ошибка при отправке менеджеру: {e}")

        # Сообщаем пользователю
        await call.answer("✅ Заказ оформлен! Менеджер скоро свяжется с вами.", show_alert=True)

    else:
        await call.answer("Неизвестная команда")


async def main():
    # Удаляем старый webhook, очищаем очередь апдейтов
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем бота в режиме polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
