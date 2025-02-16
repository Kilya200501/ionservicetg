import os
import re
import logging
import asyncio
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

import requests
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    ContentType,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

###############################################################################
# 1. Загрузка окружения, логирование
###############################################################################
load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID", "0"))

# Ссылка на ваш фид (формат <feed><offers><offer>)
# Укажите нужную ссылку здесь:
FEED_URL = "https://ion-master.ru/index.php?route=extension/feed/yaoexport"

logging.basicConfig(level=logging.INFO)


###############################################################################
# 2. Глобальные структуры
###############################################################################

# user_data[user_id] = {
#   "phone": Optional[str],
#   "selected_item": Optional[Dict[str, Any]]
# }
user_data: Dict[int, Dict[str, Any]] = {}

# Все товары в этом фиде
all_offers: List[Dict[str, Any]] = []


###############################################################################
# 3. Парсинг фида <feed version="1"><offers><offer> ... </offers></feed>
###############################################################################
def parse_feed(url: str) -> None:
    """
    Скачиваем XML, ищем <feed><offers><offer>.
    Заполняем all_offers - список словарей:
        {
          "id": str,
          "title": str,
          "price": float,
          "category": str,
          "description": str,
          "seller_phone": str,   # при желании
          ...
        }
    """
    global all_offers
    all_offers.clear()

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Ошибка загрузки фида: {e}")
        return

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        logging.error(f"Ошибка парсинга XML: {e}")
        return

    # Обычно <feed><offers>...
    offers_el = root.find('offers')
    if offers_el is None:
        logging.error("Не найден тег <offers> внутри <feed>.")
        return

    for offer_el in offers_el.findall('offer'):
        # Извлекаем нужные поля
        off_id = (offer_el.findtext('id') or "").strip()
        title_val = (offer_el.findtext('title') or "No title").strip()
        cat_val = (offer_el.findtext('category') or "").strip()
        price_str = (offer_el.findtext('price') or "0").strip()
        desc_val = (offer_el.findtext('description') or "").strip()

        # Пример получения цены
        try:
            price_val = float(price_str)
        except ValueError:
            price_val = 0.0

        # Пример получения телефона продавца (опционально)
        seller_el = offer_el.find('seller')
        seller_phone = ""
        if seller_el is not None:
            contacts_el = seller_el.find('contacts')
            if contacts_el is not None:
                phone_el = contacts_el.find('phone')
                if phone_el is not None and phone_el.text:
                    seller_phone = phone_el.text.strip()

        item = {
            "id": off_id,
            "title": title_val,
            "category": cat_val,
            "price": price_val,
            "description": desc_val,
            "seller_phone": seller_phone,  # если нужно
        }

        all_offers.append(item)


###############################################################################
# 4. Вспомогательные функции
###############################################################################
def ensure_user_data(user_id: int) -> Dict[str, Any]:
    if user_id not in user_data:
        user_data[user_id] = {"phone": None, "selected_item": None}
    return user_data[user_id]

def find_item_by_id(item_id: str) -> Optional[Dict[str, Any]]:
    for off in all_offers:
        if off["id"] == item_id:
            return off
    return None

def shorten_text(text: str, max_len: int = 60) -> str:
    txt = text.strip()
    return txt if len(txt) <= max_len else (txt[:max_len - 3].strip() + "...")

###############################################################################
# 4.1 Получение списка категорий
###############################################################################
def get_categories() -> List[str]:
    """
    Собираем уникальные категории из all_offers (если поле category не пустое или не '-').
    """
    cats = set()
    for off in all_offers:
        c = off["category"].strip()
        # Если реально нет категории или она '-'
        if c and c != '-':
            cats.add(c)
    return sorted(cats)


###############################################################################
# 5. Инициализация бота
###############################################################################
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


###############################################################################
# 5.1 Команда /start
###############################################################################
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """
    1) Скачиваем (обновляем) фид,
    2) Если есть категории - показываем их
       Иначе просто показываем все товары.
    """
    parse_feed(FEED_URL)

    if not all_offers:
        await message.answer("Нет товаров или фид недоступен.")
        return

    categories = get_categories()
    if categories:
        # Показываем список категорий
        kb = InlineKeyboardMarkup()
        for cat in categories:
            kb.add(InlineKeyboardButton(
                text=cat,
                callback_data=f"cat_{cat}"
            ))
        # Можно добавить кнопку «Все товары»
        kb.add(InlineKeyboardButton(text="Все товары", callback_data="all_items"))
        await message.answer("Выберите категорию:", reply_markup=kb)
    else:
        # Если нет категорий - сразу «все товары»
        await send_items_list(message.chat.id, all_offers, "Все товары")


###############################################################################
# 5.2 «Все товары»
###############################################################################
@dp.callback_query(F.data == "all_items")
async def on_all_items_callback(callback: CallbackQuery):
    if not all_offers:
        await callback.answer("Список товаров пуст.", show_alert=True)
        return

    await callback.message.delete()
    await send_items_list(callback.message.chat.id, all_offers, "Все товары")
    await callback.answer()


