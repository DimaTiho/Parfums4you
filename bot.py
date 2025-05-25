# main.py
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from datetime import datetime
from html import escape as escape_md
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio

# ====== Налаштування ======
API_TOKEN = 'YOUR_BOT_TOKEN_HERE'

# Google Sheets налаштування
GS_CREDENTIALS_FILE = 'path_to_google_credentials.json'
GS_SPREADSHEET_NAME = 'YourGoogleSheetName'
GS_WORKSHEET_NAME = 'Orders'

# ====== Логування ======
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.MARKDOWN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ====== Пам'ять користувачів (псевдо-база) ======
user_carts = {}
user_discounts = {}

# ID та ціна для "Знижки дня"
DISCOUNT_DAY_ITEM_ID = 101
DISCOUNT_DAY_PRICE = 150

# ====== FSM Стан для оформлення замовлення ======
class OrderStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_city = State()
    waiting_for_delivery_type = State()
    waiting_for_address = State()
    waiting_for_post_service = State()
    waiting_for_post_number = State()
    confirmation = State()

# ====== Каталог парфумів (приклад) ======
catalog_items = [
    {'id': 1, 'name': 'Парфуми A', 'price': 350},
    {'id': 2, 'name': 'Парфуми B', 'price': 450},
    {'id': DISCOUNT_DAY_ITEM_ID, 'name': 'Парфуми зі Знижкою дня', 'price': 200},
]

# ====== Клавіатури ======
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🛍 Каталог", callback_data="catalog"),
        InlineKeyboardButton("🛒 Кошик", callback_data="cart"),
        InlineKeyboardButton("🔥 Знижка дня!", callback_data="discount_day"),
        InlineKeyboardButton("🎁 Акції та бонуси", callback_data="promotions"),
    )
    return kb

def catalog_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    for item in catalog_items:
        kb.add(InlineKeyboardButton(f"{item['name']} — {item['price']} грн", callback_data=f"add_{item['id']}"))
    kb.add(InlineKeyboardButton("🏠 Головне меню", callback_data="home"))
    return kb

def cart_keyboard(user_id):
    kb = InlineKeyboardMarkup(row_width=3)
    items = user_carts.get(user_id, [])
    for i, item in enumerate(items):
        kb.add(
            InlineKeyboardButton("➖", callback_data=f"minus:{i}"),
            InlineKeyboardButton(f"{item['name']} x{item['qty']}", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data=f"plus:{i}")
        )
    kb.add(
        InlineKeyboardButton("✅ Оформити", callback_data="checkout"),
        InlineKeyboardButton("🗑 Очистити", callback_data="clear_cart"),
        InlineKeyboardButton("🏠 Головне меню", callback_data="home")
    )
    return kb

def promotions_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("1+1 зі знижкою 30% на другий товар", callback_data="promo_1plus1"),
        InlineKeyboardButton("Пакет 4 парфуми за 680 грн", callback_data="promo_pack4"),
        InlineKeyboardButton("Безкоштовна доставка від 600 грн", callback_data="promo_free_delivery"),
        InlineKeyboardButton("Розіграш серед нових покупців", callback_data="promo_raffle"),
        InlineKeyboardButton("🏠 Головне меню", callback_data="home"),
    )
    return kb

# ====== Обробники повідомлень та callback ======
@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    await message.answer("👋 Вітаємо! Оберіть розділ:", reply_markup=main_menu())

@dp.callback_query_handler(text="home")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text("👋 Вітаємо! Оберіть розділ:", reply_markup=main_menu())
    await callback.answer()

# --- Каталог ---
@dp.callback_query_handler(text="catalog")
async def show_catalog(callback: types.CallbackQuery):
    await callback.message.edit_text("🛍 Оберіть товар:", reply_markup=catalog_keyboard())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("add_"))
