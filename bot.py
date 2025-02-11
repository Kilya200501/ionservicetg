import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart

# Получаем токен из переменных окружения
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("Ошибка: переменная окружения TOKEN не установлена!")

# ID менеджеров, которым отправлять заказы (замените на реальные)
MANAGER_IDS = [631954003]

# Создаем бота и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ============================= Меню =============================

# Главное меню
main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📱 iPhone", callback_data="category_iphone")],
    [InlineKeyboardButton(text="📟 iPad", callback_data="category_ipad")],
    [InlineKeyboardButton(text="⌚ Apple Watch", callback_data="category_watch")],
    [InlineKeyboardButton(text="💻 MacBook", callback_data="category_macbook")],
])

# Меню моделей iPhone
iphone_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="iPhone 16 Pro Max", callback_data="iphone_16_pro_max")],
    [InlineKeyboardButton(text="iPhone 16 Pro", callback_data="iphone_16_pro")],
    [InlineKeyboardButton(text="iPhone 16 Plus", callback_data="iphone_16_plus")],
    [InlineKeyboardButton(text="iPhone 16", callback_data="iphone_16")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
])

# Меню подкатегорий для iPhone 16 Pro Max
iphone_16_pro_max_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Дисплей", callback_data="display_16_pro_max")],
    [InlineKeyboardButton(text="Аккумулятор", callback_data="battery_16_pro_max")],
    [InlineKeyboardButton(text="Корпус", callback_data="corpus_16_pro_max")],
    # Новая кнопка — «Корпус (черный)»
    [InlineKeyboardButton(text="Корпус (черный) - 20 000₽", callback_data="corpus_black_16_pro_max")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_iphone")],
])

# Товар «Дисплей iPhone 16 Pro Max»
display_16_pro_max_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🛒 Оформить заказ", callback_data="order_16_pro_max_display")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_16_pro_max")],
])

# Товар «Корпус (черный) iPhone 16 Pro Max»
corpus_black_16_pro_max_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🛒 Оформить заказ", callback_data="order_16_pro_max_corpus_black")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_16_pro_max")],
])

# ========================== Обработчики ==========================

# /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        text="👋 Здравствуйте! Я помощник компании **ION-Сервис**.\nВыберите категорию:",
        reply_markup=main_menu,
        parse_mode="Markdown"
    )

# Выбор категории (category_*)
@dp.callback_query(F.data.startswith("category_"))
async def category_callback(call: types.CallbackQuery):
    if call.data == "category_iphone":
        await call.message.edit_text(
            text="Выберите модель iPhone:",
            reply_markup=iphone_menu
        )
    else:
        await call.answer("🔹 В этой категории пока нет товаров.", show_alert=True)

# Выбор модели iPhone (iphone_*)
@dp.callback_query(F.data.startswith("iphone_"))
async def iphone_model_callback(call: types.CallbackQuery):
    if call.data == "iphone_16_pro_max":
        await call.message.edit_text(
            text="Выберите категорию для **iPhone 16 Pro Max**:",
            parse_mode="Markdown",
            reply_markup=iphone_16_pro_max_menu
        )
    else:
        await call.answer("🔹 В этой модели пока нет товаров.", show_alert=True)

# Подкатегории (display_*, battery_*, corpus_*)
@dp.callback_query(F.data.startswith(("display_", "battery_", "corpus_")))
async def subcategory_callback(call: types.CallbackQuery):
    # Дисплей
    if call.data == "display_16_pro_max":
        await call.message.edit_text(
            text="**Дисплей iPhone 16 Pro Max**\n"
                 "💎 Состояние: Идеал\n"
                 "💰 Цена: 25 000₽",
            parse_mode="Markdown",
            reply_markup=display_16_pro_max_menu
        )
    # Корпус (черный)
    elif call.data == "corpus_black_16_pro_max":
        await call.message.edit_text(
            text="**Корпус (черный) iPhone 16 Pro Max**\n"
                 "💎 Состояние: Идеал\n"
                 "💰 Цена: 20 000₽",
            parse_mode="Markdown",
            reply_markup=corpus_black_16_pro_max_menu
        )
    else:
        # Для остальных подкатегорий пока нет наполнения
        await call.answer("🔹 В этой категории пока нет товаров.", show_alert=True)

# Оформление заказа (order_*)
@dp.callback_query(F.data.startswith("order_"))
async def order_callback(call: types.CallbackQuery):
    user_name = call.from_user.first_name
    user_id = call.from_user.id

    # Определяем, какой товар заказали
    if call.data == "order_16_pro_max_display":
        order_text = (
            f"📦 **Новый заказ!**\n\n"
            f"🔹 **Товар**: Дисплей iPhone 16 Pro Max\n"
            f"💎 **Состояние**: Идеал\n"
            f"💰 **Цена**: 25 000₽\n\n"
            f"👤 **Клиент**: [{user_name}](tg://user?id={user_id})\n"
            f"🆔 **ID клиента**: `{user_id}`"
        )
    elif call.data == "order_16_pro_max_corpus_black":
        order_text = (
            f"📦 **Новый заказ!**\n\n"
            f"🔹 **Товар**: Корпус (черный) iPhone 16 Pro Max\n"
            f"💎 **Состояние**: Идеал\n"
            f"💰 **Цена**: 20 000₽\n\n"
            f"👤 **Клиент**: [{user_name}](tg://user?id={user_id})\n"
            f"🆔 **ID клиента**: `{user_id}`"
        )
    else:
        await call.answer("Неизвестный товар", show_alert=True)
        return

    # Рассылка менеджерам
    for manager_id in MANAGER_IDS:
        await bot.send_message(manager_id, order_text, parse_mode="Markdown")

    # Сообщение пользователю
    await call.message.answer("✅ Заказ оформлен! Менеджер скоро свяжется с вами.")

# Кнопка «Назад» (back_*)
@dp.callback_query(F.data.startswith("back_"))
async def back_callback(call: types.CallbackQuery):
    if call.data == "back_main":
        await call.message.edit_text(
            text="Выберите категорию:",
            reply_markup=main_menu
        )
    elif call.data == "back_iphone":
        await call.message.edit_text(
            text="Выберите модель iPhone:",
            reply_markup=iphone_menu
        )
    elif call.data == "back_16_pro_max":
        await call.message.edit_text(
            text="Выберите категорию для **iPhone 16 Pro Max**:",
            parse_mode="Markdown",
            reply_markup=iphone_16_pro_max_menu
        )

# ========================== Запуск бота ==========================

async def main():
    # Удаляем Webhook (если был) и запускаем бота в режиме Polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