###############################################################################
# 5.3 Выбор категории cat_xxx
###############################################################################
@dp.callback_query(F.data.startswith("cat_"))
async def on_category_callback(callback: CallbackQuery):
    cat_name = callback.data.split("_", 1)[1]
    filtered = [off for off in all_offers if off["category"].strip() == cat_name]

    if not filtered:
        await callback.message.edit_text(f"В категории «{cat_name}» нет товаров.")
        await callback.answer()
        return

    await callback.message.delete()
    await send_items_list(callback.message.chat.id, filtered, cat_name)
    await callback.answer()


###############################################################################
# 5.4 Отправка списка товаров
###############################################################################
async def send_items_list(chat_id: int, items: List[Dict[str, Any]], title: str):
    """
    Поштучно отправляем товары.
    """
    for it in items:
        short_title = shorten_text(it["title"])
        cat_str = it["category"] or "—"
        price_str = f"{it['price']:.2f}"

        text_msg = (
            f"<b>{short_title}</b>\n"
            f"Категория: {cat_str}\n"
            f"Цена: {price_str} ₽\n"
        )
        # Можно добавить часть описания (it["description"][:100]...) или seller_phone

        kb_item = InlineKeyboardMarkup()
        kb_item.add(InlineKeyboardButton("Заказать", callback_data=f"order_{it['id']}"))
        await bot.send_message(
            chat_id,
            text=text_msg,
            parse_mode="HTML",
            reply_markup=kb_item
        )

    # В конце - кнопка «Связаться с менеджером»
    kb_final = InlineKeyboardMarkup()
    kb_final.add(InlineKeyboardButton("Связаться с менеджером", callback_data="contact_manager"))
    await bot.send_message(
        chat_id,
        text=(
            f"Всего товаров: {len(items)} в разделе «{title}».\n"
            "Чтобы оформить заказ, нажмите «Заказать» под товаром,\n"
            "либо свяжитесь с менеджером:"
        ),
        reply_markup=kb_final
    )


###############################################################################
# 5.5 «Заказать» товар (order_xxx)
###############################################################################
@dp.callback_query(F.data.startswith("order_"))
async def on_order_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    item_id = callback.data.split("_", 1)[1]

    item = find_item_by_id(item_id)
    if not item:
        await callback.answer("Товар не найден.")
        return

    state = ensure_user_data(user_id)
    state["selected_item"] = item

    if state["phone"]:
        # Если уже есть номер, завершаем заказ
        await finalize_order(user_id, callback.message)
        await callback.answer("Ваш заказ оформлен!")
    else:
        await callback.answer()
        contact_btn = KeyboardButton(text="Отправить номер телефона", request_contact=True)
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(contact_btn)

        await callback.message.answer(
            "Пожалуйста, отправьте свой номер телефона, чтобы подтвердить заказ:",
            reply_markup=kb
        )


###############################################################################
# 5.6 «Связаться с менеджером» (contact_manager)
###############################################################################
@dp.callback_query(F.data == "contact_manager")
async def on_contact_manager(callback: CallbackQuery):
    user_id = callback.from_user.id
    state = ensure_user_data(user_id)

    if state["phone"]:
        await callback.answer("У нас уже есть ваш номер, ожидайте связи!")
    else:
        await callback.answer()
        contact_btn = KeyboardButton(text="Отправить номер телефона", request_contact=True)
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(contact_btn)

        await callback.message.answer(
            "Отправьте номер телефона, чтобы менеджер связался с вами:",
            reply_markup=kb
        )


###############################################################################
# 5.7 Получение контакта (message.contact)
###############################################################################
@dp.message(F.content_type == ContentType.CONTACT)
async def on_user_contact(message: Message):
    user_id = message.from_user.id
    phone_number = message.contact.phone_number

    state = ensure_user_data(user_id)
    state["phone"] = phone_number

    if state["selected_item"]:
        # Завершаем заказ
        await message.answer("Спасибо! Телефон получен. Завершаем заказ...")
        await finalize_order(user_id, message)
    else:
        # Просто контакт, без заказа
        await message.answer(
            "Спасибо! Ваш номер получен. Менеджер свяжется с вами.",
            reply_markup=ReplyKeyboardMarkup(remove_keyboard=True)
        )
        await bot.send_message(
            MANAGER_CHAT_ID,
            text=(
                f"Пользователь @{message.from_user.username or '—'} "
                f"({message.from_user.full_name or '—'}) "
                f"оставил номер: {phone_number}"
            )
        )


###############################################################################
# 5.8 Завершение заказа
###############################################################################
async def finalize_order(user_id: int, msg: Message):
    state = user_data.get(user_id)
    if not state:
        return

    phone = state.get("phone")
    item = state.get("selected_item")
    if not phone or not item:
        return

    text_msg = (
        "Новый заказ!\n"
        f"Телефон: {phone}\n"
        f"Товар: {item['title']}\n"
        f"Цена: {item['price']:.2f}₽\n"
        f"Категория: {item['category'] or '—'}"
    )
    await bot.send_message(MANAGER_CHAT_ID, text_msg)

    state["selected_item"] = None
    await msg.answer(
        "Заказ отправлен менеджеру! Ожидайте связи.\n"
        "Чтобы заказать что-то ещё, введите /start.",
        reply_markup=ReplyKeyboardMarkup(remove_keyboard=True)
    )


###############################################################################
# 5.9 Запуск бота
###############################################################################
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
