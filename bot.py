import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Telegram токен
BOT_TOKEN = '7511346484:AAEm89gjBctt55ge8yEqrfHrxlJ-yS4d56U'
GOOGLE_SHEET_NAME = 'Parfums'
CREDENTIALS_FILE = 'credentials.json'
# === Google Sheets ===
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
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


# Ініціалізація бота і диспетчера
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.MARKDOWN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Стан машини
class OrderStates(StatesGroup):
    name = State()
    phone = State()
    city = State()
    delivery_type = State()
    address_or_post = State()
    confirmation = State()

# Тимчасове збереження кошика

# === Акція: 3-й парфум зі знижкою 50% ===
def apply_third_item_discount(cart):
    if len(cart) >= 3:
        sorted_cart = sorted(cart, key=lambda x: x['price'])
        sorted_cart[2]['price'] = round(sorted_cart[2]['price'] * 0.5, 2)
    return cart
user_carts = {}
user_discounts = {}
user_data = {}

@dp.message_handler(lambda message: message.text == "Як замовити" or message.text.lower() == "/how_to_order")
async def how_to_order(message: types.Message):
    instructions = (
        "🛍 *Як зробити замовлення:*\n"
        "1️⃣ Відкрийте *Каталог* і оберіть парфуми\n"
        "2️⃣ Натисніть *Додати в кошик*\n"
        "3️⃣ Перейдіть у *Кошик* та натисніть *Оформити замовлення*\n"
        "4️⃣ Введіть свої дані (ім’я, телефон, місто, доставка)\n"
        "5️⃣ Підтвердіть замовлення — і ми все надішлемо найближчим часом!\n"
        "🧾 Ви отримаєте повідомлення з номером ТТН після відправки.\n"
    )
    await message.answer(instructions)

@dp.callback_query_handler(lambda c: c.data == "how_to_order")
async def how_to_order_callback(callback: types.CallbackQuery):
    instructions = (
        "🛍 *Як зробити замовлення:*\n"
        "1️⃣ Відкрийте *Каталог* і оберіть парфуми\n"
        "2️⃣ Натисніть *Додати в кошик*\n"
        "3️⃣ Перейдіть у *Кошик* та натисніть *Оформити замовлення*\n"
        "4️⃣ Введіть свої дані (ім’я, телефон, місто, доставка)\n"
        "5️⃣ Підтвердіть замовлення — і ми все надішлемо найближчим часом!\n"
        "🧾 Ви отримаєте повідомлення з номером ТТН після відправки.\n"
    )
    await callback.message.answer(instructions)
    await callback.answer()



@dp.callback_query_handler(lambda c: c.data == "main_menu" or c.data == "start")
async def back_to_main(callback: types.CallbackQuery):
    await bot.send_photo(
    chat_id=callback.message.chat.id,
    photo="https://fleurparfum.net.ua/images/blog/shleifovie-duhi-woman.jpg.pagespeed.ce.3PKNQ9Vn2Z.jpg",  # заміни на своє зображення
    caption=(
        "🧴 *Ласкаво просимо до нашого ароматного світу!*\n\n"
        "🌺 У нашому магазині ви знайдете брендові жіночі, чоловічі та унісекс парфуми — обрані з любов'ю.\n"
        "💸 Ми пропонуємо найкращі ціни та щедрі знижки для нових і постійних клієнтів.\n"
        "🎁 Усі покупці можуть скористатися акціями та отримати приємні подарунки.\n"
        "🚚 Доставка по всій Україні. Безкоштовна — при замовленні від 500 грн.\n\n"
        "👇 Оберіть розділ нижче, щоб почати замовлення або переглянути наші пропозиції."
        ),
        reply_markup=main_menu,
    )
    await callback.answer()
  # Стартове повідомлення та головне меню
