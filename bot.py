import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
from aiogram.utils.markdown import escape_md  # Безпека Markdown

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Конфігурація
BOT_TOKEN = '7511346484:AAEm89gjBctt55ge8yEqrfHrxlJ-yS4d56U'
GOOGLE_SHEET_NAME = 'Parfums'
CREDENTIALS_FILE = 'credentials.json'

# Google Sheets
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

# Ініціалізація бота
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.MARKDOWN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Стан оформлення
class OrderStates(StatesGroup):
    name = State()
    phone = State()
    city = State()
    delivery_type = State()
    post_service = State()
    address_or_post = State()
    confirmation = State()

# Зберігання даних користувачів
user_carts = {}
user_discounts = {}
user_data = {}

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
from aiogram.utils.markdown import escape_md  # ✅ Додано для безпеки Markdown

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
    post_service = State()
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
            "🌺 У нас ви знайдете брендові жіночі, чоловічі та унісекс парфуми — обрані з любов'ю.\n\n"
            "💸 Ми пропонуємо найкращі послуги та щедрі знижки для нових і постійних клієнтів.\n\n"
            "🎁 Усі охочі можуть скористатися акціями та отримати приємні подарунки.\n\n"
            "🚚 Відправка Новою Поштою/Укрпоштою. Доставка - за наш рахунок при великому замовленні.\n\n"
            "👇 Оберіть розділ нижче, щоб почати замовлення або переглянути наші пропозиції.\n\n"
        ),
        reply_markup=main_menu,
    )
    await callback.answer()
  # Стартове повідомлення та головне меню
main_menu_buttons = [
    [InlineKeyboardButton("📦Каталог парфум", callback_data="catalog"), InlineKeyboardButton("🔥Акції та бонуси", callback_data="promotions")],
    [InlineKeyboardButton("📉Знижка дня", callback_data="daily_discount")],
    [InlineKeyboardButton("ℹ️Як замовити?", callback_data="how_to_order"), InlineKeyboardButton("💬Відгуки", callback_data="reviews")],
    [InlineKeyboardButton("✒️Зв'язатися з нами", url="https://t.me/Dimanicer"), InlineKeyboardButton("🛒 Кошик", callback_data="show_cart")]
]
main_menu = InlineKeyboardMarkup(inline_keyboard=main_menu_buttons)

# === Каталог парфумів ===
catalog_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton("🌸Жіночі", callback_data="cat_women"), InlineKeyboardButton("🥥🍓Унісекс", callback_data="cat_unisex")],
    [InlineKeyboardButton("💣Топ продаж", callback_data="cat_top")],
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

@dp.message_handler(lambda message: message.text == "Знижка дня")
async def daily_discount_text_handler(message: types.Message):
    global daily_discount, last_discount_update
    if daily_discount == {} or last_discount_update != datetime.now().date():
        generate_daily_discount()
    p = daily_discount
    discounted_price = int(p['price'] * 0.85)
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
    await message.answer_photo(photo=p['photo'], caption=caption, reply_markup=buttons)

@dp.callback_query_handler(lambda c: c.data == "daily_discount")
async def daily_discount_callback_handler(callback: types.CallbackQuery):
    global daily_discount, last_discount_update
    if daily_discount == {} or last_discount_update != datetime.now().date():
        generate_daily_discount()
    p = daily_discount
    discounted_price = int(p['price'] * 0.85)
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
    await callback.message.answer_photo(photo=p['photo'], caption=caption, reply_markup=buttons)
    await callback.answer()
@dp.callback_query_handler(lambda c: c.data.startswith("discount_"))
async def add_discount_to_cart(callback: types.CallbackQuery):
    name = callback.data.replace("discount_", "")
    user_id = callback.from_user.id
    all_perfumes = sum(perfume_catalog.values(), [])
    perfume = next((p for p in all_perfumes if p["name"] == name), None)
    if not perfume:
        await callback.answer("Помилка: товар не знайдено.")
        return
    discounted_price = int(perfume["price"] * 0.85)
    user_carts.setdefault(user_id, []).append({"name": name + " (зі знижкою)", "price": discounted_price})
    await callback.answer("✅ Додано до кошика зі знижкою!")
# === Відгуки з промокодом ===
used_promo_users = set()
PROMO_CODES = ["PROMO10", "DISCOUNT15", "SALE20"]

class ReviewState(StatesGroup):
    waiting_text = State()

