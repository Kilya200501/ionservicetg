import os
import logging
import asyncio
import requests

from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

###############################################################################
# 1. Загрузка окружения, логирование
###############################################################################
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENCART_API_TOKEN = os.getenv("OPENCART_API_TOKEN", "")
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID", "0"))

logging.basicConfig(level=logging.INFO)

###############################################################################
# 2. Инициализация бота (aiogram 3.x)
###############################################################################
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

###############################################################################
# 3. Пример функции: обращаемся к OpenCart с API-ключом
###############################################################################
def fetch_data_from_opencart(api_token: str) -> str:
    """
    Условный пример GET-запроса к вашему OpenCart API:
    - url: пример эндпоинта для получения списка товаров
    - передаём api_token как параметр
    - возвращаем текст ответа (или JSON по желанию)

    В реальном случае вы укажете действующий URL, формат (GET/POST), заголовки,
    сессию, логин, и т.д. — в зависимости от вашего API.
    """
    # Пример URL (вы должны заменить на реальный, где принимают api_token)
    url = "https://example.com/index.php?route=api/products"

    params = {
        "api_token": api_token,
        # возможно, нужны дополнительные параметры
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        # Если ваш API вернёт JSON, можно делать: return resp.json()
        return resp.text
    except requests.RequestException as e:
        logging.error(f"Ошибка при запросе к OpenCart: {e}")
        return f"Ошибка: {e}"

###############################################################################
# 4. Обработка команды /start
###############################################################################
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """
    При команде /start бот:
    1) Проверяет, есть ли API-ключ OpenCart.
    2) Делает запрос к OpenCart (fetch_data_from_opencart).
    3) Отправляет результат пользователю.
    """
    if not OPENCART_API_TOKEN:
        await message.answer("Ошибка: не найден API-ключ для OpenCart.")
        return

    # Обращаемся к вашему OpenCart API, используя токен
    result = fetch_data_from_opencart(OPENCART_API_TOKEN)

    # Отправим результат пользователю (для демонстрации)
    # parse_mode="Markdown" или "HTML" можно настроить по вкусу
    await message.answer(
        "Ваш API-ключ OpenCart:\n\n"
        f"`{OPENCART_API_TOKEN}`\n\n"
        "Результат запроса:\n"
        f"`{result}`",
        parse_mode="Markdown"
    )

###############################################################################
# 5. Пример дальнейшей логики
###############################################################################
# Вы можете дописать функционал оформления заказа, кнопки "Заказать" и т.д.
# Аналогично тому, что мы делали в предыдущих примерах. Главное, что запрос
# к OpenCart будет подставлять ваш API-ключ.

# Пример: допустим, при нажатии кнопки "Показать товары" вы снова вызываете
# fetch_data_from_opencart(OPENCART_API_TOKEN), парсите ответ, и показываете
# товары в инлайн-кнопках.


###############################################################################
# 6. Запуск бота
###############################################################################
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
