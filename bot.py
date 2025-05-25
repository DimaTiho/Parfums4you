import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.utils.markdown import escape_md
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime

BOT_TOKEN = '7511346484:AAEm89gjBctt55ge8yEqrfHrxlJ-yS4d56U'
GOOGLE_SHEET_NAME = 'Parfums'
CREDENTIALS_FILE = 'credentials.json'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

# --- CONSTANTS ---

PARFUM_PRICE = 200

# Заглушки парфумів (назва + фото URL)
PARFUMS = {
    'Жіночі': [
        {'id': 'w1', 'name': 'Романтична ніч', 'photo': 'https://i.imgur.com/OaY3nI1.jpg'},
        {'id': 'w2', 'name': 'Весняний вітер', 'photo': 'https://i.imgur.com/NzId81A.jpg'},
        {'id': 'w3', 'name': 'Таємничий сад', 'photo': 'https://i.imgur.com/81M6cNs.jpg'},
        {'id': 'w4', 'name': 'Легка хмара', 'photo': 'https://i.imgur.com/XkMnEaH.jpg'},
    ],
    'Унісекс': [
        {'id': 'u1', 'name': 'Світло дня', 'photo': 'https://i.imgur.com/7XIkpLD.jpg'},
        {'id': 'u2', 'name': 'Міський ритм', 'photo': 'https://i.imgur.com/wlnrZY3.jpg'},
        {'id': 'u3', 'name': 'Північна зоря', 'photo': 'https://i.imgur.com/7BhZqRm.jpg'},
        {'id': 'u4', 'name': 'Лісова прохолода', 'photo': 'https://i.imgur.com/GtUMLwP.jpg'},
    ],
    'ТОП ПРОДАЖ': [
        {'id': 't1', 'name': 'Вогняний спалах', 'photo': 'https://i.imgur.com/gERt9dB.jpg'},
        {'id': 't2', 'name': 'Свіжий подих', 'photo': 'https://i.imgur.com/9J3jE9v.jpg'},
        {'id': 't3', 'name': 'Нічна мелодія', 'photo': 'https://i.imgur.com/v4jJLuF.jpg'},
        {'id': 't4', 'name': 'Сонячний промінь', 'photo': 'https://i.imgur.com/Dw1HXpe.jpg'},
    ],
}

# Знижка дня (приклад) - фіксована парфума
DISCOUNT_DAY_ITEM = {
    'id': 'w1',
    'name': 'Романтична ніч',
    'old_price': 200,
    'new_price': 170,
    'photo': 'https://i.imgur.com/OaY3nI1.jpg',
}

# Стан для оформлення замовлення
class OrderStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_city = State()
    waiting_for_delivery_type = State()
    waiting_for_address_or_post_service = State()
    confirmation = State()

# Зберігання кошиків та дискаунтів в пам'яті (пам'ятай, це вразливе для перезапусків!)
user_carts = {}
user_discounts = {}

# --- ФУНКЦІЇ ЛОГІКИ АКЦІЙ ---

