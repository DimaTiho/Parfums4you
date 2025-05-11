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

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Telegram токен
BOT_TOKEN = '7511346484:AAEm89gjBctt55ge8yEqrfHrxlJ-yS4d56U'

# Google Sheets авторизація
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Parfums").sheet1

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
user_carts = {}
user_discounts = {}
user_data = {}

# Стартове повідомлення та головне меню
main_menu_buttons = [
    [InlineKeyboardButton("Каталог парфум", callback_data="catalog")],
    [InlineKeyboardButton("Акції та бонуси", callback_data="promotions")],
    [InlineKeyboardButton("Знижка дня", callback_data="daily_discount")],
    [InlineKeyboardButton("Як замовити?", callback_data="how_to_order")],
    [InlineKeyboardButton("Відгуки", callback_data="reviews")],
    [InlineKeyboardButton("Зв'язатися з менеджером", url="https://t.me/yourmanager")]
]
main_menu = InlineKeyboardMarkup(inline_keyboard=main_menu_buttons)

@dp.message_handler(lambda message: message.text == "Як замовити" or message.text.lower() == "/how_to_order")
async def how_to_order(message: types.Message):
    instructions = (
        "🛍 *Як зробити замовлення:*\n\n"
        "1️⃣ Відкрийте *Каталог* і оберіть парфуми\n"
        "2️⃣ Натисніть *Додати в кошик*\n"
        "3️⃣ Перейдіть у *Кошик* та натисніть *Оформити замовлення*\n"
        "4️⃣ Введіть свої дані (ім’я, телефон, місто, доставка)\n"
        "5️⃣ Підтвердіть замовлення — і ми все надішлемо найближчим часом!\n\n"
        "🧾 Ви отримаєте повідомлення з номером ТТН після відправки."
    )
    await message.answer(instructions)

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    await message.answer(
        "Привіт, я твій чат-бот, щоб мене запустити натисни /start",
    )
    await message.answer(
        "🧴 *Ласкаво просимо до нашого ароматного світу!*\n\n"
        "🌺 У нашому магазині ви знайдете брендові жіночі, чоловічі та унісекс парфуми — обрані з любов'ю.\n"
        "💸 Ми пропонуємо найкращі ціни та щедрі знижки для нових і постійних клієнтів.\n"
        "🎁 Усі покупці можуть скористатися акціями та отримати приємні подарунки.\n"
        "🚚 Доставка по всій Україні. Безкоштовна — при замовленні від 500 грн.\n\n"
        "👇 Оберіть розділ нижче, щоб почати замовлення або переглянути наші пропозиції.",
        reply_markup=main_menu
    )

# === Каталог парфумів ===
catalog_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton("Жіночі", callback_data="cat_women"), InlineKeyboardButton("Унісекс", callback_data="cat_unisex")],
    [InlineKeyboardButton("Топ продаж", callback_data="cat_top")],
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
            [InlineKeyboardButton("➕ Додати до кошика", callback_data=f"add_{p['name']}")],
            [InlineKeyboardButton("🔙 Назад до каталогу", callback_data="catalog"), InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]
        ])
        await bot.send_photo(callback.from_user.id, p['photo'], caption=f"*{p['name']}*\n💸 {p['price']} грн", reply_markup=buttons)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "catalog")
async def show_catalog(callback: types.CallbackQuery):
    await callback.message.edit_text("Оберіть категорію парфумів:", reply_markup=catalog_menu)

@dp.callback_query_handler(lambda c: c.data == "main_menu")
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
        "👇 Оберіть розділ нижче, щоб почати замовлення або переглянути наші пропозиції.",
        reply_markup=main_menu
    )
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
    discounted_price = int(p['price'] * 0.5)
    caption = f"*Знижка дня!*"

Сьогодні у нас акція на:
*{p['name']}*
 "💸 Замість {p['price']} грн — лише {discounted_price} грн!"

"Встигніть скористатися пропозицією!"
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

@dp.message_handler(content_types=types.ContentTypes.ANY)
async def handle_reviews(message: types.Message):
    if message.text and message.text.startswith("/"):
        return  # пропустити команди

    user_id = message.from_user.id
    if user_id in used_promo_users:
        await message.reply("Дякуємо за відгук! Ви вже отримали промокод.")
        return


    # Відповідь з промокодом
    promo = PROMO_CODES.pop() if PROMO_CODES else "THANKYOU5"
    used_promo_users.add(user_id)
    await message.reply(f"Дякуємо за відгук! 🎁 Ось ваш персональний промокод: *{promo}*\nВикористовуйте його при наступному замовленні.")

