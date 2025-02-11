import asyncio
import os
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# -------------------------------------------------------------------
# =================== ВАШИ НАСТРОЙКИ ================================
# -------------------------------------------------------------------

# 1) Токен Телеграм-бота
#    Лучше всего указать в переменной окружения TOKEN.
#    Или впишите прямо здесь (менее безопасно).
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Не установлен токен бота! (переменная окружения TOKEN)")

# 2) Базовый URL вашего сайта (REST API).
#    Например: "https://example.com/api/v1"
BASE_API_URL = "https://example.com/api/v1"

# 3) (Опционально) Ключ/токен для авторизации вашего API.
#    Если API не требует токен, укажите API_KEY = None.
API_KEY = "https://ion-master.ru/"  # или None, если не нужно

# 4) Заголовки для HTTP-запросов (если нужна авторизация).
HEADERS = {}
if API_KEY:
    HEADERS = {
        "Authorization": f"Bearer {API_KEY}"
    }


# -------------------------------------------------------------------
# ========== ФУНКЦИИ ДЛЯ ОБРАЩЕНИЯ К ВАШЕМУ API ======================
# -------------------------------------------------------------------

async def get_categories() -> list:
    """
    Запрашивает список категорий с вашего сайта.
    Ожидаемый JSON (пример):
    [
      {"id": 1, "name": "iPhone"},
      {"id": 2, "name": "iPad"}
      ...
    ]
    """
    url = f"{BASE_API_URL}/categories"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                print(f"Ошибка при запросе категорий: статус {resp.status}")
                return []

async def get_products_by_category(cat_id: int) -> list:
    """
    Запрашивает список товаров в категории cat_id.
    Пример API: GET /categories/<cat_id>/products
    Ожидаемый JSON (пример):
    [
      {"id": 101, "name": "iPhone 16 Pro Max Display", "price": 25000},
      ...
    ]
    """
    url = f"{BASE_API_URL}/categories/{cat_id}/products"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                print(f"Ошибка при запросе товаров для cat_id={cat_id}: статус {resp.status}")
                return []

async def get_product_details(product_id: int) -> dict:
    """
    Запрашивает детальные сведения о товаре с ID = product_id.
    Пример API: GET /products/<product_id>
    Ожидаемый JSON (пример):
    {
      "id": 101,
      "name": "iPhone 16 Pro Max Display",
      "price": 25000,
      "description": "Оригинальный дисплей Apple..."
    }
    """
    url = f"{BASE_API_URL}/products/{product_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                print(f"Ошибка при запросе товара {product_id}: статус {resp.status}")
                return {}

async def create_order(user_id: int, product_id: int, quantity: int = 1) -> dict:
    """
    Создаёт заказ на сайте через POST /orders.
    Ожидаемый формат запроса (пример):
    {
      "user_id": <telegram_user_id>,
      "product_id": <product_id>,
      "quantity": <quantity>
    }
    Возвращаемый JSON (пример):
    {
      "success": true,
      "order_id": 999
    }
    """
    url = f"{BASE_API_URL}/orders"
    payload = {
        "user_id": user_id,
        "product_id": product_id,
        "quantity": quantity
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=HEADERS) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                print(f"Ошибка при создании заказа: статус {resp.status}")
                return {"success": False}


# -------------------------------------------------------------------
# ========== НАСТРОЙКА AIOGRAM (ХЭНДЛЕРЫ) ============================
# -------------------------------------------------------------------

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """
    При команде /start выводим список категорий.
    """
    categories = await get_categories()
    if not categories:
        await message.answer("Не удалось загрузить категории (ошибка API).")
        return

    # Формируем клавиатуру
    kb = InlineKeyboardMarkup()
    for cat in categories:
        cat_id = cat["id"]
        cat_name = cat["name"]
        kb.add(InlineKeyboardButton(text=cat_name, callback_data=f"cat_{cat_id}"))

    await message.answer("Выберите категорию:", reply_markup=kb)

@dp.callback_query()
async def callback_handler(call: CallbackQuery):
    data = call.data

    # 1. Если пользователь выбрал категорию: cat_<cat_id>
    if data.startswith("cat_"):
        cat_id_str = data.split("_")[1]
        cat_id = int(cat_id_str)
        products = await get_products_by_category(cat_id)
        if not products:
            await call.message.edit_text("В этой категории пока нет товаров.")
            return

        # Список товаров
        kb = InlineKeyboardMarkup()
        for p in products:
            prod_id = p["id"]
            prod_name = p["name"]
            kb.add(InlineKeyboardButton(text=prod_name, callback_data=f"prod_{prod_id}"))
        
        # Кнопка «Назад» (возвращает к списку категорий)
        kb.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_categories"))
        await call.message.edit_text("Выберите товар:", reply_markup=kb)

    # 2. Если пользователь выбрал товар: prod_<prod_id>
    elif data.startswith("prod_"):
        prod_id_str = data.split("_")[1]
        prod_id = int(prod_id_str)
        product = await get_product_details(prod_id)
        if not product:
            await call.answer("Товар не найден или ошибка API", show_alert=True)
            return

        name = product.get("name", "Без названия")
        price = product.get("price", 0)
        description = product.get("description", "Описание отсутствует")

        text = (
            f"<b>{name}</b>\n"
            f"Цена: {price}₽\n\n"
            f"{description}"
        )

        kb = InlineKeyboardMarkup()
        # Кнопка «Оформить заказ»
        kb.add(InlineKeyboardButton(text="🛒 Оформить заказ", callback_data=f"order_{prod_id}"))
        # Кнопка «Назад» (опять к списку категорий)
        kb.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_categories"))
        
        await call.message.edit_text(text, reply_markup=kb)

    # 3. Если пользователь нажал «Оформить заказ»: order_<prod_id>
    elif data.startswith("order_"):
        prod_id_str = data.split("_")[1]
        prod_id = int(prod_id_str)

        user_id = call.from_user.id  # ID телеграм-пользователя
        # Допустим, всегда quantity = 1:
        result = await create_order(user_id=user_id, product_id=prod_id, quantity=1)

        if result.get("success"):
            order_id = result.get("order_id", 0)
            await call.answer(f"✅ Заказ оформлен! Номер заказа: {order_id}", show_alert=True)
        else:
            await call.answer("Не удалось оформить заказ (ошибка API).", show_alert=True)

    # 4. Если пользователь нажал «Назад к категориям»: back_to_categories
    elif data == "back_to_categories":
        categories = await get_categories()
        if not categories:
            await call.message.edit_text("Не удалось загрузить категории (ошибка).")
            return

        kb = InlineKeyboardMarkup()
        for cat in categories:
            cat_id = cat["id"]
            cat_name = cat["name"]
            kb.add(InlineKeyboardButton(text=cat_name, callback_data=f"cat_{cat_id}"))

        await call.message.edit_text("Выберите категорию:", reply_markup=kb)


# -------------------------------------------------------------------
# =========================== ЗАПУСК БОТА ============================
# -------------------------------------------------------------------

async def main():
    # Удаляем старый webhook, если был, и очищаем очередь апдейтов
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