def apply_discounts(cart_items):
    """
    Застосувати всі акції, крім "Знижка дня" на окремий парфум.
    Повернути tuple (список оновлених товарів з цінами, сума скидки).
    Логіка акцій (1-6):
    Акція 1: 3-й парфум зі знижкою 50% на найменший третій товар
    Акція 2: Безкоштовна доставка від 600 грн (нараховується пізніше)
    Акція 3: 1+1 зі знижкою 30% на будь-який другий товар (парні зараховуються зі знижкою)
    Акція 4: Пакетна пропозиція 4 парфуми за 680 грн (рівно 4 одиниці)
    Акція 5: Знижка 20% при замовленні від 5 одиниць на кожен наступний товар (крім знижки дня)
    Акція 6: Безкоштовна доставка на перше замовлення від 2 шт (текстова логіка, в кошику не враховується)
    """
    # Вхід: list dict з ключами id, name, price, discount_day (bool)
    # Спочатку не враховуємо товари з discount_day=True (вони не змінюють ціну)

    normal_items = [item for item in cart_items if not item.get('discount_day', False)]
    discount_day_items = [item for item in cart_items if item.get('discount_day', False)]

    total_discount = 0
    updated_items = []

    # Кількість товарів, що не discount_day
    n = len(normal_items)

    # Якщо 4 одиниці, акція 4 - пакетна пропозиція 680 грн
    if n == 4:
        # Ціна за всі 4 = 680 грн
        # Розподіляємо по 170 грн кожен (щоб показати у кошику)
        price_per_item = 680 / 4
        for item in normal_items:
            updated_items.append({**item, 'final_price': price_per_item})
        total_discount += PARFUM_PRICE * 4 - 680
    else:
        # Інакше застосовуємо інші акції послідовно

        # Початково без змін
        for item in normal_items:
            item['final_price'] = PARFUM_PRICE

        # Акція 1: 3-й парфум зі знижкою 50% на найменший третій товар (не на кожен третій!)
        if n >=3:
            third_item = normal_items[2]
            # 50% від 200 = 100 грн знижки
            third_item['final_price'] = PARFUM_PRICE / 2
            total_discount += PARFUM_PRICE / 2

        # Акція 3: 1+1 зі знижкою 30% на будь-який другий товар (парні зараховуються зі знижкою)
        # Застосовується після акції 1
        # Кожен парний (2,4,6...) товар зі знижкою 30%
        for i in range(1, n, 2):
            item = normal_items[i]
            if item['final_price'] == PARFUM_PRICE:  # якщо не змінено раніше (3-й може бути змінений)
                discount_30 = PARFUM_PRICE * 0.3
                item['final_price'] = PARFUM_PRICE - discount_30
                total_discount += discount_30

        # Акція 5: Знижка 20% при замовленні від 5 одиниць на кожен наступний товар (окрім "Знижка дня")
        if n >= 5:
            # Застосувати 20% знижку на товари з 5-го і далі (індекс 4+)
            for i in range(4, n):
                item = normal_items[i]
                # Якщо ціна не знижена нижче (акції не сумуються)
                if item['final_price'] == PARFUM_PRICE:
                    discount_20 = PARFUM_PRICE * 0.2
                    item['final_price'] = PARFUM_PRICE - discount_20
                    total_discount += discount_20

        updated_items.extend(normal_items)

    # Для товарів зі "Знижка дня" ціна фіксована (new_price), без інших знижок
    for item in discount_day_items:
        item['final_price'] = DISCOUNT_DAY_ITEM['new_price']
        updated_items.append(item)

    # Повертаємо всі товари, включно зі знижкою дня, та суму знижки
    return updated_items, total_discount

def calculate_cart_summary(cart_items):
    """
    Обчислити суму, знижку, підсумок по кошику.
    """
    updated_items, total_discount = apply_discounts(cart_items)
    total_price = sum(item['final_price'] for item in updated_items)
    return updated_items, total_discount, total_price

# --- КЛЮЧІ ГОЛОВНОГО МЕНЮ ---

MAIN_MENU_IMAGE = 'https://i.imgur.com/EpS34Zp.jpg'
MAIN_MENU_TEXT = (
    "Ласкаво просимо до нашого магазину парфумів! Оберіть розділ:"
)

def main_menu_kb():
    kb = InlineKeyboardMarkup(row_width=6)
    kb.add(
        InlineKeyboardButton("Каталог парфум.", callback_data="catalog"),
        InlineKeyboardButton("Акції та бонуси", callback_data="promos"),
        InlineKeyboardButton("Знижка дня", callback_data="discount_day"),
        InlineKeyboardButton("Як замовити?", callback_data="how_to_order"),
        InlineKeyboardButton("Зв'язатися з нами", url="https://t.me/your_contact"),  # посилання на контакт
        InlineKeyboardButton("Кошик", callback_data="cart")
    )
    return kb

# --- ОБРОБКА СТАРТОВОГО ПОВІДОМЛЕННЯ ---

@dp.message_handler()
async def any_message_start(message: types.Message):
    # Запуск бота на будь-яке повідомлення
    await send_main_menu(message.chat.id)

