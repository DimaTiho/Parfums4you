import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Налаштування ===
BOT_TOKEN = '7760087730:AAGcL8oADjz5VG2EDiFNuJ5taRZZKAvB1nw'
GOOGLE_SHEET_NAME = 'Parfums'
CREDENTIALS_FILE = 'credentials.json'
COST_PRICE = 80
FREE_DELIVERY_THRESHOLD = 500
DELIVERY_COST = 80

# === Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(GOOGLE_SHEET_NAME).sheet1

# === Дані ===
perfumes = {
    "Жіночі": ["Chanel Chance", "Dior J'adore"],
    "Чоловічі": ["Dior Sauvage", "Versace Eros"],
    "Унісекс": ["Tom Ford Black Orchid", "Creed Aventus"]
}
perfume_prices = {p: 200 for cat in perfumes.values() for p in cat}

promotions = {
    "1+1=Подарунок": {"description": "Купи 2 — третій у подарунок", "discount": 66.67},
    "Парфум дня": {"description": "-20 грн на обраний аромат", "discount": 20},
    "Перший клієнт": {"description": "10% знижка на перше замовлення", "discount": 20},
    "Таємне слово": {"description": "Назви слово 'АРОМАТ' — знижка 15 грн", "discount": 15},
    "Без знижки": {"description": "Без акцій", "discount": 0},
}

# === Бот ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
user_data = {}

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Переглянути парфуми", "Акції", "Оформити замовлення")
    await message.answer("🌿 Вітаємо! Натхнення у кожному ароматі.", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "Переглянути парфуми")
async def choose_category(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for cat in perfumes:
        kb.add(cat)
    kb.add("Усі")
    await message.answer("Вибери категорію:", reply_markup=kb)

@dp.message_handler(lambda m: m.text in perfumes or m.text == "Усі")
async def show_perfumes(message: types.Message):
    text = "\n".join([f"- {p} (200 грн)" for p in sum(perfumes.values(), [])]) if message.text == "Усі" else \
           "\n".join([f"- {p} (200 грн)" for p in perfumes[message.text]])
    await message.answer(f"🌿 {message.text} аромати:\n{text}")

@dp.message_handler(lambda m: m.text == "Акції")
async def show_promotions(message: types.Message):
    promo_text = "\n".join([f"- {k}: {v['description']}" for k, v in promotions.items() if k != "Без знижки"])
    delivery_note = f"🚚 Безкоштовна доставка при замовленні від {FREE_DELIVERY_THRESHOLD} грн (інакше +{DELIVERY_COST} грн)"
    await message.answer(f"🔥 Акції на сьогодні:\n{promo_text}\n\n{delivery_note}")

@dp.message_handler(lambda m: m.text == "Оформити замовлення")
async def start_order(message: types.Message):
    user_data[message.from_user.id] = {}
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    all_perfumes = sum(perfumes.values(), [])
    for p in all_perfumes:
        kb.add(p)
    await message.answer("Обери аромат:", reply_markup=kb)

@dp.message_handler(lambda m: m.text in perfume_prices)
async def get_name(message: types.Message):
    user_data[message.from_user.id]["perfume"] = message.text
    await message.answer("Введи своє ім'я:")

@dp.message_handler(lambda m: "name" not in user_data.get(m.from_user.id, {}))
async def get_phone(message: types.Message):
    user_data[message.from_user.id]["name"] = message.text
    await message.answer("Номер телефону:")

@dp.message_handler(lambda m: "phone" not in user_data.get(m.from_user.id, {}))
async def get_address(message: types.Message):
    user_data[message.from_user.id]["phone"] = message.text
    await message.answer("Адреса доставки (або відділення НП):")

@dp.message_handler(lambda m: "address" not in user_data.get(m.from_user.id, {}))
async def get_quantity(message: types.Message):
    user_data[message.from_user.id]["address"] = message.text
    await message.answer("Кількість (шт):")

@dp.message_handler(lambda m: "quantity" not in user_data.get(m.from_user.id, {}))
async def get_promotion(message: types.Message):
    if not message.text.isdigit():
        await message.answer("Введи кількість числом!")
        return
    user_data[message.from_user.id]["quantity"] = int(message.text)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for promo in promotions:
        kb.add(promo)
    await message.answer("Обери акцію (або 'Без знижки'):", reply_markup=kb)

@dp.message_handler(lambda m: m.text in promotions)
async def confirm_order(message: types.Message):
    uid = message.from_user.id
    data = user_data[uid]
    data["promotion"] = message.text
    price = perfume_prices[data["perfume"]]
    quantity = data["quantity"]
    discount = promotions[message.text]["discount"]
    subtotal = max(0, price * quantity - discount * quantity)

    delivery_fee = 0 if subtotal >= FREE_DELIVERY_THRESHOLD else DELIVERY_COST
    total = subtotal + delivery_fee
    profit = total - (COST_PRICE * quantity)

    order_summary = (
        f"Підтвердження замовлення:\n"
        f"Аромат: {data['perfume']}\n"
        f"Кількість: {quantity}\n"
        f"Ціна за одиницю: {price} грн\n"
        f"Акція: {message.text} (-{discount} грн/шт)\n"
        f"Сума: {subtotal} грн\n"
        f"Доставка: {'Безкоштовна' if delivery_fee == 0 else f'{DELIVERY_COST} грн'}\n"
        f"Загальна сума: {total} грн\n"
        f"Прибуток: {profit} грн\n\n"
        f"Ім'я: {data['name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Адреса: {data['address']}"
    )
    sheet.append_row([
        data['name'], data['phone'], data['address'], data['perfume'], quantity,
        message.text, total, profit, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ])
    await message.answer(order_summary + "\n\n✅ Замовлення прийнято! Очікуйте на дзвінок або SMS.")
    del user_data[uid]

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