async def add_to_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    item_id = int(callback.data.split("_")[1])
    item = next((i for i in catalog_items if i['id'] == item_id), None)
    if item is None:
        await callback.answer("Товар не знайдено", show_alert=True)
        return

    cart = user_carts.setdefault(user_id, [])
    existing = next((x for x in cart if x['id'] == item_id), None)
    if existing:
        existing['qty'] += 1
    else:
        cart.append({'id': item['id'], 'name': item['name'], 'price': item['price'], 'qty': 1})

    await callback.answer(f"Додано {item['name']} до кошика")
    # Оновити повідомлення із каталогу або показати кошик?
    await show_cart_callback(callback)

# --- Кошик ---
async def show_cart_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    items = user_carts.get(user_id, [])

    if not items:
        await callback.message.edit_text("🛒 Ваш кошик порожній.", reply_markup=main_menu())
        await callback.answer()
        return

    text = "*Ваш кошик:*\n"
    total = 0
    discount = 0

    for item in items:
        price = item['price']
        # Знижка дня на конкретний товар
        if item['id'] == DISCOUNT_DAY_ITEM_ID:
            price = DISCOUNT_DAY_PRICE
        line_price = price * item['qty']
        total += line_price
        text += f"- {item['name']} x{item['qty']} = {line_price} грн\n"

    # Акція: 20% знижка при 5+ одиниць у кошику (приклад)
    count_items = sum(item['qty'] for item in items)
    if count_items >= 5:
        discount = int(total * 0.2)
        text += "\n🎁 *Знижка 20% за кількість застосована.*"

    final = total - discount
    text += f"\n\n💵 *Сума:* {total} грн\n🎁 *Знижка:* {discount} грн\n✅ *До сплати:* {final} грн"

    await callback.message.edit_text(text, reply_markup=cart_keyboard(user_id))
    await callback.answer()

@dp.callback_query_handler(text="cart")
async def show_cart(callback: types.CallbackQuery):
    await show_cart_callback(callback)

@dp.callback_query_handler(lambda c: c.data.startswith("plus:") or c.data.startswith("minus:"))
async def change_quantity(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    index = int(callback.data.split(":")[1])
    cart = user_carts.get(user_id, [])
    if 0 <= index < len(cart):
        if callback.data.startswith("plus:"):
            cart[index]['qty'] += 1
        elif callback.data.startswith("minus:") and cart[index]['qty'] > 1:
            cart[index]['qty'] -= 1

    await show_cart_callback(callback)

@dp.callback_query_handler(text="clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_carts[user_id] = []
    await callback.message.edit_text("🗑 Кошик очищено.", reply_markup=main_menu())
    await callback.answer()

@dp.callback_query_handler(text="checkout")
async def checkout_start(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not user_carts.get(user_id):
        await callback.answer("Кошик порожній!", show_alert=True)
        return
    await callback.message.answer("Введіть Ваше ПІБ:")
    await OrderStates.waiting_for_name.set()
    await callback.answer()

# --- Знижка дня ---
@dp.callback_query_handler(text="discount_day")
async def show_discount_day(callback: types.CallbackQuery):
    # Вивід знижки дня (приклад)
    item = next((i for i in catalog_items if i['id'] == DISCOUNT_DAY_ITEM_ID), None)
    if item is None:
        await callback.answer("Позиція зі знижкою дня недоступна.", show_alert=True)
        return
    text = (f"🔥 *Знижка дня!*\n\n"
            f"{item['name']}\n"
            f"Ціна зі знижкою: {DISCOUNT_DAY_PRICE} грн (звичайна {item['price']} грн)\n\n"
            f"Натисніть кнопку, щоб додати до кошика.")
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(f"Додати {item['name']}", callback_data=f"add_{item['id']}"))
    kb.add(InlineKeyboardButton("🏠 Головне меню", callback_data="home"))
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

# --- Акції та бонуси ---
@dp.callback_query_handler(text="promotions")
async def show_promotions(callback: types.CallbackQuery):
    text = (
        "🎁 *Акції та бонуси*\n\n"
        "1️⃣ 1+1 зі знижкою 30% на другий товар\n"
        "2️⃣ Пакетна пропозиція: 4 парфуми за 680 грн (рівно 4 одиниці)\n"
        "3️⃣ Безкоштовна доставка від 600 грн\n"
        "4️⃣ Розіграш серед нових покупців\n\n"
        "Обирайте акцію, щоб дізнатись подробиці."
    )
    await callback.message.edit_text(text, reply_markup=promotions_keyboard())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("promo_"))
async def promo_details(callback: types.CallbackQuery):
    promo = callback.data[6:]
    text = ""
    if promo == "1plus1":
        text = (
            "1+1 зі знижкою 30% на другий товар:\n"
            "- Купуйте 2 товари,\n"
            "- Другий — зі знижкою 30%\n"
            "Автоматично застосовується в кошику."
        )
    elif promo == "pack4":
        text = (
            "Пакетна пропозиція:\n"
            "- Рівно 4 парфуми за 680 грн.\n"
            "Знижка застосовується тільки при покупці 4 одиниць."
        )
    elif promo == "free_delivery":
        text = (
            "Безкоштовна доставка:\n"
            "- При замовленні від 600 грн доставка безкоштовна."
        )
    elif promo == "raffle":
        text = (
            "Розіграш серед нових покупців:\n"
            "- Зареєструйтеся як новий клієнт,\n"
            "- Отримайте шанс виграти приз!"
        )
    else:
        text = "Інформація про акцію відсутня."

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("⬅ Назад", callback_data="promotions"),
        InlineKeyboardButton("🏠 Головне меню", callback_data="home")
    )
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