main_menu_buttons = [
    [InlineKeyboardButton("🛒 Кошик", callback_data="show_cart"), InlineKeyboardButton("📦Каталог парфум", callback_data="catalog")],
    [InlineKeyboardButton("🔥Акції та бонуси", callback_data="promotions"), InlineKeyboardButton("📉Знижка дня", callback_data="daily_discount")],
    [InlineKeyboardButton("ℹ️Як замовити?", callback_data="how_to_order"), InlineKeyboardButton("💬Відгуки", callback_data="reviews")],
    [InlineKeyboardButton("✒️Зв'язатися з менеджером", url="https://t.me/Dimanicer")]
]
main_menu = InlineKeyboardMarkup(inline_keyboard=main_menu_buttons)
# === Каталог парфумів ===
catalog_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton("👩Жіночі", callback_data="cat_women"), InlineKeyboardButton("Унісекс", callback_data="cat_unisex")],
    [InlineKeyboardButton("🔝Топ продаж", callback_data="cat_top")],
    [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
])

perfume_catalog = {
    "cat_women": [
        {"name": "Chanel Coco Mademoiselle", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA."},
        {"name": "Dior J'adore", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA."}
    ],
    "cat_unisex": [
        {"name": "Tom Ford Tobacco Vanille", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA."},
        {"name": "Byredo Gypsy Water", "price": 200, "photo": "https://example.com/byredo.jpg"}
    ],
    "cat_top": [
        {"name": "Creed Aventus", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA."},
        {"name": "Maison Francis Kurkdjian Baccarat Rouge", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA."}
    ]
}

@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))
async def handle_category(callback: types.CallbackQuery):
    perfumes = perfume_catalog.get(callback.data, [])
    for p in perfumes:
        buttons = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton("➕ Додати до кошика", callback_data=f"add_{p['name']}"), InlineKeyboardButton("🔙 Повернення", callback_data="catalog")],
    [InlineKeyboardButton("🔙 Назад до каталогу", callback_data="catalog"), InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
])

        await bot.send_photo(callback.from_user.id, p['photo'], caption=f"*{p['name']}*\n💸 {p['price']} грн", reply_markup=buttons)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "catalog")
async def show_catalog(callback: types.CallbackQuery):
    await bot.send_message(callback.from_user.id, "Оберіть категорію парфумів:", reply_markup=catalog_menu)
# Знижка дня
daily_discount = {}
last_discount_update = None

def generate_daily_discount():
    global daily_discount, last_discount_update
    all_perfumes = sum(perfume_catalog.values(), [])
    daily_discount = random.choice(all_perfumes)
    last_discount_update = datetime.now().date()

@dp.callback_query_handler(lambda c: c.data == "daily_discount")
async def show_daily_discount(callback: types.CallbackQuery):
    global daily_discount, last_discount_update
    if daily_discount == {} or last_discount_update != datetime.now().date():
        generate_daily_discount()
    p = daily_discount
    discounted_price = int(p['price'] * 0.75)
    caption = (
        f"*Знижка дня!*\n\n"
        f"Сьогодні у нас акція на:\n"
        f"*{p['name']}*\n"
        f"💸 Замість {p['price']} грн — лише {discounted_price} грн!\n\n"
        f"Встигніть скористатися пропозицією!"
    )
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("➕ Додати зі знижкою", callback_data=f"discount_{p['name']}")],
        [InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
    ])
    await bot.send_photo(callback.from_user.id, p['photo'], caption=caption, reply_markup=buttons)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("discount_"))
async def add_discount_to_cart(callback: types.CallbackQuery):
    name = callback.data.replace("discount_", "")
    user_id = callback.from_user.id
    if user_id not in user_carts:
        user_carts[user_id] = []
    user_carts[user_id].append(name + " (зі знижкою)")
    user_discounts[user_id] = name
    await callback.answer("Додано до кошика зі знижкою!")
# === Відгуки з промокодом ===
used_promo_users = set()
PROMO_CODES = ["PROMO10", "DISCOUNT15", "SALE20"]

class ReviewState(StatesGroup):
    waiting_text = State()

@dp.callback_query_handler(lambda c: c.data == "reviews")
async def ask_for_review(callback: types.CallbackQuery):
    await bot.send_message(callback.from_user.id, "✏️ Напишіть свій відгук нижче:")
    await ReviewState.waiting_text.set()
    await callback.answer()

