import asyncio
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

# 1. Вставьте свой Telegram-бот токен:
TOKEN = "ВАШ_TELEGRAM_TOKEN"

# 2. Вставьте ваш API-ключ OpenCart-модуля:
API_KEY = "OL3sA4OR8Re6ProXXtgGno6fZnIQm4Izh0VaO3fFjFeE3SeWp1CtARi5W6By..."

# 3. Предположим, модуль требует заголовок X-Oc-Restadmin-Id:
HEADERS = {
    "X-Oc-Restadmin-Id": API_KEY
}

# 4. Предположим, базовый URL такой:
BASE_API_URL = "https:/https://ion-master.ru/index.php?route=rest/product_admin"


bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

async def get_products() -> list:
    """
    Пример: получаем список товаров.
    Путь /products может зависеть от вашего модуля (см. инструкцию).
    """
    url = f"{BASE_API_URL}/products"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                print(f"Ошибка {resp.status}")
                return []

@dp.message(Command("start"))
async def start_cmd(message: Message):
    """
    Показываем пример получения товаров и выводим их названия в чат.
    """
    products = await get_products()
    if not products:
        await message.answer("Не удалось загрузить товары (пусто или ошибка).")
        return

    # Предположим, что products — это массив JSON-объектов со структурой
    # [{"product_id":101, "name":"iPhone 16 Display", ...}, ...]
    text_lines = []
    for p in products:
        pid = p.get("product_id") or p.get("id")
        pname = p.get("name")
        text_lines.append(f"{pid} — {pname}")

    answer_text = "Список товаров:\n" + "\n".join(text_lines)
    await message.answer(answer_text)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
