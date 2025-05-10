import logging
import ssl
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, ReplyKeyboardRemove
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# === Налаштування ===
BOT_TOKEN = os.getenv("BOT_TOKEN", 'YOUR_TOKEN_HERE')
GOOGLE_SHEET_NAME = 'Parfums'
CREDENTIALS_FILE = 'credentials.json'
COST_PRICE = 80
FREE_DELIVERY_THRESHOLD = 500
DELIVERY_COST = 70

# === Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
if not os.path.exists(CREDENTIALS_FILE):
    raise FileNotFoundError(f"Файл {CREDENTIALS_FILE} не знайдено. Завантажте credentials.json або перевірте шлях.")
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

# === Ініціалізація бота ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_data = {}

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

promotions = {
    "1+1=Подарунок": {"description": "Купи 2 — третій у подарунок", "discount": 66.67},
    "Парфум дня": {"description": "-20 грн на обраний аромат", "discount": 20},
    "Перший клієнт": {"description": "10% знижка на перше замовлення", "discount": 20},
    "Таємне слово": {"description": "Назви слово 'АРОМАТ' — знижка 15 грн", "discount": 15},
    "Без знижки": {"description": "Без акцій", "discount": 0},
}

# === Обробка повідомлень ===

def message_condition(field):
    return lambda message: field in user_data.get(message.from_user.id, {})

def message_missing_field(field):
    return lambda message: field not in user_data.get(message.from_user.id, {})

@dp.message(lambda message: "search_mode" in user_data.get(message.from_user.id, {}))
async def perform_search(message: types.Message):
    pass

@dp.message(lambda message: "selected_perfume" in user_data.get(message.from_user.id, {}))
async def save_quantity_to_cart(message: types.Message):
    pass

@dp.message(lambda message: "name" not in user_data.get(message.from_user.id, {}))
async def get_phone(message: types.Message):
    pass

@dp.message(lambda message: "phone" not in user_data.get(message.from_user.id, {}))
async def get_city(message: types.Message):
    if message.from_user.id not in user_data:
        await message.answer("⚠️ Будь ласка, почніть замовлення з /start або натисніть '📝 Замовити'")
        return
    user_data[message.from_user.id]["city"] = message.text

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📦 Нова Пошта", callback_data="np"),
        InlineKeyboardButton("📮 Укрпошта", callback_data="ukr"),
        InlineKeyboardButton("🏠 Адресна доставка", callback_data="address")
    )
    kb.add(InlineKeyboardButton("🔙 На головну", callback_data="start"))
    await message.answer("Оберіть тип доставки:", reply_markup=kb)

@dp.callback_query(lambda c: c.data in ["np", "ukr", "address"])
async def ask_for_address(call: types.CallbackQuery):
    delivery_methods = {
        "np": "Нова Пошта",
        "ukr": "Укрпошта",
        "address": "Адресна доставка"
    }
    method = delivery_methods.get(call.data)
    user_data[call.from_user.id]["delivery_method"] = method

    prompt = {
        "Нова Пошта": "🏤 Введіть місто та номер відділення НП:",
        "Укрпошта": "📮 Введіть місто та поштовий індекс + адресу:",
        "Адресна доставка": "📍 Введіть місто та повну адресу доставки:"
    }

    await call.message.answer(prompt[method] + "\n‼️ Перевірте уважно правильність даних перед підтвердженням.")

# === Запуск бота ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
