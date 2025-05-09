import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
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
DELIVERY_COST = 50

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
        InlineKeyboardButton("🔥 Акції", callback_data="promotions")
    )
    kb.add(InlineKeyboardButton("📝 Замовити", callback_data="order"))
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
    kb = InlineKeyboardMarkup(row_width=2)
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
async def get_city(message: types.Message):
    user_data[message.from_user.id]["phone"] = message.text
    await message.answer("🏙 Введіть місто, куди буде здійснена доставка:")

@dp.callback_query_handler(lambda c: c.data in ["delivery_address", "delivery_np"])
async def ask_for_address(call: types.CallbackQuery):
    method = "Адресна доставка" if call.data == "delivery_address" else "Нова Пошта"
    user_data[call.from_user.id]["delivery_method"] = method
    note = "📍 Введіть місто та повну адресу доставки:" if method == "Адресна доставка" else "🏤 Введіть місто та номер відділення НП:"
    await call.message.answer(note + "‼️ Перевірте уважно правильність даних перед підтвердженням.")

@dp.message_handler(lambda m: "city" not in user_data.get(m.from_user.id, {}))
async def get_delivery_method(message: types.Message):
    user_data[message.from_user.id]["city"] = message.text
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📦 Доставка Нова Пошта", callback_data="np"),
        InlineKeyboardButton("✉️ Доставка Укрпошта", callback_data="ukr")
    )
    kb.add(InlineKeyboardButton("🏠 Адресна доставка", callback_data="address"))
    await message.answer("Оберіть тип доставки:", reply_markup=kb)




@dp.callback_query_handler(lambda c: c.data.startswith("promo_"))
async def confirm_order_prompt(call: types.CallbackQuery):
    uid = call.from_user.id
    promo_key = call.data[6:]
    user_data[uid]["promotion"] = promo_key
    data = user_data[uid]
    price = perfume_prices[data["perfume"]]
    quantity = data["quantity"]
    discount = promotions[promo_key]["discount"]
    subtotal = max(0, price * quantity - discount * quantity)
    delivery_fee = 0 if subtotal >= FREE_DELIVERY_THRESHOLD else DELIVERY_COST
    total = subtotal + delivery_fee
    address_full = f"м. {data['city']}, " + (
        f"НП {data['address']}" if data['delivery_type'] == "np" else 
        f"Укрпошта {data['address']}" if data['delivery_type'] == "ukr" else 
        f"{data['address']}" )
    order_summary = (
        f"🔍 Підтвердження замовлення:
"
        f"Аромат: {data['perfume']}
"
        f"Кількість: {quantity} шт
"
        f"Ціна за одиницю: {price} грн
"
        f"Акція: {promo_key} (-{discount} грн/шт)
"
        f"Сума: {subtotal} грн
"
        f"Доставка: {'Безкоштовна' if delivery_fee == 0 else f'{DELIVERY_COST} грн'}
"
        f"Загальна сума: {total} грн
"
        f"Ім'я: {data['name']}
"
        f"Телефон: {data['phone']}
"
        f"Адреса: {address_full}"
    )
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Так, підтверджую", callback_data="confirm_final"),
        InlineKeyboardButton("❌ Скасувати", callback_data="cancel_order")
    )
    await call.message.answer(order_summary + "

Будь ласка, підтвердіть замовлення:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "confirm_final")
async def finalize_order(call: types.CallbackQuery):
    uid = call.from_user.id
    data = user_data[uid]
    price = perfume_prices[data["perfume"]]
    quantity = data["quantity"]
    discount = promotions[data["promotion"]]["discount"]
    subtotal = max(0, price * quantity - discount * quantity)
    delivery_fee = 0 if subtotal >= FREE_DELIVERY_THRESHOLD else DELIVERY_COST
    total = subtotal + delivery_fee
    profit = total - (COST_PRICE * quantity)

    sheet.append_row([
        data['name'], data['phone'], f"м. {data['city']}, " + (
        f"НП {data['address']}" if data['delivery_type'] == "np" else 
        f"Укрпошта {data['address']}" if data['delivery_type'] == "ukr" else 
        f"{data['address']}" ), data['perfume'], quantity,
        data['promotion'], total, profit, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        uid, "", "✅ Відправлено"
    ])
    analytics_sheet.update("B2", f"=COUNTA({sheet.title}!A2:A)")
    analytics_sheet.update("B3", f"=SUM({sheet.title}!G2:G)")
    analytics_sheet.update("B4", f"=SUM({sheet.title}!H2:H)")
    analytics_sheet.update("B5", f"=INDEX({sheet.title}!D2:D, MODE(MATCH({sheet.title}!D2:D, {sheet.title}!D2:D, 0)))")

    await call.message.answer("✅ Замовлення прийнято! Очікуйте на дзвінок або SMS.")
    del user_data[uid]

@dp.callback_query_handler(lambda c: c.data == "cancel_order")
async def cancel_order(call: types.CallbackQuery):
    await call.message.answer("❌ Замовлення скасовано. Ви можете почати знову, натиснувши /start")
    user_data.pop(call.from_user.id, None)

@dp.callback_query_handler(lambda c: c.data in ["np", "ukr", "address"])
async def get_final_address(call: types.CallbackQuery):
    delivery_type = call.data
    user_data[call.from_user.id]["delivery_type"] = delivery_type
    if delivery_type == "address":
        await call.message.answer("✍️ Введіть повну адресу доставки.‼️ Перевірте уважно перед підтвердженням!")
    else:
        label = "Номер відділення Нової Пошти:" if delivery_type == "np" else "Номер відділення Укрпошти:"
        await call.message.answer(f"✍️ {label}‼️ Перевірте уважно перед підтвердженням!")

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
    kb = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(promo, callback_data=f"promo_{promo}") for promo in promotions]
    for i in range(0, len(buttons), 2):
        kb.row(*buttons[i:i+2])
    await message.answer("Обери акцію:", reply_markup=kb)



async def notify_sent_orders():
    while True:
        await asyncio.sleep(60)  # Перевіряти щохвилини
        rows = sheet.get_all_values()
        header = rows[0]
        if "ЕН" in header:
            en_index = header.index("ЕН")
            chat_index = header.index("Chat ID")
            status_index = header.index("Статус") if "Статус" in header else None
            for i, row in enumerate(rows[1:], start=2):
                if len(row) > en_index and row[en_index] and (len(row) <= chat_index or not row[chat_index].startswith("✅")):
                    try:
                        chat_id = int(row[chat_index])
                        tn_number = row[en_index]
                        await bot.send_message(chat_id, f"📦 Ваше замовлення відправлено!")
                        sheet.update_cell(i, chat_index + 1, f"✅ {tn_number}")
                    except Exception as e:
                        logging.warning(f"Не вдалося надіслати повідомлення: {e}")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(notify_sent_orders())
    executor.start_polling(dp, skip_updates=True, loop=loop)
