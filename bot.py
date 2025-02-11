import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Dispatcher
from aiogram.types import Message
from aiogram import Bot
import asyncio

# Инициализация
TOKEN = "8083923455:AAFwD2nAD5oPSeA16TrYjAgk_X2tw49F5n4"
bot = Bot(token=TOKEN)
dp = Dispatcher(bot=bot)

# Обработчик /start
@dp.message(lambda message: message.text == "/start")
async def start(message: Message):
    await message.answer("Привет! Бот работает на aiogram 3.x")

async def main():
    await dp.start_polling(bot)

if _name_ == "_main_":
    asyncio.run(main())

# Токен от BotFather
TOKEN = "8083923455:AAFwD2nAD5oPSeA16TrYjAgk_X2tw49F5n4"

# Логирование
logging.basicConfig(level=logging.INFO)

# Создаем бота и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Главное меню (Категории товаров)
main_menu = InlineKeyboardMarkup(row_width=2)
main_menu.add(
    InlineKeyboardButton("📱 iPhone", callback_data="category_iphone"),
    InlineKeyboardButton("⌚ Apple Watch", callback_data="category_watch"),
    InlineKeyboardButton("💻 MacBook", callback_data="category_macbook"),
    InlineKeyboardButton("📟 iPad", callback_data="category_ipad"),
)

# Подкатегории iPhone (Пример)
iphone_menu = InlineKeyboardMarkup(row_width=2)
iphone_menu.add(
    InlineKeyboardButton("iPhone 16 Pro Max", callback_data="iphone_16_pro_max"),
    InlineKeyboardButton("iPhone 16 Pro", callback_data="iphone_16_pro"),
    InlineKeyboardButton("iPhone 15 Pro Max", callback_data="iphone_15_pro_max"),
    InlineKeyboardButton("⬅️ Назад", callback_data="back_main")
)

# Запчасти для iPhone 16 Pro Max
iphone_16_pro_max_parts = InlineKeyboardMarkup(row_width=2)
iphone_16_pro_max_parts.add(
    InlineKeyboardButton("🔧 Дисплей", callback_data="part_display_16_pro_max"),
    InlineKeyboardButton("🔋 Батарея", callback_data="part_battery_16_pro_max"),
    InlineKeyboardButton("📸 Камера", callback_data="part_camera_16_pro_max"),
    InlineKeyboardButton("🔊 Динамики", callback_data="part_speakers_16_pro_max"),
    InlineKeyboardButton("⬅️ Назад", callback_data="back_iphone")
)

# Запчасти для iPhone 16 Pro
iphone_16_pro_parts = InlineKeyboardMarkup(row_width=2)
iphone_16_pro_parts.add(
    InlineKeyboardButton("🔧 Дисплей", callback_data="part_display_16_pro"),
    InlineKeyboardButton("🔋 Батарея", callback_data="part_battery_16_pro"),
    InlineKeyboardButton("📸 Камера", callback_data="part_camera_16_pro"),
    InlineKeyboardButton("🔊 Динамики", callback_data="part_speakers_16_pro"),
    InlineKeyboardButton("⬅️ Назад", callback_data="back_iphone")
)

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("👋 Привет! Я помощник компании *Ion Service*.\n"
                         "Я помогу вам подобрать запчасти для техники Apple.\n\n"
                         "Выберите категорию товара:", reply_markup=main_menu)

# Обработчик выбора категории
@dp.callback_query_handler(lambda call: call.data.startswith("category_"))
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
@dp.callback_query_handler(lambda call: call.data == "iphone_16_pro_max")
async def iphone_16_pro_max_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите запчасть для *iPhone 16 Pro Max*:", reply_markup=iphone_16_pro_max_parts)

# Обработчик выбора iPhone 16 Pro
@dp.callback_query_handler(lambda call: call.data == "iphone_16_pro")
async def iphone_16_pro_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите запчасть для *iPhone 16 Pro*:", reply_markup=iphone_16_pro_parts)

# Обработчик возврата в главное меню
@dp.callback_query_handler(lambda call: call.data == "back_main")
async def back_main_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите категорию товара:", reply_markup=main_menu)

# Обработчик возврата в меню iPhone
@dp.callback_query_handler(lambda call: call.data == "back_iphone")
async def back_iphone_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите модель iPhone:", reply_markup=iphone_menu)

# Обработчик выбора запчастей
@dp.callback_query_handler(lambda call: call.data.startswith("part_"))
async def part_callback(call: types.CallbackQuery):
    part_names = {
        "part_display_16_pro_max": "🔧 Дисплей для iPhone 16 Pro Max\n💰 Цена: 500$",
        "part_battery_16_pro_max": "🔋 Батарея для iPhone 16 Pro Max\n💰 Цена: 150$",
        "part_camera_16_pro_max": "📸 Камера для iPhone 16 Pro Max\n💰 Цена: 200$",
        "part_speakers_16_pro_max": "🔊 Динамики для iPhone 16 Pro Max\n💰 Цена: 100$",
        
        "part_display_16_pro": "🔧 Дисплей для iPhone 16 Pro\n💰 Цена: 480$",
        "part_battery_16_pro": "🔋 Батарея для iPhone 16 Pro\n💰 Цена: 140$",
        "part_camera_16_pro": "📸 Камера для iPhone 16 Pro\n💰 Цена: 190$",
        "part_speakers_16_pro": "🔊 Динамики для iPhone 16 Pro\n💰 Цена: 90$",
    }
    
    text = part_names.get(call.data, "Запчасть не найдена.")
    back_button = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Назад", callback_data="back_iphone"))
    
    await call.message.edit_text(text, reply_markup=back_button)

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