@dp.callback_query_handler(lambda c: c.data == "reviews")
async def ask_for_review(callback: types.CallbackQuery):
    await bot.send_message(callback.from_user.id, "✏️ Напишіть свій відгук нижче та отримай промо на наступне замовлення!:")
    await ReviewState.waiting_text.set()
    await callback.answer()

@dp.message_handler(state=ReviewState.waiting_text)
async def receive_review(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in used_promo_users:
        await message.answer("Дякуємо за відгук! Ви вже отримали промокод.")
    else:
        if PROMO_CODES:
            promo = PROMO_CODES.pop()
        else:
            promo = "PROMO10"
        used_promo_users.add(user_id)
        await message.answer(f"🎁 Дякуємо за відгук! Ваш промокод: *{promo}*")
    await state.finish()


# Блок: Акції та бонуси
# Функція застосування знижок у кошику
def apply_discounts(cart, user_id):
    total = sum(item['price'] for item in cart)
    discount = 0
    details = []

    # Акція 1: 3-й парфум зі знижкою 50% на найменший за ціною третій товар
    if len(cart) >= 3:
        sorted_cart = sorted(cart, key=lambda x: x['price'])
        # Знижка на кожен 3-й товар
        count_3rd = len(cart) // 3
        discount_3rd = sum(sorted_cart[i * 3 + 2]['price'] * 0.5 for i in range(count_3rd))
        discount += discount_3rd
        if discount_3rd > 0:
            details.append(f"Знижка 50% на {count_3rd} третій парфум: -{int(discount_3rd)} грн")

    # Акція 2: Безкоштовна доставка від 600 грн
    # (припускаємо, що доставка додається пізніше, тут лише перевірка)
    free_delivery_min_sum = 600

    # Акція 3: 1+1 зі знижкою 30% на другий товар (парфуми у парі)
    # Сортуємо по імені, застосовуємо для пар однакових парфумів
    from collections import Counter
    counter = Counter(item['name'] for item in cart)
    for name, count in counter.items():
        pairs = count // 2
        if pairs > 0:
            # Знижка 30% на другий товар у кожній парі
            price_of_item = next(item['price'] for item in cart if item['name'] == name)
            discount_1plus1 = pairs * price_of_item * 0.3
            discount += discount_1plus1
            details.append(f"Знижка 30% на другий парфум '{name}' (в {pairs} парах): -{int(discount_1plus1)} грн")

    # Акція 4: Пакетна пропозиція 4 парфуми за 680 грн (рівно 4 одиниці)
    if len(cart) == 4:
        price_sum_4 = sum(item['price'] for item in cart)
        if price_sum_4 > 680:
            discount_4pack = price_sum_4 - 680
            discount += discount_4pack
            details.append(f"Пакетна ціна 4 парфуми за 680 грн: -{int(discount_4pack)} грн")

    # Акція 5: Знижка 20% при замовленні від 5 одиниць на кожен наступний товар (крім "Знижка дня")
    if len(cart) >= 5:
        # Застосовуємо 20% знижку на товари з 6-го і далі
        sorted_cart = sorted(cart, key=lambda x: x['price'])
        extra_items = len(cart) - 5
        if extra_items > 0:
            discount_20 = sum(sorted_cart[5:][i]['price'] * 0.2 for i in range(extra_items))
            discount += discount_20
            details.append(f"Знижка 20% на {extra_items} товари після 5-го: -{int(discount_20)} грн")

    # Акція 6: Безкоштовна доставка на перше замовлення від 2 шт (текстова логіка)
    # Тут додаткові перевірки можна додати на етапі оформлення замовлення

    return int(discount), details


@dp.callback_query_handler(lambda c: c.data == "show_cart")
async def show_cart_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await callback.message.answer("🛒 Ваш кошик порожній.", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton("🔙 Повернення", callback_data="main_menu")]]))
        return

    total = sum(item['price'] for item in cart)
    discount, discount_details = apply_discounts(cart, user_id)
    final_price = total - discount

    counted = {}
    for item in cart:
        if item['name'] not in counted:
            counted[item['name']] = {'count': 1, 'price': item['price']}
        else:
            counted[item['name']]['count'] += 1
            counted[item['name']]['price'] += item['price']

    text = "*Ваш кошик:*\n"
    i = 1
    for name, data in counted.items():
        unit_price = round(data['price'] / data['count'])
        text += f"{i}. {name} — {data['count']} шт. x {unit_price} грн = {data['price']} грн\n"
        i += 1

    text += f"\n💵 Сума без знижок: {total} грн\n"
    if discount > 0:
        text += "🎁 Знижки:\n"
        for d in discount_details:
            text += f" - {d}\n"
        text += f"✅ До сплати: {final_price} грн"
    else:
        text += f"✅ До сплати: {final_price} грн"

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🧾 Оформити замовлення", callback_data="checkout"),
        InlineKeyboardButton("🧹 Очистити кошик", callback_data="clear_cart"),
        InlineKeyboardButton("🔙 Повернення", callback_data="main_menu")
    )
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