@dp.message_handler(state=ReviewState.waiting_text)
async def receive_review(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in used_promo_users:
        await message.answer("Дякуємо за відгук! Ви вже отримали промокод.")
    else:
        promo = PROMO_CODES.pop() if PROMO_CODES else "PROMO10"
        used_promo_users.add(user_id)
        await message.answer(f"🎁 Дякуємо за відгук! Ваш промокод: *{promo}*")
    await state.finish()

# Блок: Акції та бонуси
@dp.message_handler(lambda message: message.text == "Акції та бонуси")
async def promotions_handler(message: types.Message):
    promo_text = (
        "🎉 *Наявні акції:*\n\n"
        "1️⃣ *3-й парфум зі знижкою -50%*"
        "Купіть 2 будь-які парфуми — третій отримаєте зі знижкою 50%\n\n"
        "2️⃣ *Безкоштовна доставка від 500 грн*\n"
        "Оформіть замовлення на суму від 500 грн (без доставки) — ми доставимо безкоштовно!\n\n"
        "3️⃣ *Знижка для подруг — 10% кожній!*\n"
        "Запросіть подругу — обидві отримаєте знижку 10%.\n\n"
        "4️⃣ *Набір зі знижкою -15%*\n"
        "При покупці 3+ парфумів — знижка 15% на кожен."
    )
    await message.answer(promo_text, reply_markup=main_menu)
      
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📄 Умови 3-й парфум", callback_data="promo_cond_1"),
        InlineKeyboardButton("📦 Перейти до каталогу", callback_data="catalog"), InlineKeyboardButton("🔙 Повернення", callback_data="main_menu"),
        InlineKeyboardButton("📄 Умови безкоштовної доставки", callback_data="promo_cond_2"),
        InlineKeyboardButton("📦 Перейти до каталогу", callback_data="catalog"),
        InlineKeyboardButton("📄 Умови з подругою", callback_data="promo_cond_3"),
        InlineKeyboardButton("📦 Перейти до каталогу", callback_data="catalog"),
        InlineKeyboardButton("📄 Умови набору зі знижкою", callback_data="promo_cond_4"),
        InlineKeyboardButton("📦 Перейти до каталогу", callback_data="catalog")
    )

    await message.answer(promo_text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith("promo_cond_"))
async def promo_conditions(call: types.CallbackQuery):
    conditions = {
        "promo_cond_1": "🎉 *3-й парфум зі знижкою -50%*"
"Купіть будь-які 2 парфуми та отримайте третій зі знижкою 50%."
"Знижка застосовується до найменшого за ціною товару. Доставка не входить в облік.",
        "promo_cond_2": "🚚 *Безкоштовна доставка від 500 грн*"
"Загальна сума без урахування доставки має перевищувати 500 грн.",
        "promo_cond_3": "👭 *Знижка для подруг — 10% кожній!*"
"Надішліть посилання подрузі. Обидві отримаєте знижку після замовлення.",
        "promo_cond_4": "🎁 *Набір зі знижкою -15%*"
"При купівлі 3 або більше парфумів — знижка 15% на кожен."
    }
    await call.message.answer(conditions[call.data])
    await call.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("add_"))
async def add_to_cart_callback(callback: types.CallbackQuery):
    perfume_name = callback.data[4:]
    user_id = callback.from_user.id
    if user_id not in user_carts:
        user_carts[user_id] = []
    user_carts[user_id].append({"name": perfume_name, "price": 200})
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🛒 Переглянути кошик", callback_data="show_cart")],
        [InlineKeyboardButton("🧾 Оформити замовлення", callback_data="checkout")]
    ])
    await callback.message.answer(f"✅ {perfume_name} додано до кошика.", reply_markup=buttons)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "show_cart")
