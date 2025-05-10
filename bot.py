import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, ReplyKeyboardRemove
from aiogram.utils import executor
from datetime import datetime
import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Налаштування ===
BOT_TOKEN = '7511346484:AAEm89gjBctt55ge8yEqrfHrxlJ-yS4d56U'
GOOGLE_SHEET_NAME = 'Parfums'
CREDENTIALS_FILE = 'credentials.json'
COST_PRICE = 80
FREE_DELIVERY_THRESHOLD = 500
DELIVERY_COST = 70

# === Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
try:
    workbook = client.open(GOOGLE_SHEET_NAME)
except gspread.SpreadsheetNotFound:
    print("❗ Таблицю не знайдено. Перевірте назву або доступи.")
    raise
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
dp = Dispatcher(bot)
user_data = {}
user_cart = {}

# === Обробка команди /start ===
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    user_data[uid] = {"step": "name"}
    user_cart[uid] = []
    await message.answer("👋 Вітаємо! Введіть ваше ім'я:")

# === Обробка етапів оформлення замовлення ===
@dp.message_handler(lambda m: m.text)
async def handle_order_steps(message: types.Message):
    uid = message.from_user.id
    data = user_data.setdefault(uid, {})
    step = data.get("step", "name")

    if step == "name":
        data["name"] = message.text
        data["step"] = "phone"
        await message.answer("📱 Введіть номер телефону:")
    elif step == "phone":
        data["phone"] = message.text
        data["step"] = "city"
        await message.answer("🏙 Введіть місто, куди буде здійснена доставка:")
    elif step == "city":
        data["city"] = message.text
        data["step"] = "delivery"
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("📦 Нова Пошта", callback_data="delivery_np"),
            InlineKeyboardButton("✉️ Укрпошта", callback_data="delivery_ukr")
        )
        kb.add(InlineKeyboardButton("🏠 Адресна доставка", callback_data="delivery_address"))
        await message.answer("🚚 Оберіть тип доставки:", reply_markup=kb)
    else:
        await message.answer("❗ Введення вже завершено або почніть спочатку з /start")

# === Обробка вибору доставки ===
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("delivery_"))
async def process_delivery_choice(callback_query: types.CallbackQuery):
    uid = callback_query.from_user.id
    data = user_data.get(uid, {})
    if not data:
        await callback_query.message.answer("Будь ласка, почніть замовлення з /start")
        return

    delivery_type = callback_query.data.replace("delivery_", "")
    delivery_map = {
        "np": "Нова Пошта",
        "ukr": "Укрпошта",
        "address": "Адресна доставка"
    }
    delivery_name = delivery_map.get(delivery_type, "Невідомо")
    data["delivery"] = delivery_type

    # Розрахунок суми замовлення
    cart = user_cart.get(uid, [])
    total = sum(item['price'] for item in cart)
    delivery_fee = 0 if total >= FREE_DELIVERY_THRESHOLD else DELIVERY_COST
    final_total = total + delivery_fee

    summary = (
        f"✅ Замовлення підтверджено!\n\n"
        f"👤 Ім'я: {data.get('name')}\n"
        f"📞 Телефон: {data.get('phone')}\n"
        f"🏙 Місто: {data.get('city')}\n"
        f"🚚 Доставка: {delivery_name}\n"
        f"🛒 Кошик: {', '.join([item['name'] for item in cart])}\n"
        f"💵 Сума: {total} грн\n"
        f"🚚 Доставка: {delivery_fee} грн\n"
        f"💰 Всього до сплати: {final_total} грн"
    )

    await callback_query.message.edit_reply_markup()
    await callback_query.message.answer(summary)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([
        now,
        data.get("name", ""),
        data.get("phone", ""),
        data.get("city", ""),
        delivery_name,
        ", ".join([item['name'] for item in cart]),
        total,
        delivery_fee,
        final_total
    ])

    user_data.pop(uid, None)
    user_cart.pop(uid, None)

# === Додати товар до кошика (приклад функції) ===
@dp.message_handler(commands=["add"])
async def add_to_cart(message: types.Message):
    uid = message.from_user.id
    if uid not in user_cart:
        user_cart[uid] = []

    item = {"name": "Chanel No. 5", "price": 120}
    user_cart[uid].append(item)
    await message.answer(f"✅ {item['name']} додано до кошика!")

# === Перегляд кошика ===
@dp.message_handler(commands=["cart"])
async def view_cart(message: types.Message):
    uid = message.from_user.id
    cart = user_cart.get(uid, [])

    if not cart:
        await message.answer("🛒 Ваш кошик порожній.")
        return

    text = "🛍 Ваш кошик:\n"
    total = 0
    for idx, item in enumerate(cart, start=1):
        text += f"{idx}. {item['name']} — {item['price']} грн\n"
        total += item['price']

    text += f"\n💵 Загальна сума: {total} грн"
    await message.answer(text)

# === Видалення товару з кошика ===
@dp.message_handler(commands=["remove"])
async def remove_from_cart(message: types.Message):
    uid = message.from_user.id
    cart = user_cart.get(uid, [])

    if not cart:
        await message.answer("❌ Ваш кошик порожній. Нічого видаляти.")
        return

    args = message.get_args()
    if not args.isdigit():
        await message.answer("❗ Введіть номер товару для видалення. Наприклад: /remove 1")
        return

    index = int(args) - 1
    if 0 <= index < len(cart):
        removed = cart.pop(index)
        await message.answer(f"🗑 {removed['name']} видалено з кошика.")
    else:
        await message.answer("❗ Невірний номер товару.")