# Оновлення тексту акцій
@dp.callback_query_handler(lambda c: c.data == "promotions")
async def promotions_callback(callback_or_message):
    promo_text = (
        "🎉 *Наявні акції:*\n"
        "1️⃣ *3-й парфум зі знижкою -50%*\n"
        "Купіть 2 будь-які парфуми — третій отримаєте зі знижкою 50%\n\n"
        "2️⃣ *Безкоштовна доставка від 600 грн*\n"
        "Оформіть замовлення на суму від 600 грн (без доставки) — ми доставимо безкоштовно!\n\n"
        "3️⃣ *1+1 зі знижкою 30% на другий товар*\n"
        "Купуйте один парфум, другий отримаєте зі знижкою 30%\n\n"
        "4️⃣ *Пакетна пропозиція: 4 парфуми за 680 грн*\n"
        "Акція діє при замовленні рівно 4 одиниць.\n\n"
        "5️⃣ *Знижка 20% від 5 одиниць*\n"
        "При замовленні від 5 одиниць — знижка 20% на кожен наступний товар.\n\n"
        "6️⃣ *Безкоштовна доставка на перше замовлення від 2 шт*\n"
        "Акція не сумується з іншими знижками.\n\n"
        "7️⃣ *Розіграш серед нових покупців*\n"
        "Приймайте участь та вигравайте призи!\n"
    )

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📄 Умови 3-й парфум", callback_data="promo_cond_1"),
        InlineKeyboardButton("📦 Перейти до каталогу", callback_data="catalog"),
        InlineKeyboardButton("📄 Умови безкоштовної доставки", callback_data="promo_cond_2"),
        InlineKeyboardButton("📦 Перейти до каталогу", callback_data="catalog"),
        InlineKeyboardButton("📄 Умови 1+1 зі знижкою", callback_data="promo_cond_3"),
        InlineKeyboardButton("📦 Перейти до каталогу", callback_data="catalog"),
        InlineKeyboardButton("📄 Умови пакетної пропозиції", callback_data="promo_cond_4"),
        InlineKeyboardButton("📦 Перейти до каталогу", callback_data="catalog"),
        InlineKeyboardButton("📄 Умови знижки від 5 одиниць", callback_data="promo_cond_5"),
        InlineKeyboardButton("📦 Перейти до каталогу", callback_data="catalog"),
        InlineKeyboardButton("📄 Умови безкоштовної доставки на перше замовлення", callback_data="promo_cond_6"),
        InlineKeyboardButton("📦 Перейти до каталогу", callback_data="catalog"),
        InlineKeyboardButton("🔙 Повернення", callback_data="main_menu")
    )

    if isinstance(callback_or_message, types.CallbackQuery):
        await callback_or_message.message.answer(promo_text, reply_markup=keyboard)
        await callback_or_message.answer()
    else:
        await callback_or_message.answer(promo_text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith("promo_cond_"))
async def promo_conditions(call: types.CallbackQuery):
    conditions = {
        "promo_cond_1": "🎉 *3-й парфум зі знижкою -50%*\nКупіть будь-які 2 парфуми та отримайте третій зі знижкою 50%.\nЗнижка застосовується до найменшого за ціною товару. Доставка не входить в облік.",
        "promo_cond_2": "🚚 *Безкоштовна доставка від 600 грн*\nЗагальна сума без урахування доставки має перевищувати 600 грн.",
        "promo_cond_3": "🛍 *1+1 зі знижкою 30%*\nКупуйте один парфум, другий отримаєте зі знижкою 30%.",
        "promo_cond_4": "🎁 *Пакетна пропозиція: 4 парфуми за 680 грн*\nАкція діє при замовленні рівно 4 одиниць.",
        "promo_cond_5": "🔟 *Знижка 20% від 5 одиниць*\nПри замовленні від 5 одиниць — знижка 20% на кожен наступний товар.",
        "promo_cond_6": "🎉 *Безкоштовна доставка на перше замовлення від 2 шт*\nАкція не сумується з іншими знижками."
    }
    await call.message.answer(conditions[call.data])
    await call.answer()