# Блок: Акції та бонуси
@dp.message_handler(lambda message: message.text == "Акції та бонуси")
async def promotions_handler(message: types.Message):
    promo_text = "🎉 *Наявні акції:*"

"1️⃣ *3-й парфум у подарунок*"
"Купіть 2 будь-які парфуми — третій отримаєте безкоштовно"

"2️⃣ *Безкоштовна доставка від 500 грн*
"Оформіть замовлення на суму від 500 грн (без доставки) — ми доставимо безкоштовно!"

"3️⃣ *Знижка для подруг — 10% кожній!*"
"Запросіть подругу — обидві отримаєте знижку 10%."

"4️⃣ *Набір зі знижкою -15%*"
"При покупці 3+ парфумів — знижка 15% на кожен."

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📄 Умови 3-й парфум", callback_data="promo_cond_1"),
        InlineKeyboardButton("📦 Перейти до каталогу", callback_data="catalog"),
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
        "promo_cond_1": "🎉 *3-й парфум у подарунок*
Купіть 2 будь-які парфуми — третій отримаєте безкоштовно.
(Доставка не входить в облік вартості подарунка)",
        "promo_cond_2": "🚚 *Безкоштовна доставка від 500 грн*
Загальна сума без урахування доставки має перевищувати 500 грн.",
        "promo_cond_3": "👭 *Знижка для подруг — 10% кожній!*
Надішліть посилання подрузі. Обидві отримаєте знижку після замовлення.",
        "promo_cond_4": "🎁 *Набір зі знижкою -15%*
При купівлі 3 або більше парфумів — знижка 15% на кожен."
    }
    await call.message.answer(conditions[call.data])
    await call.answer()

# === Додавання до кошика ===
@dp.callback_query_handler(lambda c: c.data.startswith("add_"))
async def add_to_cart(callback: types.CallbackQuery):
    perfume_name = callback.data[4:]
    user_id = callback.from_user.id
    if user_id not in user_carts:
        user_carts[user_id] = []
    user_carts[user_id].append(perfume_name)
    await callback.answer("Додано до кошика!")

@dp.message_handler(commands=["cart"])
async def view_cart(message: types.Message):
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await message.answer("Ваш кошик порожній.")
        return
    text = "🛒 *Ваш кошик:*\n" + "\n".join(f"• {item}" for item in cart)
    await message.answer(text)

@dp.message_handler(commands=["clearcart"])
async def clear_cart(message: types.Message):
    user_id = message.from_user.id
    user_carts[user_id] = []
    await message.answer("Кошик очищено.")

# === Оформлення замовлення ===
@dp.message_handler(commands=["order"])
async def start_order(message: types.Message):
    await message.answer("Введіть ваше *ім’я*:")
    await OrderStates.name.set()

@dp.message_handler(state=OrderStates.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введіть ваш *номер телефону*:")
    await OrderStates.phone.set()

@dp.message_handler(state=OrderStates.phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("Введіть ваше *місто*:")
    await OrderStates.city.set()

@dp.message_handler(state=OrderStates.city)
async def get_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📦 На відділення", callback_data="delivery_branch")],
        [InlineKeyboardButton("🚚 Адресна доставка", callback_data="delivery_address")]
    ])
    await message.answer("Оберіть тип доставки:", reply_markup=buttons)
    await OrderStates.delivery_type.set()

@dp.callback_query_handler(state=OrderStates.delivery_type)
async def get_delivery_type(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "delivery_branch":
        await state.update_data(delivery_type="Відділення")
        await bot.send_message(callback.from_user.id, "Введіть номер відділення:")
    else:
        await state.update_data(delivery_type="Адресна доставка")
        await bot.send_message(callback.from_user.id, "Введіть адресу доставки:")
    await OrderStates.address_or_post.set()
    await callback.answer()

@dp.message_handler(state=OrderStates.address_or_post)
async def get_address(message: types.Message, state: FSMContext):
    await state.update_data(address_or_post=message.text)
    data = await state.get_data()
    summary = f"*Перевірте ваші дані:*\n\n"
    summary += f"👤 Ім’я: {data['name']}\n📱 Телефон: {data['phone']}\n🏙 Місто: {data['city']}\n"
    summary += f"🚚 Доставка: {data['delivery_type']}\n📦 Деталі: {data['address_or_post']}\n"
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅ Підтвердити", callback_data="confirm_order")],
        [InlineKeyboardButton("❌ Скасувати", callback_data="cancel_order")]
    ])
    await message.answer(summary, reply_markup=buttons)
    await OrderStates.confirmation.set()