async def send_main_menu(chat_id):
    await bot.send_photo(
        chat_id,
        photo=MAIN_MENU_IMAGE,
        caption=MAIN_MENU_TEXT,
        reply_markup=main_menu_kb()
    )

# --- КАТАЛОГ ---

def catalog_menu_kb():
    kb = InlineKeyboardMarkup(row_width=4)
    kb.add(
        InlineKeyboardButton("Жіночі", callback_data="cat_women"),
        InlineKeyboardButton("Унісекс", callback_data="cat_unisex"),
        InlineKeyboardButton("ТОП ПРОДАЖ", callback_data="cat_top"),
        InlineKeyboardButton("⬅ Повернутися назад", callback_data="main_menu")
    )
    return kb

@dp.callback_query_handler(lambda c: c.data == "catalog")
async def show_catalog(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_media(
        media=InputMediaPhoto(
            media=MAIN_MENU_IMAGE,
            caption="Оберіть категорію парфумів:",
        ),
        reply_markup=catalog_menu_kb()
    )

def parfums_kb(category):
    kb = InlineKeyboardMarkup(row_width=2)
    for parfum in PARFUMS[category]:
        kb.insert(InlineKeyboardButton(parfum['name'], callback_data=f"show_{parfum['id']}"))
    kb.add(InlineKeyboardButton("⬅ Повернутися назад", callback_data="catalog"))
    return kb

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("cat_"))
async def show_parfums_category(callback: types.CallbackQuery):
    category_key = callback.data[4:]
    # Перевірка валідності
    category_map = {
        'women': 'Жіночі',
        'unisex': 'Унісекс',
        'top': 'ТОП ПРОДАЖ',
    }
    category = category_map.get(category_key)
    if not category:
        await callback.answer("Невідома категорія.", show_alert=True)
        return
    parfum = PARFUMS[category][0]
    media = InputMediaPhoto(
        media=parfum['photo'],
        caption=f"Категорія: *{category}*\nОберіть парфум:",
        parse_mode='MarkdownV2'
    )
    await callback.answer()
    await callback.message.edit_media(
        media=media,
        reply_markup=parfums_kb(category)
    )
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("show_"))
async def show_parfum_detail(callback: types.CallbackQuery):
    parfum_id = callback.data[5:]
    # Знайти парфум по id в усіх категоріях
    parfum = None
    for cat, parfums in PARFUMS.items():
        for p in parfums:
            if p['id'] == parfum_id:
                parfum = p
                break
        if parfum:
            break
    if not parfum:
        await callback.answer("Парфум не знайдено.", show_alert=True)
        return

    text = (
        f"*{escape_md(parfum['name'], version=2)}*\n"
        f"Ціна: {PARFUM_PRICE} грн\n\n"
        "Натисніть кнопку, щоб додати до кошика."
    )
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Додати в кошик", callback_data=f"add_{parfum['id']}"),
        InlineKeyboardButton("⬅ Назад до категорії", callback_data="catalog")
    )
    await callback.answer()
    await callback.message.edit_media(
        media=InputMediaPhoto(media=parfum['photo'], caption=text, parse_mode='MarkdownV2'),
        reply_markup=kb
    )


# --- КОШИК ---
def get_cart(chat_id):
    return user_carts.setdefault(chat_id, {})

def cart_keyboard(cart):
    kb = InlineKeyboardMarkup(row_width=4)
    for parfum_id, quantity in cart.items():
        # Знайти назву
        parfum_name = None
        for cat_parfums in PARFUMS.values():
            for p in cat_parfums:
                if p['id'] == parfum_id:
                    parfum_name = p['name']
                    break
            if parfum_name:
                break
        kb.insert(
            InlineKeyboardButton(f"{parfum_name} ×{quantity}", callback_data="noop")
        )
    kb.add(
        InlineKeyboardButton("Оформити замовлення", callback_data="order"),
        InlineKeyboardButton("Очистити кошик", callback_data="clear_cart"),
        InlineKeyboardButton("⬅ Повернутися назад", callback_data="main_menu")
    )
    return kb