# Переглянути кошик
from aiogram.utils.markdown import escape_md

user_carts = {}

async def update_cart_message(message: types.Message, user_id: int):
    try:
        await show_cart(message)
    except Exception:
        await message.answer("Помилка оновлення кошика.")

@dp.callback_query_handler(lambda c: c.data.startswith("add_"))
async def add_to_cart_callback(callback: types.CallbackQuery):
    perfume_name = callback.data[4:]
    user_id = callback.from_user.id

    if user_id not in user_carts:
        user_carts[user_id] = []

    cart = user_carts[user_id]

    for item in cart:
        if item['name'] == perfume_name:
            item['quantity'] += 1
            break
    else:
        cart.append({"name": perfume_name, "price": 200, "quantity": 1})

    await callback.answer("✅ Товар додано в кошик")
    await update_cart_message(callback.message, user_id)

async def show_cart(message: types.Message):
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await message.edit_text("🛒 Ваш кошик порожній.")
        return

    text = "🛒 *Ваш кошик:*\n"
    keyboard = InlineKeyboardMarkup(row_width=3)

    for i, item in enumerate(cart):
        text += f"\n{i+1}. *{escape_md(item['name'].capitalize())}* — {item['price']} грн × {item['quantity']}"
        keyboard.row(
            InlineKeyboardButton("➕", callback_data=f"inc_{i}"),
            InlineKeyboardButton("➖", callback_data=f"dec_{i}"),
            InlineKeyboardButton("❌", callback_data=f"del_{i}")
        )
    total = sum(item['price'] * item['quantity'] for item in cart)
    text += f"\n*Загалом:* {total} грн"

    keyboard.row(
        InlineKeyboardButton("🧾 Оформити замовлення", callback_data="checkout"),
        InlineKeyboardButton("🔙 Повернутися в каталог", callback_data="catalog")
    )

    try:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="MarkdownV2")
    except:
        await message.answer(text, reply_markup=keyboard, parse_mode="MarkdownV2")

@dp.callback_query_handler(lambda c: c.data.startswith("inc_"))
async def increment_quantity(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])
    idx = int(callback.data[4:])
    if 0 <= idx < len(cart):
        cart[idx]['quantity'] += 1
        await callback.answer("➕ Кількість збільшена")
    else:
        await callback.answer("❗ Невірний товар", show_alert=True)

    await update_cart_message(callback.message, user_id)

@dp.callback_query_handler(lambda c: c.data.startswith("dec_"))
async def decrement_quantity(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])
    idx = int(callback.data[4:])
    if 0 <= idx < len(cart):
        if cart[idx]['quantity'] > 1:
            cart[idx]['quantity'] -= 1
            await callback.answer("➖ Кількість зменшена")
        else:
            cart.pop(idx)
            await callback.answer("❌ Товар видалено з кошика")
    else:
        await callback.answer("❗ Невірний товар", show_alert=True)

    await update_cart_message(callback.message, user_id)

@dp.callback_query_handler(lambda c: c.data.startswith("del_"))
async def delete_item(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])
    idx = int(callback.data[4:])
    if 0 <= idx < len(cart):
        removed = cart.pop(idx)
        await callback.answer(f"❌ Видалено: {removed['name'].capitalize()}")
    else:
        await callback.answer("❗ Невірний товар", show_alert=True)

    await update_cart_message(callback.message, user_id)

# Обробник кнопки оформлення замовлення
@dp.callback_query_handler(lambda c: c.data == "checkout")
async def checkout_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await callback.answer("🛒 Ваш кошик порожній.", show_alert=True)
        return
    await callback.answer()
    await OrderStates.name.set()
    await callback.message.answer(
        "📝 Починаємо оформлення замовлення.\nВведіть ваше ПІБ:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("🔙 Повернення", callback_data="back")]
        ])
    )
@dp.callback_query_handler(lambda c: c.data == "back")
async def back_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()  # або повернутися на потрібний стан, якщо потрібно
    # Наприклад, показати головне меню або каталог
    await callback.message.answer("🔙 Повернення.")
    await callback.answer()

