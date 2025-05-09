import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from aiogram.utils import executor
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Налаштування ===
BOT_TOKEN = '7511346484:AAEm89gjBctt55ge8yEqrfHrxlJ-yS4d56U'
GOOGLE_SHEET_NAME = 'Parfums'
CREDENTIALS_FILE = 'credentials.json'
COST_PRICE = 80
FREE_DELIVERY_THRESHOLD = 500
DELIVERY_COST = 50

# === Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(GOOGLE_SHEET_NAME).sheet1

# === Дані ===
perfumes = {
    "Жіночі": [
        {"name": "Chanel Chance", "photo": "https://example.com/chanel.jpg"},
        {"name": "Dior J'adore", "photo": "https://example.com/jadore.jpg"}
    ],
    "Чоловічі": [
        {"name": "Dior Sauvage", "photo": "https://example.com/sauvage.jpg"},
        {"name": "Versace Eros", "photo": "https://example.com/eros.jpg"}
    ],
    "Унісекс": [
        {"name": "Tom Ford Black Orchid", "photo": "https://example.com/ford.jpg"},
        {"name": "Creed Aventus", "photo": "https://example.com/aventus.jpg"}
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

# === Бот ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
user_data = {}

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📦 Парфуми", callback_data="show_perfumes"),
        InlineKeyboardButton("🔥 Акції", callback_data="promotions"),
        InlineKeyboardButton("📝 Замовити", callback_data="order")
    )
    await message.answer("🌿 Вітаємо! Натхнення у кожному ароматі.", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "show_perfumes")
async def choose_category(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=2)
    for cat in perfumes:
        kb.add(InlineKeyboardButton(cat, callback_data=f"cat_{cat}"))
    kb.add(InlineKeyboardButton("Усі", callback_data="cat_all"))
    await call.message.answer("Вибери категорію:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))
async def show_perfumes(call: types.CallbackQuery):
    category = call.data[4:]
    selected = sum(perfumes.values(), []) if category == "all" else perfumes[category]
    for p in selected:
        await call.message.answer_photo(photo=p["photo"], caption=f"{p['name']} — 200 грн")

@dp.callback_query_handler(lambda c: c.data == "promotions")
async def show_promotions(call: types.CallbackQuery):
    promo_text = "\n".join([f"- {k}: {v['description']}" for k, v in promotions.items() if k != "Без знижки"])
    delivery_note = f"🚚 Безкоштовна доставка при замовленні від {FREE_DELIVERY_THRESHOLD} грн (інакше +{DELIVERY_COST} грн)"
    await call.message.answer(f"🔥 Акції на сьогодні:\n{promo_text}\n\n{delivery_note}")

@dp.callback_query_handler(lambda c: c.data == "order")
async def start_order(call: types.CallbackQuery):
    user_data[call.from_user.id] = {}
    kb = InlineKeyboardMarkup()
    for cat in perfumes.values():
        for p in cat:
            kb.add(InlineKeyboardButton(p['name'], callback_data=f"choose_{p['name']}"))
    await call.message.answer("Обери аромат:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("choose_"))
async def get_name(call: types.CallbackQuery):
    perfume_name = call.data[7:]
    user_data[call.from_user.id]["perfume"] = perfume_name
    await call.message.answer("Введи своє ім'я:")

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
    kb = InlineKeyboardMarkup()
    for promo in promotions:
        kb.add(InlineKeyboardButton(promo, callback_data=f"promo_{promo}"))
    await message.answer("Обери акцію:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("promo_"))
async def confirm_order(call: types.CallbackQuery):
    uid = call.from_user.id
    promo_key = call.data[6:]
    data = user_data[uid]
    data["promotion"] = promo_key
    price = perfume_prices[data["perfume"]]
    quantity = data["quantity"]
    discount = promotions[promo_key]["discount"]
    subtotal = max(0, price * quantity - discount * quantity)

    delivery_fee = 0 if subtotal >= FREE_DELIVERY_THRESHOLD else DELIVERY_COST
    total = subtotal + delivery_fee
    profit = total - (COST_PRICE * quantity)

    order_summary = (
        f"Підтвердження замовлення:\n"
        f"Аромат: {data['perfume']}\n"
        f"Кількість: {quantity}\n"
        f"Ціна за одиницю: {price} грн\n"
        f"Акція: {promo_key} (-{discount} грн/шт)\n"
        f"Сума: {subtotal} грн\n"
        f"Доставка: {'Безкоштовна' if delivery_fee == 0 else f'{DELIVERY_COST} грн'}\n"
        f"Загальна сума: {total} грн\n"
        f"Ім'я: {data['name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Адреса: {data['address']}"
    )
    sheet.append_row([
        data['name'], data['phone'], data['address'], data['perfume'], quantity,
        promo_key, total, profit, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ])
    await call.message.answer(order_summary + "\n\n✅ Замовлення прийнято! Очікуйте на дзвінок або SMS.")
    del user_data[uid]

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