# === Після підтвердження — перевірка ТТН ===
@dp.message_handler(commands=["track_ttns"])
async def track_pending_orders(message: types.Message):
    all_data = sheet.get_all_values()
    for i, row in enumerate(all_data[1:], start=2):  # пропускаємо заголовок, індексація з 2
        if len(row) >= 10 and not row[9].strip():  # якщо ТТН ще не заповнено
            try:
                chat_id = int(row[1])
                await asyncio.sleep(2)  # невелика затримка між запитами
                current_row = sheet.row_values(i)
                if len(current_row) >= 10 and current_row[9].strip():
                    ttn = current_row[9].strip()
                    await bot.send_message(chat_id, f"📦 Ваше замовлення надіслано!\nНомер накладної: *{ttn}*")
            except Exception as e:
                logging.error(f"Помилка при надсиланні ТТН: {e}")

@dp.callback_query_handler(lambda c: c.data == "confirm_order", state=OrderStates.confirmation)
async def confirm_order(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])
    total = len(cart) * 200
    if total > 500:
        delivery = 0
    else:
        delivery = 80
    final_total = total + delivery
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([now, user_id, data['name'], data['phone'], data['city'], data['delivery_type'], data['address_or_post'], ", ".join(cart), final_total])
    await bot.send_message(user_id, f"✅ Замовлення підтверджено! Загальна сума: {final_total} грн. Дякуємо за покупку!")
    await state.finish()
@dp.message_handler(commands=["cart"])
async def view_cart(message: types.Message):
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await message.answer("🛒 Ваш кошик порожній.")
        return

    text = "🛍 *Ваш кошик:*\n\n"
    for i, item in enumerate(cart, 1):
        text += f"{i}. {item}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🧾 Оформити замовлення", callback_data="checkout")],
        [InlineKeyboardButton("🗑 Очистити кошик", callback_data="clear_cart")]
    ])
    await message.answer(text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_carts[user_id] = []
    await callback.answer("Кошик очищено!")
    await callback.message.edit_text("🛒 Ваш кошик очищено.")

@dp.callback_query_handler(lambda c: c.data == "checkout")
async def start_checkout(callback: types.CallbackQuery):
    await callback.message.edit_text("✍️ Введіть ваше ім’я:")
    await OrderStates.name.set()

@dp.message_handler(state=OrderStates.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📞 Введіть ваш номер телефону:")
    await OrderStates.phone.set()

@dp.message_handler(state=OrderStates.phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("🏙 Введіть місто доставки:")
    await OrderStates.city.set()

@dp.message_handler(state=OrderStates.city)
async def get_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📦 Відділення", callback_data="delivery_branch"),
        InlineKeyboardButton("🚪 Адресна доставка", callback_data="delivery_address")
    )
    await message.answer("Оберіть тип доставки:", reply_markup=kb)
    await OrderStates.delivery_type.set()

@dp.callback_query_handler(state=OrderStates.delivery_type)
async def get_delivery_type(callback: types.CallbackQuery, state: FSMContext):
    delivery_type = callback.data
    await state.update_data(delivery_type=delivery_type)
    text = "Введіть адресу доставки:" if delivery_type == "delivery_address" else "Введіть номер відділення та службу доставки:"
    await bot.send_message(callback.from_user.id, text)
    await OrderStates.address_or_post.set()

@dp.message_handler(state=OrderStates.address_or_post)
async def get_delivery_info(message: types.Message, state: FSMContext):
    await state.update_data(address_or_post=message.text)
    data = await state.get_data()
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])

    # Зберігаємо в таблицю
    order_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet.append_row([
        str(user_id),
        data['name'],
        data['phone'],
        data['city'],
        "Адресна" if data['delivery_type'] == "delivery_address" else "Відділення",
        data['address_or_post'],
        ', '.join(cart),
        order_time,
        ""
    ])

    # Очистити кошик після замовлення
    user_carts[user_id] = []

    await message.answer("✅ Замовлення прийнято! Очікуйте на повідомлення з номером ТТН.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == "cancel_order", state=OrderStates.confirmation)
async def cancel_order(callback: types.CallbackQuery, state: FSMContext):
    await bot.send_message(callback.from_user.id, "❌ Замовлення скасовано.")
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