# === Оформлення замовлення ===


@dp.message_handler(state=OrderStates.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📞Введіть ваш *номер телефону*:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("🔙 Повернення", callback_data="back")]]))
    await OrderStates.phone.set()

@dp.message_handler(state=OrderStates.phone)
async def get_phone(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or len(message.text) != 10:
        await message.answer("❗ Номер телефону має містити 10 цифр без +38. Наприклад: 0931234567")
        return
    await state.update_data(phone=message.text)
    await message.answer("🏙Введіть *місто доставки*:")
    await OrderStates.next()



@dp.message_handler(state=OrderStates.city)
async def get_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(OrderStates.delivery_type)
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("На відділення", callback_data="delivery_post"),
        InlineKeyboardButton("Кур'єром на адресу", callback_data="delivery_address")
    )
    await message.answer("Оберіть *тип доставки*:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "back", state=OrderStates.phone)
async def back_to_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введіть ваше *ПІБ* для оформлення замовлення:")
    await OrderStates.name.set()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back", state=OrderStates.city)
async def back_to_phone(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введіть ваш номер телефону:")
    await OrderStates.phone.set()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back", state=OrderStates.delivery_type)
async def back_to_city(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введіть ваше місто:")
    await OrderStates.city.set()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data in ["delivery_post", "delivery_address"], state=OrderStates.delivery_type)
async def get_delivery_type(callback: types.CallbackQuery, state: FSMContext):
    delivery_type = callback.data
    await state.update_data(delivery_type=delivery_type)
    if delivery_type == "delivery_post":
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🚚Нова Пошта", callback_data="nova_post"),
            InlineKeyboardButton("🚛Укрпошта", callback_data="ukr_post")
        )
        await callback.message.answer("Оберіть службу доставки:", reply_markup=keyboard)
        await OrderStates.post_service.set()  # Переходимо у новий стан
    else:
        await callback.message.answer("🏡 Внесіть *повну адресу доставки* (вулиця, номер будинку, квартира):")
        await OrderStates.address_or_post.set()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data in ["nova_post", "ukr_post"], state=OrderStates.post_service)
async def get_post_service(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(post_service=callback.data)
    await callback.message.answer("📮 Введіть *номер відділення або поштомату* (тільки цифри):")
    await OrderStates.address_or_post.set()
    await callback.answer()


@dp.message_handler(state=OrderStates.address_or_post)
async def get_address_or_post(message: types.Message, state: FSMContext):
    data = await state.get_data()
    delivery_type = data['delivery_type']

    if delivery_type == "delivery_post" and not message.text.isdigit():
        await message.answer("❗ Введіть лише номер відділення цифрами.")
        return

    if delivery_type == "delivery_post":
        post_service = data.get('post_service', '-')
        post_service_full = "Нова Пошта" if post_service == "nova_post" else "Укрпошта"
        address_or_post = f"{post_service_full} №{message.text}"
    else:
        address_or_post = message.text

    await state.update_data(address_or_post=address_or_post)


  
    # Формування та відображення замовлення
    data = await state.get_data()
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
    cart = apply_third_item_discount(cart)

    text_items = ""
    total = 0
    for i, item in enumerate(cart, 1):
        text_items += f"{i}. {escape_md(item['name'])} — {item['price']} грн\n"
        total += item['price']

    discount = user_discounts.get(user_id, 0)
    final = total - discount

    order_summary = (
        f"📦 *Перевірте замовлення перед підтвердженням:*\n"
        f"👤 *ПІБ:* {escape_md(data['name'])}\n"
        f"📞 *Телефон:* {escape_md(data['phone'])}\n"
        f"🏙 *Місто:* {escape_md(data['city'])}\n"
        f"📍 *Адреса / Відділення:* {escape_md(data['address_or_post'])}\n"
        f"🛍 *Товари в кошику:*\n{text_items}"
        f"💵 *Сума без знижок:* {total} грн\n"
        f"🎁 *Знижка:* {discount} грн\n"
        f"✅ *До сплати:* {final} грн"
    )
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
        delivery_type = data.get('post_service', 'Адреса') if data['delivery_type'] == 'delivery_post' else 'Адреса'
        address = data.get('address_or_post', '-')
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
            total_sum,
            discount,
            user_id,
            ""
        ])

        await callback.message.answer("🎉 Замовлення підтверджено! Очікуйте на повідомлення з номером ТТН після відправки.")
        user_carts[user_id] = []
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
            "🌺 У нас ви знайдете брендові жіночі, чоловічі та унісекс парфуми — обрані з любов'ю.\n\n"
            "💸 Ми пропонуємо найкращі послуги та щедрі знижки для нових і постійних клієнтів.\n\n"
            "🎁 Усі охочі можуть скористатися акціями та отримати приємні подарунки.\n\n"
            "🚚 Відправка Новою Поштою/Укрпоштою. Доставка - за наш рахунок при великому замовленні.\n\n"
            "👇 Оберіть розділ нижче, щоб почати замовлення або переглянути наші пропозиції.\n\n"
        ),
        reply_markup=main_menu
    )

