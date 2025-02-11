import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery
)

# ========= НАСТРОЙКИ =========

# Токен бота (возьмите из переменной окружения или впишите напрямую)
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Ошибка: переменная окружения TOKEN не установлена!")

# ID менеджеров (можно указать несколько)
MANAGER_IDS = [5300643604]

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, parse_mode="Markdown")
dp = Dispatcher()

# ========= МЕНЮ ==========

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

# Подкатегории iPhone 16 Pro Max
iphone_16_pro_max_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Дисплей", callback_data="display_16_pro_max")],
    [InlineKeyboardButton(text="Аккумулятор", callback_data="battery_16_pro_max")],
    [InlineKeyboardButton(text="Корпус", callback_data="corpus_16_pro_max")],
    [InlineKeyboardButton(text="Корпус (черный) - 20 000₽", callback_data="corpus_black_16_pro_max")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_iphone")],
])

# Меню «Оформить заказ» для конкретных товаров
display_16_pro_max_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🛒 Оформить заказ", callback_data="order_16_pro_max_display")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_16_pro_max")],
])

corpus_black_16_pro_max_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🛒 Оформить заказ", callback_data="order_16_pro_max_corpus_black")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_16_pro_max")],
])

# ========= ХЭНДЛЕР /start (с deep_link или без) ==========

@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandStart):
    """
    Обрабатывает /start. Если есть deep-link (command.args), 
    показываем конкретный товар. Если нет — показываем главное меню.
    """
    deep_link = command.args  # Параметр после /start

    # Если пользователь пришёл без параметра, показываем «прежнее» меню
    if not deep_link:
        await message.answer(
            text=(
                "👋 Здравствуйте! Я помощник компании **ION-Сервис**.\n"
                "Выберите категорию:"
            ),
            reply_markup=main_menu
        )
        return

    # Если пришли с deep-link (например: /start display_16_pro_max)
    if deep_link == "display_16_pro_max":
        await message.answer(
            text=(
                "**Дисплей iPhone 16 Pro Max**\n"
                "💎 Состояние: Идеал\n"
                "💰 Цена: 25 000₽\n\n"
                "Нажмите кнопку ниже, чтобы оформить заказ:"
            ),
            reply_markup=display_16_pro_max_menu
        )
    elif deep_link == "corpus_black_16_pro_max":
        await message.answer(
            text=(
                "**Корпус (черный) iPhone 16 Pro Max**\n"
                "💎 Состояние: Идеал\n"
                "💰 Цена: 20 000₽\n\n"
                "Нажмите кнопку ниже, чтобы оформить заказ:"
            ),
            reply_markup=corpus_black_16_pro_max_menu
        )
    else:
        # Если deep_link незнаком
        await message.answer(
            text="Неизвестная ссылка. Нажмите /start, чтобы открыть главное меню."
        )

# ========= ХЭНДЛЕРЫ ДЛЯ ИНТЕРАКТИВНОГО МЕНЮ ==========

# Выбор категории
@dp.callback_query(F.data.startswith("category_"))
async def category_callback(call: CallbackQuery):
    if call.data == "category_iphone":
        await call.message.edit_text(
            text="Выберите модель iPhone:",
            reply_markup=iphone_menu
        )
    else:
        await call.answer("🔹 В этой категории пока нет товаров.", show_alert=True)

# Выбор модели iPhone
@dp.callback_query(F.data.startswith("iphone_"))
async def iphone_model_callback(call: CallbackQuery):
    if call.data == "iphone_16_pro_max":
        await call.message.edit_text(
            text="Выберите категорию для **iPhone 16 Pro Max**:",
            reply_markup=iphone_16_pro_max_menu
        )
    else:
        # Для примера считаем, что другие модели не заполнены
        await call.answer("🔹 В этой модели пока нет товаров.", show_alert=True)

# Обработчик подкатегорий (дисплей, аккумулятор, корпус)
@dp.callback_query(F.data.startswith(("display_", "battery_", "corpus_")))
async def subcategory_callback(call: CallbackQuery):
    if call.data == "display_16_pro_max":
        await call.message.edit_text(
            text=(
                "**Дисплей iPhone 16 Pro Max**\n"
                "💎 Состояние: Идеал\n"
                "💰 Цена: 25 000₽"
            ),
            reply_markup=display_16_pro_max_menu
        )
    elif call.data == "corpus_black_16_pro_max":
        await call.message.edit_text(
            text=(
                "**Корпус (черный) iPhone 16 Pro Max**\n"
                "💎 Состояние: Идеал\n"
                "💰 Цена: 20 000₽"
            ),
            reply_markup=corpus_black_16_pro_max_menu
        )
    else:
        # Остальные пока не заполнены товарами
        await call.answer("🔹 В этой категории пока нет товаров.", show_alert=True)

# ========= ОБРАБОТКА ЗАКАЗОВ (кнопка «Оформить заказ») ==========

@dp.callback_query(F.data.startswith("order_"))
async def order_callback(call: CallbackQuery):
    """
    Получаем callback_data типа order_16_pro_max_display или order_16_pro_max_corpus_black,
    формируем заказ и отправляем менеджерам.
    """
    user_name = call.from_user.first_name
    user_id = call.from_user.id
    cb_data = call.data

    if cb_data == "order_16_pro_max_display":
        product_name = "Дисплей iPhone 16 Pro Max"
        price = "25 000₽"
    elif cb_data == "order_16_pro_max_corpus_black":
        product_name = "Корпус (черный) iPhone 16 Pro Max"
        price = "20 000₽"
    else:
        await call.answer("Неизвестный товар", show_alert=True)
        return

    # Текст для менеджера
    order_text = (
        f"📦 **Новый заказ!**\n\n"
        f"🔹 **Товар**: {product_name}\n"
        f"💰 **Цена**: {price}\n\n"
        f"👤 **Клиент**: [{user_name}](tg://user?id={user_id})\n"
        f"🆔 **ID**: `{user_id}`"
    )

    # Отправляем менеджеру(ам)
    for manager_id in MANAGER_IDS:
        await bot.send_message(manager_id, order_text)

    # Сообщаем пользователю
    await call.answer("✅ Заказ оформлен! Менеджер скоро свяжется с вами.", show_alert=True)

# ========= КНОПКИ «НАЗАД» ==========

@dp.callback_query(F.data.startswith("back_"))
async def back_callback(call: CallbackQuery):
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
            reply_markup=iphone_16_pro_max_menu
        )

# ========= ЗАПУСК БОТА ==========

async def main():
    # Отключаем старый webhook и включаем "long polling"
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
