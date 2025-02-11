import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart

# Получаем токен из переменной окружения
TOKEN = os.getenv("8083923455:AAFwD2nAD5oPSeA16TrYjAgk_X2tw49F5n4")

# Проверяем, есть ли токен
if not TOKEN: 
    raise ValueError("Ошибка: переменная окружения TOKEN не установлена!")

# Создаем бота и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Главное меню (категории товаров)
main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📱 iPhone", callback_data="category_iphone")],
    [InlineKeyboardButton(text="⌚ Apple Watch", callback_data="category_watch")],
    [InlineKeyboardButton(text="💻 MacBook", callback_data="category_macbook")],
    [InlineKeyboardButton(text="📟 iPad", callback_data="category_ipad")],
])

# Подкатегории iPhone
iphone_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="iPhone 16 Pro Max", callback_data="iphone_16_pro_max")],
    [InlineKeyboardButton(text="iPhone 16 Pro", callback_data="iphone_16_pro")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
])

# Запчасти для iPhone 16 Pro Max
iphone_16_pro_max_parts = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔧 Дисплей", callback_data="part_display")],
    [InlineKeyboardButton(text="🔋 Батарея", callback_data="part_battery")],
    [InlineKeyboardButton(text="📸 Камера", callback_data="part_camera")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_iphone")],
])

# Обработчик команды /start
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("👋 Привет! Я помощник компании Ion Service!\nВыберите категорию:", reply_markup=main_menu)

# Обработчик выбора категории
@dp.callback_query(lambda call: call.data.startswith("category_"))
async def category_callback(call: types.CallbackQuery):
    if call.data == "category_iphone":
        await call.message.edit_text("Выберите модель iPhone:", reply_markup=iphone_menu)
    elif call.data == "category_watch":
        await call.message.edit_text("Выберите модель Apple Watch (меню в разработке).")
    elif call.data == "category_macbook":
        await call.message.edit_text("Выберите модель MacBook (меню в разработке).")
    elif call.data == "category_ipad":
        await call.message.edit_text("Выберите модель iPad (меню в разработке).")

# Обработчик выбора iPhone 16 Pro Max
@dp.callback_query(lambda call: call.data == "iphone_16_pro_max")
async def iphone_16_pro_max_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите запчасть для *iPhone 16 Pro Max*:", reply_markup=iphone_16_pro_max_parts)

# Обработчик кнопки "Назад" в главное меню
@dp.callback_query(lambda call: call.data == "back_main")
async def back_main_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите категорию:", reply_markup=main_menu)

# Обработчик кнопки "Назад" в меню iPhone
@dp.callback_query(lambda call: call.data == "back_iphone")
async def back_iphone_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите модель iPhone:", reply_markup=iphone_menu)

# Обработчик выбора запчастей (пример)
@dp.callback_query(lambda call: call.data.startswith("part_"))
async def part_callback(call: types.CallbackQuery):
    parts = {
        "part_display": "🔧 Дисплей для iPhone 16 Pro Max\n💰 Цена: 500$",
        "part_battery": "🔋 Батарея для iPhone 16 Pro Max\n💰 Цена: 150$",
        "part_camera": "📸 Камера для iPhone 16 Pro Max\n💰 Цена: 200$",
    }
    text = parts.get(call.data, "Запчасть не найдена.")
    back_button = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("⬅️ Назад", callback_data="back_iphone")]])
    
    await call.message.edit_text(text, reply_markup=back_button)

# Функция запуска бота
async def main():
    dp.include_router(dp)  # Подключаем маршрутизацию
    await bot.delete_webhook(drop_pending_updates=True)  # Убираем старые сообщения
    await dp.start_polling(bot)  # Запускаем бота

if __name__ == "__main__":
    asyncio.run(main())  # Запускаем асинхронный цикл