@dp.message_handler(state=None)
async def auto_start_from_any_message(message: types.Message):
    await bot.send_photo(
        chat_id=message.chat.id,
        photo="https://fleurparfum.net.ua/images/blog/shleifovie-duhi-woman.jpg.pagespeed.ce.3PKNQ9Vn2Z.jpg",
        caption=(
           "🧴 *Ласкаво просимо до нашого ароматного світу!*\n\n"
            "🌺 У нас ви знайдете брендові жіночі, чоловічі та унісекс парфуми — обрані з любов'ю.\n\n"
            "💸 Ми пропонуємо найкращі послуги та щедрі знижки для нових і постійних клієнтів.\n\n"
            "🎁 Усі охочі можуть скористатися акціями та отримати приємні подарунки.\n\n"
            "🚚 Відправка Новою Поштою/Укрпоштою. Доставка - за наш рахунок при великому замовленні.\n\n"
            "👇 Оберіть розділ нижче, щоб почати замовлення або переглянути наші пропозиції.\n\n"
        ),
        reply_markup=main_menu
    )

@dp.message_handler(commands=["track_ttns"])
async def track_pending_orders(message: types.Message):
    all_data = sheet.get_all_values()
    for i, row in enumerate(all_data[1:], start=2):  # пропускаємо заголовок
        try:
            chat_id = row[10].strip() if len(row) > 10 else ""
            ttn = row[11].strip() if len(row) > 11 else ""
            status = row[12].strip() if len(row) > 12 else ""

            if chat_id.isdigit() and ttn and not status:
                await bot.send_message(int(chat_id), f"📦 Ваше замовлення надіслано!Номер накладної: *{ttn}*")
                logging.info(f"Оновлюю рядок {i}, колонка 13, ставлю '✅ надіслано'")
                sheet.update(f'M{i}', "✅ надіслано")
                await asyncio.sleep(1)

        except Exception as e:
            logging.error(f"❌ Помилка в рядку {i}: {e}")

sent_ttns = set()

async def check_new_ttns():
    while True:
        try:
            all_rows = sheet.get_all_values()
            header = all_rows[0]
            ttn_index = header.index("Номер ТТН")
            chat_id_index = header.index("Chat ID")

            for row in all_rows[1:]:
                if len(row) > max(ttn_index, chat_id_index):
                    ttn = row[ttn_index].strip()
                    chat_id = row[chat_id_index].strip()
                    if ttn and chat_id and ttn not in sent_ttns:
                        await bot.send_message(int(chat_id), f"📦 Ваше замовлення відправлено! Ось номер ТТН: *{ttn}*")
                        sent_ttns.add(ttn)

        except Exception as e:
            logging.error(f"Помилка при перевірці ТТН: {e}")

        await asyncio.sleep(30)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(check_new_ttns())
    executor.start_polling(dp, skip_updates=True)


# (при необхідності умовні блоки promo_cond можна додати аналогічно)

# ======================= Приклади інтеграції при оформленні =======================
# cart=user_carts[user_id]
# cart_pr=apply_all_promotions(cart)
# total = sum(i['price']*i['quantity'] for i in cart_pr)
# qty = sum(i['quantity'] for i in cart_pr)
# promo_applied = cart_pr!=cart
# free = is_free_delivery(total, user_data[user_id].get('order_count',0), qty, promo_applied)

# Решта вашого коду без змін: обробники /start, каталог, show_cart, checkout, save to sheet, etc.

if __name__=='__main__':
    loop=asyncio.get_event_loop()
    loop.create_task(asyncio.sleep(0))
    executor.start_polling(dp, skip_updates=True)
