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
MANAGER_IDS = [631954003]  # <-- Вставь Telegram ID менеджеров

# Создаем бота и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Главное меню
main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📱 iPhone", callback_data="category_iphone")],
])

# Обработчик команды /start
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("👋 Привет! Я помощник компании Ion Service!\nВыберите категорию:", reply_markup=main_menu)

# Список моделей iPhone
iphone_models = [
    "16_pro_max", "16_pro", "16_plus", "15_pro_max", "15_pro", "15_plus",
    "14_pro_max", "14_pro", "14_plus", "14", "13_pro_max", "13_pro", "13",
    "12_pro_max", "12_pro", "12", "11_pro_max", "11_pro", "11",
    "xr", "xs_max", "xs", "x", "8_plus", "8", "7_plus", "7"
]

# Меню моделей iPhone
iphone_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=f"iPhone {model.replace('_', ' ').title()}", callback_data=f"iphone_{model}")]
    for model in iphone_models
] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]])

# Функция для генерации подкатегорий для каждой модели
def generate_subcategories(model):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Корпус", callback_data=f"corpus_{model}")],
        [InlineKeyboardButton(text="Дисплей", callback_data=f"display_{model}")],
        [InlineKeyboardButton(text="Основная камера", callback_data=f"camera_main_{model}")],
        [InlineKeyboardButton(text="Фронтальная камера", callback_data=f"camera_front_{model}")],
        [InlineKeyboardButton(text="Аккумулятор", callback_data=f"battery_{model}")],
        [InlineKeyboardButton(text="Шлейф зарядки", callback_data=f"flex_{model}")],
        [InlineKeyboardButton(text="Динамик", callback_data=f"speaker_{model}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_iphone")],
    ])

# Подключаем подкатегории ко всем моделям
subcategories_menu = {f"iphone_{model}": generate_subcategories(model) for model in iphone_models}

# Товары для каждой модели iPhone
products = {
    # iPhone 16 Pro Max
    "corpus_16_pro_max": [
        ("Средняя часть", "18,000₽", "order_16_pro_max_mid"),
        ("Задняя крышка", "21,000₽", "order_16_pro_max_back"),
    ],
    "display_16_pro_max": [
        ("Оригинальный снятый дисплей", "44,000₽ (идеал)", "order_16_pro_max_display"),
    ],

    # iPhone 15 Pro Max
    "corpus_15_pro_max": [
        ("Средняя часть", "10,000₽", "order_15_pro_max_mid"),
        ("Задняя крышка", "23,000₽", "order_15_pro_max_back"),
    ],
    "display_15_pro_max": [
        ("Оригинальный снятый дисплей", "32,000₽ (хорошее состояние)", "order_15_pro_max_display"),
    ],

    # iPhone 14 Pro Max
    "corpus_14_pro_max": [
        ("Средняя часть eSIM", "10,000₽", "order_14_pro_max_mid"),
        ("Задняя крышка", "21,000₽", "order_14_pro_max_back"),
    ],
    "display_14_pro_max": [
        ("Оригинальный снятый дисплей", "30,000₽ (отличное состояние)", "order_14_pro_max_display"),
    ],
}

# Функция генерации клавиатуры с товарами
def generate_product_keyboard(category):
    if category not in products or not products[category]:  # Проверяем, есть ли товары
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_subcategory")]
        ])

    keyboard = InlineKeyboardMarkup()  # Исправлено
    for name, price, callback in products[category]:
        keyboard.add(InlineKeyboardButton(f"{name} - {price}", callback_data=callback))

    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_subcategory"))
    return keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])  # Исправлено
    for name, price, callback in products[category]:
        keyboard.inline_keyboard.append([InlineKeyboardButton(f"{name} - {price}", callback_data=callback)])

    keyboard.inline_keyboard.
append([InlineKeyboardButton("⬅️ Назад", callback_data="back_subcategory")])
    return keyboard

# Обработчик выбора подкатегории
@dp.callback_query(lambda call: call.data.startswith(("corpus_", "display_", "camera_", "battery_", "flex_", "speaker_")))
async def subcategory_callback(call: types.CallbackQuery):
    category = call.data
    keyboard = generate_product_keyboard(category)

    try:
        await call.message.delete()  # Удаляем старое сообщение
        await call.message.answer(f"Вы выбрали: {category.split('_')[0].title()}.\nВыберите товар:", reply_markup=keyboard)
    except Exception as e:
        await call.answer(f"Ошибка: {e}", show_alert=True)

# Функция запуска бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