@dp.callback_query_handler(lambda c: c.data == "cart")
async def show_cart(callback: types.CallbackQuery):
    await callback.answer()
    cart = get_cart(callback.message.chat.id)
    if not cart:
        await callback.message.edit_caption(
            "Ваш кошик порожній.",
            reply_markup=main_menu_kb()
        )
        return

    # Формуємо список товарів з деталями для калькуляції
    cart_items = []
    for parfum_id, qty in cart.items():
        parfum = None
        for cat_parfums in PARFUMS.values():
            for p in cat_parfums:
                if p['id'] == parfum_id:
                    parfum = p
                    break
            if parfum:
                break
        if parfum:
            for _ in range(qty):
                cart_items.append({'id': parfum['id'], 'name': parfum['name']})

    # Додаємо товар зі "Знижкою дня", якщо є в кошику
    for i, item in enumerate(cart_items):
        if item['id'] == DISCOUNT_DAY_ITEM['id']:
            cart_items[i]['discount_day'] = True

    updated_items, total_discount, total_price = calculate_cart_summary(cart_items)

    text_lines = ["Ваш кошик:\n"]
    counts = {}
    prices = {}
    for item in updated_items:
        counts[item['id']] = counts.get(item['id'], 0) + 1
        prices[item['id']] = item['final_price']

    for parfum_id, count in counts.items():
        # Знайти назву
        name = None
        for cat_parfums in PARFUMS.values():
            for p in cat_parfums:
                if p['id'] == parfum_id:
                    name = p['name']
                    break
            if name:
                break
        price_per_unit = prices[parfum_id]
        total_item_price = price_per_unit * count
        text_lines.append(f"{name} ×{count} — {total_item_price:.2f} грн ({price_per_unit:.2f} грн/шт)")

    text_lines.append(f"\nЗагальна знижка: {total_discount:.2f} грн")
    text_lines.append(f"До оплати: {total_price:.2f} грн")
    text_lines.append("\nЩоб оформити замовлення — натисніть кнопку.")

    await callback.message.edit_caption(
        '\n'.join(text_lines),
        reply_markup=cart_keyboard(cart)
    )


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("add_"))
async def add_to_cart(callback: types.CallbackQuery):
    parfum_id = callback.data[4:]
    cart = get_cart(callback.message.chat.id)
    cart[parfum_id] = cart.get(parfum_id, 0) + 1
    await callback.answer("Додано до кошика!")
    await show_cart(callback)