async def show_cart_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await callback.message.answer("🛒 Ваш кошик порожній.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("🔙 Повернення", callback_data="main_menu")]]))
        return

    cart = apply_third_item_discount(cart)
    text = "*Ваш кошик:*"
    total = 0
    keyboard = InlineKeyboardMarkup(row_width=2)
    counted = {}
    for item in cart:
        key = item['name']
        if key in counted:
            counted[key]['count'] += 1
            counted[key]['total'] += item['price']
        else:
            counted[key] = {'price': item['price'], 'count': 1, 'total': item['price']}

    i = 1
    for name, details in counted.items():
        text += f"{i}. {name} — {details['count']} шт. x {details['price']} грн = {details['total']} грн
"
        keyboard.add(
            InlineKeyboardButton(f"➖", callback_data=f"decrease_{name}"),
            InlineKeyboardButton(f"➕", callback_data=f"increase_{name}")
        )
        total += details['total']
        i += 1

    discount = user_discounts.get(user_id, 0)
    final_price = total - discount
    text += f"💵 Сума без знижок: {total} грн"
    if discount:
        text += f"🎁 Знижка: {discount} грн"
        text += f"✅ До сплати: {final_price} грн"

    keyboard.add(
        InlineKeyboardButton("🧾 Оформити замовлення", callback_data="checkout"),
        InlineKeyboardButton("🔙 Повернення", callback_data="main_menu"),
        InlineKeyboardButton("🧹 Очистити кошик", callback_data="clear_cart")
    )
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("increase_"))
async def increase_item_quantity(callback: types.CallbackQuery):
    name = callback.data.replace("increase_", "")
    user_id = callback.from_user.id
    user_carts.setdefault(user_id, []).append({"name": name, "price": 200})
    await show_cart_callback(callback)

@dp.callback_query_handler(lambda c: c.data.startswith("decrease_"))
async def decrease_item_quantity(callback: types.CallbackQuery):
    name = callback.data.replace("decrease_", "")
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])
    for i, item in enumerate(cart):
        if item["name"] == name:
            cart.pop(i)
            break
    await show_cart_callback(callback)

@dp.callback_query_handler(lambda c: c.data == "clear_cart")
async def clear_cart_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_carts[user_id] = []
    await callback.message.answer("🧹 Кошик очищено.")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "checkout")
async def checkout_handler(callback: types.CallbackQuery):
    await callback.message.answer("✍️ Введіть ваше *ім'я* для оформлення замовлення:")
    await OrderStates.name.set()
    await callback.answer()


@dp.message_handler(lambda message: message.text.lower().startswith("додати "))
async def add_to_cart(message: types.Message):
    user_id = message.from_user.id
    parts = message.text.split(" ", 2)
    if len(parts) < 3:
        await message.answer("❗ Введіть команду у форматі: Додати Назва Ціна")
        return
    name = parts[1]
    try:
        price = int(parts[2])
    except ValueError:
        await message.answer("❗ Ціна повинна бути числом.")
        return

    if user_id not in user_carts:
        user_carts[user_id] = []
    user_carts[user_id].append({"name": name, "price": price})
    await message.answer(f"✅ {name} додано до кошика за {price} грн.")

# Переглянути кошик
@dp.message_handler(commands=["кошик", "cart"])
async def view_cart(message: types.Message):
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await message.answer("🛒 Ваш кошик порожній.")
        return
    text = "*Ваш кошик:*\n"
    total = 0
    for i, item in enumerate(cart, 1):
        text += f"{i}. {item['name']} - {item['price']} грн\n"
        total += item['price']
    discount = user_discounts.get(user_id, 0)
    final_price = total - discount
    text += f"\n💵 Загальна сума: {total} грн"
    if discount:
        text += f"\n🎁 Знижка: {discount} грн"
        text += f"\n✅ До сплати: {final_price} грн"
    await message.answer(text)

# Очистити кошик
@dp.message_handler(commands=["очистити", "clear"])
async def clear_cart(message: types.Message):
    user_id = message.from_user.id
    user_carts[user_id] = []
    await message.answer("🧹 Кошик очищено.")

# Видалити товар із кошика
@dp.message_handler(lambda message: message.text.lower().startswith("видалити "))
async def remove_from_cart(message: types.Message):
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
    try:
        index = int(message.text.split()[1]) - 1
        if 0 <= index < len(cart):
            removed = cart.pop(index)
            await message.answer(f"❌ Видалено: {removed['name']}")
        else:
            await message.answer("❗ Невірний номер товару.")
    except (IndexError, ValueError):
        await message.answer("❗ Введіть команду у форматі: Видалити 1")

