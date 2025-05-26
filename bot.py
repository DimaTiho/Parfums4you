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
from collections import Counter
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
    [InlineKeyboardButton("📦Каталог парфум", callback_data="catalog"), InlineKeyboardButton("🔥Акції та бонуси", callback_data="promotions")],
    [InlineKeyboardButton("📉Знижка дня", callback_data="daily_discount")],
    [InlineKeyboardButton("ℹ️Як замовити?", callback_data="how_to_order")],
    [InlineKeyboardButton("✒️Зв'язатися з менеджером", url="https://t.me/Dimanicer"), InlineKeyboardButton("🛒 Кошик", callback_data="show_cart")]
]
main_menu = InlineKeyboardMarkup(inline_keyboard=main_menu_buttons)

# === Каталог парфумів ===
catalog_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton("💃🏻Жіночі", callback_data="cat_women"), InlineKeyboardButton("👩🏼‍🦰👱🏼Унісекс", callback_data="cat_unisex")],
    [InlineKeyboardButton("‼️Топ продаж", callback_data="cat_top")],
    [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
])

perfume_catalog = {
    "cat_women": [
        {"name": "Chanel Coco Mademoiselle", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1},
        {"name": "Dior J'adore", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1}
    ],
    "cat_unisex": [
        {"name": "Tom Ford Tobacco Vanille", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1},
        {"name": "Byredo Gypsy Water", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.jpg","quantity": 1}
    ],
    "cat_top": [
        {"name": "Creed Aventus", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1},
        {"name": "Maison Francis Kurkdjian Baccarat Rouge", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1}
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
    discounted_price = int(perfume["price"] * 0.75)
    user_carts.setdefault(user_id, []).append({"name": name + " (зі знижкою)", "price": discounted_price})
    await callback.answer("✅ Додано до кошика зі знижкою!")

# Блок: Акції та бонуси
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
        InlineKeyboardButton("📄 Умови безкоштовної доставки", callback_data="promo_cond_2"),
        InlineKeyboardButton("📄 Умови 1+1 зі знижкою", callback_data="promo_cond_3"),
        InlineKeyboardButton("📄 Умови пакетної пропозиції", callback_data="promo_cond_4"),
        InlineKeyboardButton("📄 Умови знижки від 5 одиниць", callback_data="promo_cond_5"),
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

@dp.callback_query_handler(lambda c: c.data.startswith("add_"))
async def add_to_cart_callback(callback: types.CallbackQuery):
    perfume_name = callback.data[4:]
    user_id = callback.from_user.id
    if user_id not in user_carts:
        user_carts[user_id] = []
    user_carts[user_id].append({"name": perfume_name, "price": 200})

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("🛒 Переглянути кошик", callback_data="show_cart"),
            InlineKeyboardButton("🧾 Оформити замовлення", callback_data="checkout")
        ],
        [
            InlineKeyboardButton("🔙 Повернення", callback_data="catalog"),
            InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")
        ]
    ])
    await callback.message.answer(f"✅ {perfume_name} додано до кошика.", reply_markup=buttons)
    await callback.answer()

user_carts = {}  # Словник користувачів з їхніми кошиками

def calculate_cart(cart, day_discount_percent=0):
     if not cart:
         return {"cart": [], "total": 0}
    # Підрахунок кількості кожного товару
    counts = Counter(item['name'] for item in cart)
    prices = {item['name']: item['price'] 
              for item in cart}

    cart_summary = []
    for name, count in counts.items():
        cart_summary.append({
            'name': name,
            'quantity': count,
            'price': prices[name]
        })

    total_price = sum(item['price'] * item['quantity'] for item in cart_summary)

    # Акції:

    # 1. Знижка на 3-й товар -50% на найменший третій товар
    discount_3rd = 0
    if sum(counts.values()) >= 3:
        all_prices = []
        for item in cart_summary:
            all_prices.extend([item['price']] * item['quantity'])
        all_prices.sort()
        discount_3rd = all_prices[2] * 0.5

    # 2. Пакетна пропозиція: 4 парфуми за 680 грн
    package_discount = 0
    if sum(counts.values()) == 4:
        if total_price > 680:
            package_discount = total_price - 680

    # 3. Знижка 20% від 5 одиниць
    discount_20_percent = 0
    if sum(counts.values()) >= 5:
        discount_20_percent = total_price * 0.2

    # 4. 1+1 зі знижкою 30% на другий товар
    discount_bogo = 0
    for item in cart_summary:
        pairs = item['quantity'] // 2
        discount_bogo += pairs * item['price'] * 0.3

    # 5. Безкоштовна доставка від 600 грн (після знижок)
    max_discount = max(discount_3rd, package_discount, discount_20_percent, discount_bogo)
    price_after_discount = total_price - max_discount
    free_shipping = price_after_discount >= 600

    # 6. Знижка дня (окремо)
    day_discount_amount = price_after_discount * (day_discount_percent / 100)

    # Фінальна сума з урахуванням знижок та знижки дня
    total_discount = max_discount + day_discount_amount
    final_price = total_price - total_discount