@dp.callback_query_handler(lambda c: c.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    user_carts[callback.message.chat.id] = {}
    await callback.answer("Кошик очищено.")
    await callback.message.edit_caption("Ваш кошик порожній.", reply_markup=main_menu_kb())
wait callback.message.edit_caption("Ваш кошик порожній.", reply_markup=main_menu_kb())

--- ОФОРМЛЕННЯ ЗАМОВЛЕННЯ ---
@dp.callback_query_handler(lambda c: c.data == "order")
async def start_order(callback: types.CallbackQuery):
    cart = get_cart(callback.message.chat.id)
    if not cart:
        await callback.answer("Ваш кошик порожній, додайте товари.")
        return
    await callback.answer()
    await bot.send_message(callback.message.chat.id, "Введіть ваше ім'я:")
    await OrderStates.waiting_for_name.set()

@dp.message_handler(state=OrderStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введіть ваш номер телефону:")
    await OrderStates.waiting_for_phone.set()

@dp.message_handler(state=OrderStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text
    # Проста перевірка формату
    if len(phone) < 7:
        await message.answer("Введіть коректний номер телефону:")
        return
    await state.update_data(phone=phone)
    await message.answer("Введіть ваше місто:")
    await OrderStates.waiting_for_city.set()

@dp.message_handler(state=OrderStates.waiting_for_city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Доставка на адресу", callback_data="delivery_address"),
        InlineKeyboardButton("Доставка у відділення", callback_data="delivery_post_office")
    )
    await message.answer("Оберіть тип доставки:", reply_markup=kb)
    await OrderStates.waiting_for_delivery_type.set()

@dp.callback_query_handler(
    lambda c: c.data in ["delivery_address", "delivery_post_office"],
    state=OrderStates.waiting_for_delivery_type
)
async def process_delivery_type(callback: types.CallbackQuery, state: FSMContext):
    delivery_type = callback.data
    await state.update_data(delivery_type=delivery_type)
    await callback.answer()
    if delivery_type == "delivery_address":
        await bot.send_message(callback.message.chat.id, "Введіть адресу доставки (вулиця, номер будинку):")
        await OrderStates.waiting_for_address_or_post_service.set()
    else:
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("Нова Пошта", callback_data="post_np"),
            InlineKeyboardButton("Укрпошта", callback_data="post_ukr")
        )
        await bot.send_message(callback.message.chat.id, "Оберіть службу доставки:", reply_markup=kb)
        await OrderStates.waiting_for_address_or_post_service.set()

@dp.callback_query_handler(
    lambda c: c.data in ["post_np", "post_ukr"],
    state=OrderStates.waiting_for_address_or_post_service
)
async def process_post_service(callback: types.CallbackQuery, state: FSMContext):
    post_service = callback.data
    await state.update_data(post_service=post_service)
    await callback.answer()
    await bot.send_message(callback.message.chat.id, "Введіть номер відділення або адресу вручну:")
    await OrderStates.confirmation.set()

@dp.message_handler(state=OrderStates.waiting_for_address_or_post_service)
async def process_address_manual(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get('delivery_type') == 'delivery_address':
        await state.update_data(address=message.text)
        await confirm_order(message, state)
    else:
        await state.update_data(post_address=message.text)
        await confirm_order(message, state)

async def confirm_order(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cart = get_cart(message.chat.id)
    if not cart:
        await message.answer("Ваш кошик порожній, замовлення скасовано.")
        await state.finish()
        return
    # Подальша логіка обробки підтвердження замовлення...

  
# Підготувати текст підтвердження
text = (
    f"Підтвердіть ваше замовлення:\n\n"
    f"Ім'я: {escape_md(data['name'], version=2)}\n"
    f"Телефон: {escape_md(data['phone'], version=2)}\n"
    f"Місто: {escape_md(data['city'], version=2)}\n"
    f"Тип доставки: {escape_md('Адресна доставка' if data['delivery_type']=='delivery_address' else 'Доставка у відділення', version=2)}\n"
)
if data['delivery_type'] == 'delivery_address':
    text += f"Адреса: {escape_md(data.get('address',''), version=2)}\n"
else:
    service_name = "Нова Пошта" if data.get('post_service') == "post_np" else "Укрпошта"
    text += f"Служба доставки: {service_name}\n"
    text += f"Відділення/адреса: {escape_md(data.get('post_address',''), version=2)}\n"

# Список товарів і підсумок
cart_items = []
for parfum_id, qty in cart.items():
    parfum = None
    for cat_parfums in PARFUMS.values():
        for p in cat_parfums:
            if p['id'] == parfum_id:
                parfum = p
                break
        if parfum:
           break
if parfum:
    for _ in range(qty):
        cart_items.append({
            'id': parfum['id'],
            'name': parfum['name'],
            'price': parfum['price']
        })
  for i, item in enumerate(cart_items):
    if item['id'] == DISCOUNT_DAY_ITEM['id']:
        cart_items[i]['discount_day'] = True

updated_items, total_discount, total_price = calculate_cart_summary(cart_items)

for item in updated_items:
    text += f"\n- {escape_md(item['name'], version=2)} — {item['final_price']:.2f} грн"

text += f"\n\nЗагальна знижка: {total_discount:.2f} грн"
text += f"\nДо оплати: {total_price:.2f} грн"

kb = InlineKeyboardMarkup()
kb.add(InlineKeyboardButton("✅ Підтвердити замовлення", callback_data="confirm_order"))
kb.add(InlineKeyboardButton("❌ Скасувати", callback_data="cancel_order"))

await message.answer(text, parse_mode='MarkdownV2', reply_markup=kb)Щоб виправити помилку `KeyError: 'price'`, потрібно переконатися, що кожен елемент у `cart_items` (тобто кожен товар у кошику) містить ключ `'price'`. Помилка сталася в функції `calculate_cart_summary`, де очікується, що кожен товар має `item['price']`, але цей ключ відсутній.