# === Оформлення замовлення ===


@dp.message_handler(state=OrderStates.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введіть ваш *номер телефону*:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("🔙 Повернення", callback_data="back")]]))
    await OrderStates.phone.set()

@dp.message_handler(state=OrderStates.phone)
async def get_phone(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or len(message.text) != 10:
        await message.answer("❗ Номер телефону має містити 10 цифр без +38. Наприклад: 0931234567")
        return
    await state.update_data(phone=message.text)
    await message.answer("Введіть *місто доставки*:")
    await OrderStates.next()



@dp.message_handler(state=OrderStates.city)
async def get_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("На відділення", callback_data="delivery_post"),
        InlineKeyboardButton("Кур'єром на адресу", callback_data="delivery_address")
    )
    await message.answer("Оберіть *тип доставки*:", reply_markup=keyboard)
    await OrderStates.next()

@dp.callback_query_handler(lambda c: c.data == "back", state=OrderStates.phone)
async def back_to_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Введіть ваше *ім'я* для оформлення замовлення:")
    await OrderStates.name.set()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back", state=OrderStates.city)
async def back_to_phone(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📞 Введіть ваш номер телефону:")
    await OrderStates.phone.set()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back", state=OrderStates.delivery_type)
async def back_to_city(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🏙 Введіть ваше місто:")
    await OrderStates.city.set()
    await callback.answer()

@dp.callback_query_handler(state=OrderStates.delivery_type)
async def get_delivery_type(callback: types.CallbackQuery, state: FSMContext):
    delivery_type = callback.data
    await state.update_data(delivery_type=delivery_type)
    if delivery_type == "delivery_post":
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("Нова Пошта", callback_data="nova_post"),
            InlineKeyboardButton("Укрпошта", callback_data="ukr_post")
        )
        await callback.message.answer("Оберіть службу доставки:", reply_markup=keyboard)
    else:
        await callback.message.answer("Введіть *Номер відділення*:")
        await OrderStates.address_or_post.set()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data in ["nova_post", "ukr_post"])
