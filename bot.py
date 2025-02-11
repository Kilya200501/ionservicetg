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

# Товары для всех моделей iPhone
products = {}
for model in iphone_models:
    products[f"corpus_{model}"] = [
        ("Средняя часть", "18,000₽", f"order_{model}_mid"),
        ("Задняя крышка", "21,000₽", f"order_{model}_back"),
    ]
    products[f"display_{model}"] = [
        ("Оригинальный снятый дисплей", "44,000₽ (идеал)", f"order_{model}_display"),
    ]
    products[f"camera_main_{model}"] = [
        ("Основная камера", "9,000₽", f"order_{model}_main_camera"),
    ]
    products[f"camera_front_{model}"] = [
        ("Фронтальная камера", "2,500₽", f"order_{model}_front_camera"),
    ]
    products[f"battery_{model}"] = [
        ("Аккумулятор 100%", "6,000₽", f"order_{model}_battery"),
    ]
    products[f"flex_{model}"] = [
        ("Шлейф зарядки", "5,500₽", f"order_{model}_flex"),
    ]
    products[f"speaker_{model}"] = [
        ("Полифонический динамик", "500₽", f"order_{model}_speaker"),
    ]

# Функция генерации клавиатуры с товарами
def generate_product_keyboard(category):
    if category not in products:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_subcategory")]
        ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(f"{name} - {price}", callback_data=callback)]
        for name, price, callback in products[category]
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_subcategory")])
    return keyboard

# Обработчик команды /start
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("👋 Привет! Я помощник компании Ion Service!\nВыберите категорию:", reply_markup=main_menu)

# Обработчик выбора категории "iPhone"
@dp.callback_query(lambda call: call.data == "category_iphone")
async def category_callback(call: types.CallbackQuery):
    await call.message.edit_text("Выберите модель iPhone:", reply_markup=iphone_menu)

# Обработчик выбора модели iPhone
@dp.callback_query(lambda call: call.data.startswith("iphone_"))
async def iphone_model_callback(call: types.CallbackQuery):
    model = call.data.replace("iphone_", "").replace("_", " ").title()
    await call.message.edit_text(f"Вы выбрали {model}.\nВыберите категорию:", reply_markup=subcategories_menu.get(call.data, main_menu))

# Обработчик выбора подкатегории (Корпус, Дисплей и т. д.)

@dp.callback_query(lambda call: call.data.startswith(("corpus_", "display_", "camera_", "battery_", "flex_", "speaker_")))
async def subcategory_callback(call: types.CallbackQuery):
    category = call.data
    keyboard = generate_product_keyboard(category)

    
    # Обработчик выбора товара
@dp.callback_query(lambda call: call.data.startswith("order_"))
async def order_callback(call: types.CallbackQuery):
    product_found = None

    # Поиск выбранного товара
    for category, items in products.items():
        for name, price, callback in items:
            if call.data == callback:
                product_found = (name, price)
                break
        if product_found:
            break

    if product_found:
        name, price = product_found
        user_name = call.from_user.first_name
        user_id = call.from_user.id

        order_text = (
            f"📦 **Новый заказ!**\n\n"
            f"🔹 Товар: {name}\n"
            f"💰 Цена: {price}\n\n"
            f"👤 Клиент: [{user_name}](tg://user?id={user_id})\n"
            f"🆔 ID клиента: `{user_id}`"
        )

if keyboard.inline_keyboard:  # Проверяем, есть ли кнопки с товарами
        await call.message.edit_text(f"Вы выбрали: {category.split('_')[0].title()}.\nВыберите товар:", reply_markup=keyboard)
    else:
        await call.answer("🔹 В этой категории пока нет товаров.", show_alert=True)

        # Отправляем заказ менеджерам
        for manager_id in MANAGER_IDS:
            await bot.send_message(manager_id, order_text, parse_mode="Markdown")

        # Подтверждение клиенту
        await call.message.answer(f"✅ Заказ оформлен!\n\n🔹 Товар: {name}\n💰 Цена: {price}\n\nМенеджер скоро свяжется с вами.")
    else:
        await call.answer("⚠️ Ошибка: товар не найден.", show_alert=True)

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

# Функция запуска бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

