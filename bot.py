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


@dp.callback_query(lambda call: call.data == "category_iphone")
async def category_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите модель iPhone:", reply_markup=iphone_menu)

@dp.callback_query(lambda call: call.data.startswith("iphone_"))
async def iphone_model_callback(call: types.CallbackQuery):
    model = call.data.replace("iphone_", "").replace("_", " ").title()
    await call.message.edit_text(f"Вы выбрали {model}.\nВыберите категорию:", reply_markup=subcategories_menu.get(call.data, main_menu))

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

# Обработчик выбора подкатегории (Корпус, Дисплей и т. д.)
@dp.callback_query(lambda call: call.data.startswith(("corpus_", "display_", "camera_", "battery_", "flex_", "speaker_")))
async def subcategory_callback(call: types.CallbackQuery):
    category = call.data
    await call.message.edit_text(f"Вы выбрали: {category.split('_')[0].title()}.\nВыберите товар:", reply_markup=generate_product_keyboard(category))

# Обработчик кнопки "Назад" в меню моделей iPhone
@dp.callback_query(lambda call: call.data == "back_iphone")
async def back_iphone_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите модель iPhone:", reply_markup=iphone_menu)

# Обработчик кнопки "Назад" в главное меню
@dp.callback_query(lambda call: call.data == "back_main")
async def back_main_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите категорию:", reply_markup=main_menu)

# Обработчик кнопки "Назад" в подкатегории
@dp.callback_query(lambda call: call.data == "back_subcategory")
async def back_subcategory_callback(call: types.CallbackQuery):
    model_key = call.message.text.split("**")[1].lower().replace(" ", "_")
    await call.message.edit_text("Выберите категорию:", reply_markup=subcategories_menu.get(f"iphone_{model_key}", main_menu))

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

# Товары (добавлены все, которые ты отправил)
products = {
    # iPhone 16 Pro Max
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
    "battery_16_pro_max": [
        ("Аккумулятор 100%", "6,000₽", "order_16_pro_max_battery"),
    ],
    "flex_16_pro_max": [
        ("Шлейф зарядки", "5,500₽", "order_16_pro_max_flex"),
    ],
    "speaker_16_pro_max": [
        ("Полифонический динамик", "500₽", "order_16_pro_max_speaker"),
    ],
    
    # iPhone 15 Pro Max
    "corpus_15_pro_max": [
        ("Корпус в отличном состоянии", "23,000₽", "order_15_pro_max_body_perfect"),
        ("Корпус в хорошем состоянии", "22,000₽", "order_15_pro_max_body_good"),
        ("Средняя часть", "10,000₽", "order_15_pro_max_mid"),
    ],
    "display_15_pro_max": [
        ("Оригинальный снятый дисплей", "32,000₽ (хорошее состояние)", "order_15_pro_max_display"),
    ],
    "camera_main_15_pro_max": [
        ("Основная камера", "3,000₽", "order_15_pro_max_main_camera"),
    ],
    "camera_front_15_pro_max": [
        ("Фронтальная камера", "1,000₽", "order_15_pro_max_front_camera"),
    ],
    "battery_15_pro_max": [
        ("Аккумулятор 100%", "3,000₽", "order_15_pro_max_battery"),
    ],
    "flex_15_pro_max": [
        ("Шлейф зарядки", "4,500₽", "order_15_pro_max_flex"),
    ],
    "speaker_15_pro_max": [("Полифонический динамик", "300₽", "order_15_pro_max_speaker"),
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

# Функция обработки заказа
@dp.callback_query(lambda call: call.data.startswith("order_"))
async def order_callback(call: types.CallbackQuery):
    user_name = call.from_user.first_name
    user_id = call.from_user.id

    # Получаем информацию о заказе
    for category, items in products.items():
        for name, price, callback in items:
            if call.data == callback:
                model = category.split("_")[1:]
                model_name = " ".join(model).title().replace("_", " ")
                order_text = (
                    f"📦 **Новый заказ!**\n\n"
                    f"📱 Модель: {model_name}\n"
                    f"🔹 Товар: {name}\n"
                    f"💰 Цена: {price}\n\n"
                    f"👤 Клиент: [{user_name}](tg://user?id={user_id})\n"
                    f"🆔 ID клиента: `{user_id}`"
                )

                for manager_id in MANAGER_IDS:
                    await bot.send_message(manager_id, order_text, parse_mode="Markdown")
                
                await call.message.answer("✅ Ваш заказ отправлен менеджеру. Скоро с вами свяжутся!")

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("👋 Привет! Я помощник компании Ion Service!\nВыберите категорию:", reply_markup=main_menu)

# Функция запуска бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)  # Очистка Webhook
    await dp.start_polling(bot)  # Запуск бота

if __name__ == "__main__":
    asyncio.run(main())  # Запускаем асинхронный цикл