# ====== FSM Оформлення замовлення ======
@dp.message_handler(state=OrderStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введіть Ваш номер телефону:")
    await OrderStates.next()

@dp.message_handler(state=OrderStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    # Проста перевірка номера (можна покращити)
    if not phone.replace("+", "").replace("-", "").isdigit():
        await message.answer("Будь ласка, введіть коректний номер телефону.")
        return
    await state.update_data(phone=phone)
    await message.answer("Введіть Ваше місто:")
    await OrderStates.next()

@dp.message_handler(state=OrderStates.waiting_for_city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Адресна доставка", callback_data="delivery_address"),
        InlineKeyboardButton("Доставка у відділення", callback_data="delivery_post")
    )
    await message.answer("Оберіть тип доставки:", reply_markup=kb)
    await OrderStates.next()

@dp.callback_query_handler(lambda c: c.data in ["delivery_address", "delivery_post"], state=OrderStates.waiting_for_delivery_type)
async def process_delivery_type(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "delivery_address":
        await state.update_data(delivery_type="address")
        await bot.send_message(callback.from_user.id, "Введіть адресу доставки:")
        await OrderStates.waiting_for_address.set()
    else:
        await state.update_data(delivery_type="post")
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("Нова Пошта", callback_data="post_service_np"),
            InlineKeyboardButton("Укрпошта", callback_data="post_service_up")
        )
        await bot.send_message(callback.from_user.id, "Оберіть поштову службу:", reply_markup=kb)
    await callback.answer()

@dp.message_handler(state=OrderStates.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await confirm_order(message, state)

@dp.callback_query_handler(lambda c: c.data in ["post_service_np", "post_service_up"], state=OrderStates.waiting_for_post_service)
async def process_post_service(callback: types.CallbackQuery, state: FSMContext):
    service = "Нова Пошта" if callback.data == "post_service_np" else "Укрпошта"
    await state.update_data(post_service=service)
    await bot.send_message(callback.from_user.id, f"Введіть номер відділення {service}:")
    await OrderStates.waiting_for_post_number.set()
    await callback.answer()

@dp.message_handler(state=OrderStates.waiting_for_post_number)
async def process_post_number(message: types.Message, state: FSMContext):
    await state.update_data(post_number=message.text)
    await confirm_order(message, state)

async def confirm_order(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await message.answer("Кошик порожній. Оформлення скасовано.")
        await state.finish()
        return
text = f"📝 *Підтвердження замовлення*\n\n"
text += f"Ім'я: {escape_md(data.get('name',''))}\n"
text += f"Телефон: {escape_md(data.get('phone',''))}\n"
text += f"Місто: {escape_md(data.get('city',''))}\n"
delivery_type = data.get('delivery_type')
if delivery_type == "address":
    text += f"Доставка: Адресна\nАдреса: {escape_md(data.get('address',''))}\n"
else:
    text += (f"Доставка: Відділення\n"
             f"Служба: {escape_md(data.get('post_service',''))}\n"
             f"Відділення №: {escape_md(data.get('post_number',''))}\n")
text += "\n*Ваші товари:*\n"
total = 0
for item in cart:
    price = item['price']
    if item['id'] == DISCOUNT_DAY_ITEM_ID:
        price = DISCOUNT_DAY_PRICE
    line_price = price * item['qty']
    total += line_price
    text += f"- {item['name']} x{item['qty']} = {line_price} грн\n"
text += f"\n*Всього до оплати:* {total} грн\n\n"
text += "Підтвердіть замовлення або скасуйте."

kb = InlineKeyboardMarkup()
kb.add(
    InlineKeyboardButton("✅ Підтвердити", callback_data="order_confirm"),
    InlineKeyboardButton("❌ Відмінити", callback_data="order_cancel")
)
await message.answer(text, reply_markup=kb)
await OrderStates.confirmation.set()

@dp.callback_query_handler(text="order_cancel", state=OrderStates.confirmation)
async def order_cancel(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("❌ Замовлення скасовано.")
    await state.finish()
    user_carts[callback.from_user.id] = []
    await callback.answer()
user_carts[callback.from_user.id] = []

@dp.callback_query_handler(text="order_confirm", state=OrderStates.confirmation)
async def order_confirm(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    cart = user_carts.get(user_id, [])
    await callback.answer("Дякуємо! Ваше замовлення прийнято.")
# Запис у Google Sheets
    order_text = ""
    for item in cart:
        price = item['price']
        if item['id'] == DISCOUNT_DAY_ITEM_ID:
            price = DISCOUNT_DAY_PRICE
        order_text += f"{item['name']} x{item['qty']} ({price} грн); "

row = [
    str(user_id),
    data.get('name', ''),
    data.get('phone', ''),
    data.get('city', ''),
    data.get('delivery_type', ''),
    data.get('address', '') if data.get('delivery_type') == 'address' else '',
    data.get('post_service', '') if data.get('delivery_type') == 'post' else '',
    data.get('post_number', '') if data.get('delivery_type') == 'post' else '',
    order_text.strip(),
    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ""  # поле для ТТН (номер накладної), буде заповнене адміном
]

success = await write_order_to_gs(row)
if success:
    await callback.message.answer("✅ Замовлення збережено. Чекайте на номер накладної (ТТН).")
else:
    await callback.message.answer("⚠ Сталася помилка при збереженні замовлення. Спробуйте пізніше.")

user_carts[user_id] = []
await state.finish()

====== Функція запису в Google Sheets ======
async def write_order_to_gs(row):
    loop = asyncio.get_event_loop()
    try:
        def gs_job():
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_name(GS_CREDENTIALS_FILE, scope)
            client = gspread.authorize(creds)
            sheet = client.open(GS_SPREADSHEET_NAME).worksheet(GS_WORKSHEET_NAME)
            sheet.append_row(row)
    await loop.run_in_executor(None, gs_job)
        return True
    except Exception as e:
        logging.error(f"GS error: {e}")
        return False

====== Обробка повідомлень - будь-яке повідомлення відкриває головне меню ======

@dp.message_handler()
async def any_message(message: types.Message):
    await message.answer("👋 Вітаємо! Оберіть розділ:", reply_markup=main_menu())
====== Запуск бота ======
if name == "main":
executor.start_polling(dp, skip_updates=True)

markdown
Копировать
Редактировать