async def get_post_service(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(post_service=callback.data)
    await callback.message.answer("Введіть *номер або назву відділення*:")
    await OrderStates.address_or_post.set()
    await callback.answer()

@dp.message_handler(state=OrderStates.address_or_post)
async def get_address_or_post(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❗ Введіть лише номер відділення цифрами.")
        return
    data = await state.get_data()
    delivery_type = data['delivery_type']
    if delivery_type == "delivery_post":
        post_service = data.get('post_service', '-')
        address_or_post = f"{post_service.upper()} {message.text}"
    else:
        address_or_post = message.text

    await state.update_data(address_or_post=address_or_post)
    data = await state.get_data()
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
    cart = apply_third_item_discount(cart)

    text_items = ""
    total = 0
    for i, item in enumerate(cart, 1):
        text_items += f"{i}. {item['name']} — {item['price']} грн"
        total += item['price']

    discount = user_discounts.get(user_id, 0)
    final = total - discount

    order_summary = (
        f"📦 *Перевірте замовлення перед підтвердженням:*"
        f"👤 *Ім’я:* {data['name']}"
        f"📞 *Телефон:* {data['phone']}"
        f"🏙 *Місто:* {data['city']}"
        f"🚚 *Тип доставки:* {'Відділення' if delivery_type == 'delivery_post' else 'Адресна'}"
        f"📍 *Адреса / Відділення:* {data['address_or_post']}"
        f"🛍 *Товари в кошику:*{text_items}"
        f"💵 *Сума без знижок:* {total} грн"
        f"🎁 *Знижка:* {discount} грн"
        f"✅ *До сплати:* {final} грн")
  

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Підтвердити", callback_data="confirm_order"),
        InlineKeyboardButton("❌ Скасувати", callback_data="cancel_order")
    )
    await message.answer(order_summary, reply_markup=keyboard)
    await OrderStates.confirmation.set()

@dp.callback_query_handler(state=OrderStates.confirmation)
async def confirm_order(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "confirm_order":
        data = await state.get_data()

        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")
        name = data['name']
        phone = data['phone']
        city = data['city']
        delivery_type = 'Відділення' if data['delivery_type'] == 'delivery_post' else 'Адреса'
        address = data['address_or_post']
        user_id = callback.from_user.id

        cart_items = user_carts.get(user_id, [])
        cart_items = apply_third_item_discount(cart_items)
        order_description = "; ".join([f"{item['name']} ({item['price']} грн)" for item in cart_items]) if cart_items else "-"
        total_sum = sum([item['price'] for item in cart_items]) if cart_items else 0
        discount = user_discounts.get(user_id, 0)
        final_price = total_sum - discount

        sheet.append_row([
            date,
            time,
            name,
            phone,
            city,
            delivery_type,
            address,
            order_description,
            final_price,
            discount,
            user_id,
            ""
        ])

        await callback.message.answer("🎉 Замовлення підтверджено! Очікуйте на повідомлення з номером ТТН після відправки.")
    else:
        await callback.message.answer("❌ Замовлення скасовано.")
    await state.finish()
    await callback.answer()



@dp.callback_query_handler(lambda c: c.data == "cancel_order", state=OrderStates.confirmation)
async def cancel_order(callback: types.CallbackQuery, state: FSMContext):
    await bot.send_message(callback.from_user.id, "❌ Замовлення скасовано.")
    await state.finish()


@dp.message_handler(commands=["start"])
async def handle_start(message: types.Message):
    await bot.send_photo(
        chat_id=message.chat.id,
        photo="https://fleurparfum.net.ua/images/blog/shleifovie-duhi-woman.jpg.pagespeed.ce.3PKNQ9Vn2Z.jpg",
        caption=(
            "🧴 *Ласкаво просимо до нашого ароматного світу!*\n\n"
            "🌺 У нашому магазині ви знайдете брендові жіночі, чоловічі та унісекс парфуми — обрані з любов'ю.\n\n"
            "💸 Ми пропонуємо найкращі ціни та щедрі знижки для нових і постійних клієнтів.\n\n"
            "🎁 Усі покупці можуть скористатися акціями та отримати приємні подарунки.\n\n"
            "🚚 Доставка по всій Україні. Безкоштовна — при замовленні від 500 грн.\n\n"
            "👇 Оберіть розділ нижче, щоб почати замовлення або переглянути наші пропозиції.\n\n"
        ),
        reply_markup=main_menu
    )

@dp.message_handler()
async def auto_start_from_any_message(message: types.Message):
    await bot.send_photo(
        chat_id=message.chat.id,
        photo="https://fleurparfum.net.ua/images/blog/shleifovie-duhi-woman.jpg.pagespeed.ce.3PKNQ9Vn2Z.jpg",
        caption=(
            "🧴 *Ласкаво просимо до нашого ароматного світу!*\n\n"
        "🌺 У нашому магазині ви знайдете брендові жіночі, чоловічі та унісекс парфуми — обрані з любов'ю.\n"
        "💸 Ми пропонуємо найкращі ціни та щедрі знижки для нових і постійних клієнтів.\n"
        "🎁 Усі покупці можуть скористатися акціями та отримати приємні подарунки.\n"
        "🚚 Доставка по всій Україні. Безкоштовна — при замовленні від 500 грн.\n\n"
        "👇 Оберіть розділ нижче, щоб почати замовлення або переглянути наші пропозиції."
        ),
        reply_markup=main_menu
    )

@dp.message_handler(commands=["track_ttns"])
async def track_pending_orders(message: types.Message):
    all_data = sheet.get_all_values()
    for i, row in enumerate(all_data[1:], start=2):  # пропускаємо заголовок
        if len(row) >= 12:
            chat_id = row[10].strip()
            ttn = row[11].strip()
            status = row[12].strip() if len(row) > 12 else ""
            if ttn and not status:
                try:
                    await bot.send_message(int(chat_id), f"📦 Ваше замовлення надіслано!Номер накладної: *{ttn}*")
                    sheet.update_cell(i, 13, "✅ надіслано")
                    await asyncio.sleep(1)
                except Exception as e:
                    logging.error(f"Помилка при надсиланні ТТН: {e}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
