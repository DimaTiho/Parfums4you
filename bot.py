
# Оновлена версія: початок
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, ReplyKeyboardRemove
from aiogram.utils import executor
from datetime import datetime
import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Налаштування ===
BOT_TOKEN = 'ВАШ_ТОКЕН'
GOOGLE_SHEET_NAME = 'Parfums'
CREDENTIALS_FILE = 'credentials.json'
COST_PRICE = 80
FREE_DELIVERY_THRESHOLD = 500
DELIVERY_COST = 70

# === Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
workbook = client.open(GOOGLE_SHEET_NAME)
sheet = workbook.sheet1
try:
    analytics_sheet = workbook.worksheet("Аналітика")
except:
    analytics_sheet = workbook.add_worksheet(title="Аналітика", rows="10", cols="2")
    analytics_sheet.update("A1", [["Показник", "Значення"],
                                   ["Усього замовлень", ""],
                                   ["Загальна сума", ""],
                                   ["Загальний прибуток", ""],
                                   ["Найпопулярніший аромат", ""]])

# === Дані ===
perfumes = {
    "Жіночі": [
        {"name": "Chanel Chance", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Dior J'adore", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Lancôme La Vie Est Belle", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "YSL Mon Paris", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"}
    ],
    "Чоловічі": [
        {"name": "Dior Sauvage", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Versace Eros", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Bleu de Chanel", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Paco Rabanne Invictus", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"}
    ],
    "Унісекс": [
        {"name": "Tom Ford Black Orchid", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Creed Aventus", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Molecule 01", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Byredo Gypsy Water", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"}
    ],
    "ТОП продаж": [
        {"name": "Dior Sauvage", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Chanel Chance", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Tom Ford Black Orchid", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"}
    ]
}

perfume_prices = {p["name"]: 200 for cat in perfumes.values() for p in cat}

# === Ініціалізація бота ===
from aiogram.dispatcher.filters import Text

@dp.message_handler(commands=['start'])
async def welcome(message: types.Message):
    user_data[message.from_user.id] = {"cart": {}, "state": None}
    keyboard = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("🛍 Каталог парфумів", callback_data="show_perfumes"),
        InlineKeyboardButton("🎁 Акції та Бонуси", callback_data="show_promotions"),
        InlineKeyboardButton("📦 Кошик", callback_data="view_cart"),
        InlineKeyboardButton("ℹ Як замовити?", callback_data="how_to_order"),
        InlineKeyboardButton("📨 Зв'язок з менеджером", url="https://t.me/your_manager_username")
    )
    await message.answer("🌸 Вітаємо у світі ароматів!
Обирайте найкраще та замовляйте зручно:", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == "show_promotions")
async def show_promotions(call: types.CallbackQuery):
    promo_text = "\n".join([f"- {k}: {v['description']}" for k, v in promotions.items() if k != "Без знижки"])
    await call.message.answer(f"🎁 Актуальні акції:
{promo_text}")


@dp.callback_query_handler(lambda c: c.data == "show_perfumes")
async def show_perfumes(call: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("👨 Чоловічі", callback_data="cat_Чоловічі"),
        InlineKeyboardButton("👩 Жіночі", callback_data="cat_Жіночі"),
        InlineKeyboardButton("🌿 Унісекс", callback_data="cat_Унісекс"),
        InlineKeyboardButton("🔝 ТОП продаж", callback_data="cat_ТОП продаж"),
        InlineKeyboardButton("🔎 Знайти назву", callback_data="search_perfume"),
        InlineKeyboardButton("🏠 Головна", callback_data="main_menu")
    )
    await call.message.answer("📦 Оберіть категорію:", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))
async def show_perfume_by_category(call: types.CallbackQuery):
    category = call.data.split("_")[1]
    for perfume in perfumes[category]:
        name = perfume["name"]
        photo = perfume["photo"]
        price = perfume_prices.get(name, 200)
        text = f"💎 {name}
💰 Ціна: {price} грн"
        keyboard = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("➕ До кошика", callback_data=f"add_{name}"),
            InlineKeyboardButton("🔙 Назад", callback_data="show_perfumes")
        )
        await call.message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith("add_"))
async def add_to_cart(call: types.CallbackQuery):
    perfume_name = call.data[4:]
    uid = call.from_user.id
    if uid not in user_data:
        user_data[uid] = {"cart": {}}
    cart = user_data[uid].setdefault("cart", {})
    cart[perfume_name] = cart.get(perfume_name, 0) + 1
    await call.message.answer(f"🧺 Додано до кошика: {perfume_name}")


@dp.callback_query_handler(lambda c: c.data == "view_cart")
async def view_cart(call: types.CallbackQuery):
    uid = call.from_user.id
    cart = user_data.get(uid, {}).get("cart", {})
    if not cart:
        await call.message.answer("🧺 Кошик порожній.")
        return
    lines = ["🛒 Ваш кошик:"]
    total = 0
    for name, qty in cart.items():
        price = perfume_prices.get(name, 200)
        subtotal = price * qty
        lines.append(f"• {name} — {qty} шт × {price} грн = {subtotal} грн")
        total += subtotal
    lines.append(f"
💵 Сума: {total} грн")
    keyboard = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("✅ Оформити замовлення", callback_data="confirm_order"),
        InlineKeyboardButton("🧹 Очистити кошик", callback_data="clear_cart"),
        InlineKeyboardButton("🔙 Назад", callback_data="show_perfumes")
    )
    await call.message.answer("\n".join(lines), reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == "clear_cart")
async def clear_cart(call: types.CallbackQuery):
    uid = call.from_user.id
    user_data[uid]["cart"] = {}
    await call.message.answer("🧹 Кошик очищено.")


@dp.callback_query_handler(lambda c: c.data == "main_menu")
async def back_to_main(call: types.CallbackQuery):
    await welcome(call.message)
