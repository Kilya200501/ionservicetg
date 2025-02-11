import asyncio
import requests
import xmltodict
from aiogram import Bot, Dispatcher
from aiogram.types import (Message, CallbackQuery,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.filters import Command

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# 1. Настройки
# Вставьте токен вашего Телеграм-бота
TOKEN = "8102076873:AAHf_fPaG5n2tr5C1NnoOVJ62MnIo-YbRi8"

# Адрес Yandex YML-фида
FEED_URL = "https://ion-master.ru/index.php?route=extension/feed/yandex_yml"

# ID менеджера (продавца), который будет получать заказы
MANAGER_ID = 5300643604
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

# Инициализация бота и диспетчера (aiogram 3.x)
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()


def get_products_from_feed():
    """
    Скачивает Yandex YML-фид, парсит XML и возвращает список товаров
    в формате [{'id': ..., 'name':..., 'price':..., 'description':...}, ...].

    Исходим из структуры (упрощённо):
      <yml_catalog>
        <shop>
          <offers>
            <offer id="33" available="true">
              <name>...</name>
              <price>...</price>
              <description>...</description>
              ...
            </offer>
            ...
          </offers>
        </shop>
      </yml_catalog>
    """
    try:
        response = requests.get(FEED_URL, timeout=10)
        if response.status_code != 200:
            print(f"Ошибка при загрузке фида: {response.status_code}")
            return []

        # Парсим XML в словарь
        data = xmltodict.parse(response.content)

        # Извлекаем список offer
        offers = data["yml_catalog"]["shop"]["offers"]["offer"]
        # Если всего один <offer>, xmltodict вернёт dict вместо list — превратим в list
        if isinstance(offers, dict):
            offers = [offers]

        products = []
        for offer in offers:
            prod_id = offer.get("@id")      # <offer id="33" ...>
            name = offer.get("name")        # <name>Товар</name>
            price = offer.get("price")      # <price>12345</price>
            desc = offer.get("description") # <description>Описание...</description>

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
    Показываем список товаров (название + цена) из YML-фида.
    """
    products = get_products_from_feed()
    if not products:
        await message.answer("Не удалось загрузить товары (фид пуст или ошибка).")
        return

    kb = InlineKeyboardMarkup()
    for p in products:
        pid = p["id"]
        pname = p["name"]
        pprice = p["price"]
        # Пример текста кнопки: "Дисплей iPhone 16 Pro Max - 25000₽"
        button_text = f"{pname} - {pprice}₽"
        kb.add(InlineKeyboardButton(text=button_text, callback_data=f"prod_{pid}"))

    await message.answer("Список товаров (из Yandex YML фида):", reply_markup=kb)


@dp.callback_query()
async def callback_handler(call: CallbackQuery):
    """
    1) Выбор товара: prod_<ID>
    2) Оформление заказа: order_<ID>
    """
    data = call.data

    # 1. Если пользователь выбрал товар
    if data.startswith("prod_"):
        product_id = data.split("_")[1]
        products = get_products_from_feed()
        product = next((p for p in products if p["id"] == product_id), None)
        if not product:
            await call.answer("Товар не найден в фиде", show_alert=True)
            return

        # Описание
        name = product["name"]
        price = product["price"]
        desc = product["description"] or "Нет описания"

        text = (
            f"<b>{name}</b>\n"
            f"Цена: {price}₽\n\n"
            f"{desc}"
        )

        # Добавляем кнопку «Оформить заказ»
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(text="🛒 Оформить заказ",
                                   callback_data=f"order_{product_id}"))
        # При желании можно добавить кнопку «Назад» или другие

        await call.message.edit_text(text, reply_markup=kb)

    # 2. Если пользователь оформляет заказ
    elif data.startswith("order_"):
        product_id = data.split("_")[1]
        products = get_products_from_feed()
        product = next((p for p in products if p["id"] == product_id), None)
        if not product:
            await call.answer("Товар не найден", show_alert=True)
            return

        user_name = call.from_user.first_name
        user_id = call.from_user.id

        # Собираем данные заказа
        name = product["name"]
        price = product["price"]
        text_for_manager = (
            f"📦 <b>Новый заказ</b>\n\n"
            f"🔹 <b>Товар:</b> {name}\n"
            f"💰 <b>Цена:</b> {price}₽\n\n"
            f"👤 <b>Клиент:</b> {user_name}\n"
            f"🆔 <b>ID:</b> {user_id}"
        )

        # Отправляем менеджеру
        try:
            await bot.send_message(MANAGER_ID, text_for_manager)
        except Exception as e:
            print(f"Не удалось отправить сообщение менеджеру: {e}")

        # Сообщаем пользователю
        await call.answer("✅ Заказ оформлен! Менеджер скоро свяжется с вами.", show_alert=True)

    else:
        await call.answer("Неизвестная команда")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
