import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================== Настройка окружения ==================

# Токен бота (запишите в переменную окружения TOKEN или впишите сюда напрямую, если нужно)
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Ошибка: переменная окружения TOKEN не установлена!")

# ID менеджеров (можно добавить несколько через запятую, здесь только один)
MANAGER_IDS = [5300643604]

# Создаём бота и диспетчер (parse_mode="Markdown" для форматирования)
bot = Bot(token=TOKEN, parse_mode="Markdown")
dp = Dispatcher()

# ================== Кнопки для товаров ==================

# Кнопки для «Дисплей iPhone 16 Pro Max»
order_display_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🛒 Оформить заказ", callback_data="order_display_16_pro_max")],
])

# Кнопки для «Корпус (черный) iPhone 16 Pro Max»
order_corpus_black_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🛒 Оформить заказ", callback_data="order_corpus_black_16_pro_max")],
])

# ================== Хэндлер /start (с deep_link) ==================

@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandStart):
    """
    Обрабатывает команду /start, включая deep_link (например, /start display_16_pro_max).
    В aiogram 3.x параметр command: CommandStart содержит .args (deep_link).
    """
    deep_link = command.args  # Это то, что идёт после /start

    # Если /start без параметров (пользователь пришёл сам, без ссылки)
    if not deep_link:
        await message.answer(
            "Здравствуйте! Я бот для оформления заказов.\n\n"
            "Кажется, вы зашли без выбора конкретного товара. "
            "Пожалуйста, перейдите в наш канал, выберите товар и нажмите кнопку «Заказать»."
        )
        return

    # Если пришёл deep_link с конкретным товаром
    if deep_link == "display_16_pro_max":
        await message.answer(
            "**Дисплей iPhone 16 Pro Max**\n"
            "💎 Состояние: Идеал\n"
            "💰 Цена: 25 000₽\n\n"
            "Нажмите кнопку ниже, чтобы оформить заказ:",
            reply_markup=order_display_kb
        )

    elif deep_link == "corpus_black_16_pro_max":
        await message.answer(
            "**Корпус (черный) iPhone 16 Pro Max**\n"
            "💎 Состояние: Идеал\n"
            "💰 Цена: 20 000₽\n\n"
            "Нажмите кнопку ниже, чтобы оформить заказ:",
            reply_markup=order_corpus_black_kb
        )

    else:
        # Неизвестная метка товара
        await message.answer("Неизвестная ссылка. Попробуйте ещё раз или свяжитесь с поддержкой.")

# ================== Хэндлер нажатия «Оформить заказ» ==================

@dp.callback_query(F.data.startswith("order_"))
async def process_order(call: types.CallbackQuery):
    """Обрабатывает callback_data вида order_display_16_pro_max и т.п."""
    user_id = call.from_user.id
    user_name = call.from_user.first_name
    cb_data = call.data  # например, "order_display_16_pro_max"

    if cb_data == "order_display_16_pro_max":
        product_name = "Дисплей iPhone 16 Pro Max"
        price = "25 000₽"
    elif cb_data == "order_corpus_black_16_pro_max":
        product_name = "Корпус (черный) iPhone 16 Pro Max"
        price = "20 000₽"
    else:
        await call.answer("Неизвестный товар", show_alert=True)
        return

    # Формируем текст для менеджера
    order_text = (
        f"📦 **Новый заказ!**\n\n"
        f"🔹 **Товар**: {product_name}\n"
        f"💰 **Цена**: {price}\n\n"
        f"👤 **Клиент**: [{user_name}](tg://user?id={user_id})\n"
        f"🆔 **ID**: `{user_id}`"
    )

    # Отправляем менеджеру(ам)
    for manager_id in MANAGER_IDS:
        try:
            await bot.send_message(manager_id, order_text)
        except Exception as e:
            # Если вдруг не удалось отправить менеджеру
            print(f"Ошибка при отправке менеджеру {manager_id}: {e}")

    # Показываем всплывающее сообщение (alert) пользователю
    await call.answer("✅ Заказ оформлен! Менеджер скоро свяжется с вами.", show_alert=True)

# ================== Запуск бота ==================

async def main():
    # Удаляем возможный старый Webhook и запускаем "long polling"
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
