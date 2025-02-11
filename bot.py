import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart

# Получаем токен из переменной окружения
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("Ошибка: переменная окружения TOKEN не установлена!")

# ID менеджеров, которым отправлять заказы (замени на реальные ID)
MANAGER_IDS = [631954003]  # <-- Добавь Telegram ID менеджеров

# Создаем бота и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Главное меню
main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📱 iPhone", callback_data="category_iphone")],
])

# Меню моделей iPhone
iphone_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="iPhone 16 Pro Max", callback_data="iphone_16_pro_max")],
    [InlineKeyboardButton(text="iPhone 16 Pro", callback_data="iphone_16_pro")],
    [InlineKeyboardButton(text="iPhone 16 Plus", callback_data="iphone_16_plus")],
    [InlineKeyboardButton(text="iPhone 15 Pro Max", callback_data="iphone_15_pro_max")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
])

# Подкатегории (Корпус / Дисплей / Камера)
subcategories_menu = {
    "iphone_16_pro_max": InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Корпус", callback_data="corpus_16_pro_max")],
        [InlineKeyboardButton(text="Дисплей", callback_data="display_16_pro_max")],
        [InlineKeyboardButton(text="Основная камера", callback_data="camera_main_16_pro_max")],
        [InlineKeyboardButton(text="Фронтальная камера", callback_data="camera_front_16_pro_max")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_iphone")],
    ]),
}

# Товары
products = {
    "corpus_16_pro_max": [
        ("Средняя часть", "18,000₽", "order_16_pro_max_mid"),
        ("Задняя крышка", "21,000₽", "order_16_pro_max_back"),
    ],
    "display_16_pro_max": [
        ("Оригинальный снятый дисплей", "44,000₽ (идеал)", "order_16_pro_max_display"),
    ],
    "camera_main_16_pro_max": [
        ("Основная камера", "9,000₽", "order_16_pro_max_main_camera"),
    ],
    "camera_front_16_pro_max": [
        ("Фронтальная камера", "2,500₽", "order_16_pro_max_front_camera"),
    ],
}

# Функция генерации клавиатуры с товарами
def generate_product_keyboard(category):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(f"{name} - {price}", callback_data=callback)]
        for name, price, callback in products.get(category, [])
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_subcategory")])
    return keyboard

# Обработчик команды /start
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("👋 Привет! Я помощник компании Ion Service!\nВыберите категорию:", reply_markup=main_menu)

# Обработчик выбора категории
@dp.callback_query(lambda call: call.data == "category_iphone")
async def category_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите модель iPhone:", reply_markup=iphone_menu)

# Обработчик выбора модели iPhone
@dp.callback_query(lambda call: call.data.startswith("iphone_"))
async def iphone_model_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите категорию:", reply_markup=subcategories_menu.get(call.data, main_menu))

# Обработчик выбора подкатегории (Корпус / Дисплей / Камера)
@dp.callback_query(lambda call: call.data.startswith(("corpus_", "display_", "camera_")))
async def subcategory_callback(call: types.CallbackQuery):
    category = call.data
    keyboard = generate_product_keyboard(category)
    await call.message.edit_text("Выберите товар:", reply_markup=keyboard)

# Обработчик возврата в главное меню
@dp.callback_query(lambda call: call.data == "back_main")
async def back_main_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите категорию:", reply_markup=main_menu)

# Обработчик возврата в меню моделей iPhone
@dp.callback_query(lambda call: call.data == "back_iphone")
async def back_iphone_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите модель iPhone:", reply_markup=iphone_menu)

# Обработчик возврата в меню подкатегорий
@dp.callback_query(lambda call: call.data == "back_subcategory")
async def back_subcategory_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите категорию:", reply_markup=subcategories_menu.get(call.message.text, main_menu))

# Обработчик заказа товара
@dp.callback_query(lambda call: call.data.startswith("order_"))
async def order_callback(call: types.CallbackQuery):
    product_mapping = {
        "order_16_pro_max_mid": ("iPhone 16 Pro Max", "Корпус", "Средняя часть", "18,000₽"),
        "order_16_pro_max_back": ("iPhone 16 Pro Max", "Корпус", "Задняя крышка", "21,000₽"),
        "order_16_pro_max_display": ("iPhone 16 Pro Max", "Дисплей", "Оригинальный снятый дисплей", "44,000₽ (идеал)"),
        "order_16_pro_max_main_camera": ("iPhone 16 Pro Max", "Камера", "Основная камера", "9,000₽"),
        "order_16_pro_max_front_camera": ("iPhone 16 Pro Max", "Камера", "Фронтальная камера", "2,500₽"),
    }

    if call.data in product_mapping:
        model, category, product, price = product_mapping[call.data]
        user_id = call.from_user.id
        user_name = call.from_user.first_name

        order_text = (
            f"📦 **Новый заказ!**\n\n"
            f"📱 Модель: {model}\n"
            f"📂 Категория: {category}\n"
            f"🔹 Товар: {product}\n"
            f"💰 Цена: {price}\n\n"
            f"👤 Клиент: [{user_name}](tg://user?id={user_id})\n"
            f"🆔 ID клиента: `{user_id}`"
        )

        # Отправляем заказ менеджерам
        for manager_id in MANAGER_IDS:
            await bot.send_message(manager_id, order_text, parse_mode="Markdown")

        # Подтверждение клиенту
        await call.message.answer("✅ Ваш заказ отправлен менеджеру. Скоро с вами свяжутся!")
    else:
        await call.message.answer("⚠️ Ошибка: товар не найден.")

# Функция запуска бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