@dp.callback_query_handler(lambda c: c.data == "open_cart")
async def open_cart_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])

    if not cart:
        await callback.answer("🛒 Ваш кошик порожній.", show_alert=True)
        await callback.message.edit_text("🛒 Ваш кошик порожній.", reply_markup=None)
        return

    text_items = ""
    total = 0
    keyboard = InlineKeyboardMarkup(row_width=3)

    for i, item in enumerate(cart, 1):
        item_total = item['price'] * item['quantity']
        text_items += f"{i}. {escape_md(item['name'])} — {item['price']} грн × {item['quantity']} = {item_total} грн\n"
        total += item_total

        keyboard.add(
            InlineKeyboardButton(f"➖ {i}", callback_data=f"decrease_{i-1}"),
            InlineKeyboardButton(f"❌ {i}", callback_data=f"remove_{i-1}"),
            InlineKeyboardButton(f"➕ {i}", callback_data=f"increase_{i-1}")
        )

    discount = user_discounts.get(user_id, 0)
    final = total - discount if total >= discount else 0

    text = (
        f"🛒 *Ваш кошик:*\n\n"
        f"{text_items}\n"
        f"💵 *Сума без знижок:* {total} грн\n"
        f"🎁 *Знижка:* {discount} грн\n"
        f"✅ *До сплати:* {final} грн\n\n"
        "Використайте кнопки для зміни кількості або видалення товару."
    )

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()
    # Додаємо поле discount (поки 0) для кожного товару (можна деталізувати, якщо потрібно)
    for item in cart_summary:
        item['discount'] = 0

    return {
        'cart': cart_summary,
        "cart": some_cart_data,
        "total": some_total,
        'total_price': final_price,
        'total_discount': total_discount,
        'free_shipping': free_shipping,
        'day_discount_amount': day_discount_amount
    }

@dp.callback_query_handler(lambda c: c.data == "show_cart")
async def show_cart_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await callback.message.answer(
            "🛒 Ваш кошик порожній.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton("🔙 Повернення", callback_data="main_menu")]]
            )
        )
        return

    result = calculate_cart(cart, day_discount_percent=0)  # Задай day_discount_percent за потребою

    cart_summary = result['cart']
    total_price = result['total_price']
    free_shipping_flag = result['free_shipping']
    day_discount_amount = result['day_discount_amount']
    total_discount = result['total_discount']

    text = "*Ваш кошик:*\n"
    i = 1
    for item in cart_summary:
        unit_price = item['price']
        count = item['quantity']
        line_price = unit_price * count
        text += f"{i}. {item['name']} — {count} шт. x {unit_price} грн = {line_price} грн\n"
        i += 1

    text += f"\n💵 Сума без знижок: {sum(item['price'] * item['quantity'] for item in cart_summary)} грн\n"
    if day_discount_amount > 0:
        text += f"🎉 Знижка дня: {round(day_discount_amount)} грн\n"
    text += f"🎁 Загальна знижка: {round(total_discount)} грн\n"
    text += f"✅ До сплати: {round(total_price)} грн\n"
    if free_shipping_flag:
        text += "🚚 У вас безкоштовна доставка!\n"

    buttons = InlineKeyboardMarkup(row_width=2)
    for item in cart_summary:
        buttons.add(
            InlineKeyboardButton(f"➕ {item['name']}", callback_data=f"increase_{item['name']}"),
            InlineKeyboardButton(f"➖ {item['name']}", callback_data=f"decrease_{item['name']}")
        )
    buttons.add(
        InlineKeyboardButton("🧾 Оформити замовлення", callback_data="checkout"),
        InlineKeyboardButton("🔙 Повернення", callback_data="catalog"),
    )

    await callback.message.answer(text, reply_markup=buttons)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("increase_"))
async def increase_item_quantity(callback: types.CallbackQuery):
    name = callback.data.replace("increase_", "")
    user_id = callback.from_user.id
    cart = user_carts.setdefault(user_id, [])
    for item in cart:
        if item["name"] == name:
            item["quantity"] += 1
            break
    else:
        cart.append({"name": name, "price": 200, "quantity": 1})  # або дізнайся справжню ціну
    await show_cart_callback(callback)
  
@dp.callback_query_handler(lambda c: c.data.startswith("decrease_"))
async def decrease_item_quantity(callback: types.CallbackQuery):
    name = callback.data.replace("decrease_", "")
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])
    for i, item in enumerate(cart):
        if item["name"] == name:
            item["quantity"] -= 1
            if item["quantity"] <= 0:
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
    await callback.message.answer("✍️ Введіть ваше *ПІБ* для оформлення замовлення:")
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
    # Переадресація на функцію show_cart_callback з фейковим callback
    class DummyCallback:
        def __init__(self, user_id, message):
            self.from_user = types.User(id=user_id, is_bot=False, first_name="User")
            self.message = message
            self.data = "show_cart"
    await show_cart_callback(DummyCallback(message.from_user.id, message))

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
async def handle_order_confirmation(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id

    if callback.data == "confirm_order":
        print(f"User {user_id} підтвердив замовлення")  # Логування для перевірки
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")
        name = data.get('name', '-')
        phone = data.get('phone', '-')
        city = data.get('city', '-')
        delivery_type = data.get('post_service', 'Адреса') if data.get('delivery_type') == 'delivery_post' else 'Адреса'
        address = data.get('address_or_post', '-')

        cart_items = user_carts.get(user_id, [])
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

    elif callback.data == "cancel_order":
        print(f"User {user_id} скасував замовлення")  # Логування для перевірки
        await callback.message.answer("❌ Замовлення скасовано.")

    else:
        print(f"User {user_id} надіслав невідомий callback: {callback.data}")

    await state.finish()
    await callback.answer()


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

@dp.message_handler(state=None)
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
        try:
            chat_id = row[10].strip() if len(row) > 10 else ""
            ttn = row[11].strip() if len(row) > 11 else ""
            status = row[12].strip() if len(row) > 12 else ""

            if chat_id.isdigit() and ttn and not status:
                await bot.send_message(int(chat_id), f"📦 Ваше замовлення надіслано!Номер накладної: *{ttn}*")
                sheet.update_cell(i, 13, "Надіслано")
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


