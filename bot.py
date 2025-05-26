import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.utils import executor
from aiogram.utils.markdown import escape_md

BOT_TOKEN = '7511346484:AAEm89gjBctt55ge8yEqrfHrxlJ-yS4d56U'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Дані парфумів (заглушки назви і фото)
perfumes = {
    'female': [
        {
            'id': 'f1',
            'name': 'Парфум Жіночий 1',
            'photo': 'https://via.placeholder.com/150?text=Жіночий+1',
            'price': 200
        },
        {
            'id': 'f2',
            'name': 'Парфум Жіночий 2',
            'photo': 'https://via.placeholder.com/150?text=Жіночий+2',
            'price': 200
        },
    ],
    'unisex': [
        {
            'id': 'u1',
            'name': 'Парфум Унісекс 1',
            'photo': 'https://via.placeholder.com/150?text=Унісекс+1',
            'price': 200
        },
        {
            'id': 'u2',
            'name': 'Парфум Унісекс 2',
            'photo': 'https://via.placeholder.com/150?text=Унісекс+2',
            'price': 200
        },
    ],
    'top': [
        {
            'id': 't1',
            'name': 'ТОП Парфум 1',
            'photo': 'https://via.placeholder.com/150?text=ТОП+1',
            'price': 200
        },
        {
            'id': 't2',
            'name': 'ТОП Парфум 2',
            'photo': 'https://via.placeholder.com/150?text=ТОП+2',
            'price': 200
        },
    ]
}

# Користувацькі кошики: user_id -> list товарів
user_carts = {}

# --- Головне меню ---
def main_menu_kb():
    kb = InlineKeyboardMarkup(row_width=6)
    kb.add(
        InlineKeyboardButton("Каталог парфум", callback_data="catalog"),
        InlineKeyboardButton("Акції та бонуси", callback_data="promos"),
        InlineKeyboardButton("Знижка дня", callback_data="discount_day"),
        InlineKeyboardButton("Як замовити?", callback_data="how_to_order"),
        InlineKeyboardButton("Зв'язатися з нами", callback_data="contact_us"),
        InlineKeyboardButton("Кошик", callback_data="cart")
    )
    return kb

# --- Меню каталогу ---
def catalog_menu_kb():
    kb = InlineKeyboardMarkup(row_width=4)
    kb.add(
        InlineKeyboardButton("Жіночі", callback_data="cat_female"),
        InlineKeyboardButton("Унісекс", callback_data="cat_unisex"),
        InlineKeyboardButton("ТОП ПРОДАЖ", callback_data="cat_top"),
        InlineKeyboardButton("Повернутися назад", callback_data="main_menu")
    )
    return kb

# --- Кнопки під парфумом ---
def perfume_buttons_kb():
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("➕ Додати до кошика", callback_data="add_to_cart"),
        InlineKeyboardButton("🔙 Назад до каталогу", callback_data="catalog"),
        InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")
    )
    return kb

# --- Показ головного меню (картинка + текст + кнопки) ---
async def send_main_menu(message_or_callback):
    text = (
        "Вітаємо у нашому магазині парфумів!\n"
        "Обирайте категорію або дійте за меню."
    )
    main_photo_url = "https://via.placeholder.com/400x200?text=Головне+Меню+Парфумів"

    if isinstance(message_or_callback, types.Message):
        await bot.send_photo(
            message_or_callback.chat.id,
            main_photo_url,
            caption=text,
            reply_markup=main_menu_kb()
        )
    else:  # CallbackQuery
        await message_or_callback.message.edit_media(
            media=types.InputMediaPhoto(media=main_photo_url, caption=text, parse_mode='HTML'),
            reply_markup=main_menu_kb()
        )

# --- Обробка будь-якого текстового повідомлення (запуск головного меню) ---
@dp.message_handler()
async def any_message_handler(message: types.Message):
    await send_main_menu(message)

# --- Обробка callback для головного меню та каталогу ---
@dp.callback_query_handler(lambda c: True)
async def process_callback(callback: types.CallbackQuery):
    data = callback.data

    if data == "main_menu":
        await send_main_menu(callback)
        await callback.answer()

    elif data == "catalog":
        text = "Оберіть категорію парфумів:"
        await callback.message.edit_text(text, reply_markup=catalog_menu_kb())
        await callback.answer()

    elif data in ["cat_female", "cat_unisex", "cat_top"]:
        # Визначаємо категорію
        category_map = {
            "cat_female": "female",
            "cat_unisex": "unisex",
            "cat_top": "top"
        }
        category_key = category_map[data]
        perfumes_list = perfumes[category_key]

        # Відправляємо 2 парфуми в 1 рядок (поки що послідовно)
        # Через обмеження Telegram, краще відправляти повідомлення з фото окремо для кожного парфуму
        # Але тут зробимо одне повідомлення з 2 назвами і кнопками для кожного

        text = f"Категорія: {category_key.capitalize()}\nОберіть парфум:"

        # Видаляємо старе повідомлення і відправляємо нове з фото та кнопками
        media_group = [
            types.InputMediaPhoto(media=perfumes_list[0]['photo'], caption=f"{perfumes_list[0]['name']}\nЦіна: {perfumes_list[0]['price']} грн"),
            types.InputMediaPhoto(media=perfumes_list[1]['photo'], caption=f"{perfumes_list[1]['name']}\nЦіна: {perfumes_list[1]['price']} грн"),
        ]
        # Видаляємо старе повідомлення, бо edit_media для групи не підтримується
        await callback.message.delete()
        await bot.send_media_group(callback.message.chat.id, media_group)

        # Після фото - відправляємо клавіатуру для кожного товару
        # Для спрощення - під кожним фото буде однакова клавіатура, але Telegram не підтримує inline під фото окремо,
        # тому в кожному повідомленні кнопки будуть загальні під останнім повідомленням.

        kb = InlineKeyboardMarkup(row_width=3)
        for p in perfumes_list:
            kb.add(
                InlineKeyboardButton(f"➕ Додати {p['name']} до кошика", callback_data=f"add_{p['id']}"),
            )
        kb.add(
            InlineKeyboardButton("🔙 Назад до каталогу", callback_data="catalog"),
            InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")
        )

        await bot.send_message(callback.message.chat.id, "Оберіть дію:", reply_markup=kb)
        await callback.answer()

    elif data.startswith("add_"):
        user_id = callback.from_user.id
        perfume_id = data[4:]

        # Знаходимо парфум за id
        all_perfumes = perfumes['female'] + perfumes['unisex'] + perfumes['top']
        perfume_item = next((p for p in all_perfumes if p['id'] == perfume_id), None)
        if perfume_item is None:
            await callback.answer("Парфум не знайдено", show_alert=True)
            return

        # Додаємо до кошика
        user_carts.setdefault(user_id, [])
        user_carts[user_id].append(perfume_item)

        await callback.answer(f"Товар '{perfume_item['name']}' доданий до кошика!", show_alert=True)

    else:
        await callback.answer()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
# Додаємо до існуючого коду нижче або у відповідні блоки

# --- Тексти для нових розділів ---
PROMOS_TEXT = (
    "🎉 Акції та бонуси:\n\n"
    "1. 1+1 зі знижкою 20% на другий товар\n"
    "2. Пакетна пропозиція: 4 парфуми за 680 грн\n"
    "3. Безкоштовна доставка від 600 грн\n"
    "4. Безкоштовна доставка на перше замовлення від 2 шт (без акцій)\n"
    "5. Розіграш серед нових покупців\n"
)

DISCOUNT_DAY_ITEM = {
    'id': 'discount_day_1',
    'name': 'Парфум Знижка Дня',
    'photo': 'https://via.placeholder.com/150?text=Знижка+Дня',
    'original_price': 200,
    'discount_price': 160
}

HOW_TO_ORDER_TEXT = (
    "🛒 Як замовити?\n\n"
    "1. Оберіть парфум у каталозі.\n"
    "2. Додайте у кошик.\n"
    "3. Оформіть замовлення через кошик.\n"
    "4. Оберіть спосіб доставки.\n"
    "5. Очікуйте на підтвердження та номер накладної.\n"
)

CONTACT_US_TEXT = (
    "📞 Зв'язатися з нами:\n\n"
    "Телефон: +38 099 123 45 67\n"
    "Telegram: @parfum_shop_support\n"
    "Email: support@parfumshop.ua\n"
)

# --- Кнопка "Повернутися в головне меню" ---
def back_to_main_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu"))
    return kb

# --- Обробка callback для нових пунктів меню ---
@dp.callback_query_handler(lambda c: c.data in ["promos", "discount_day", "how_to_order", "contact_us"])
async def special_sections_handler(callback: types.CallbackQuery):
    data = callback.data

    if data == "promos":
        await callback.message.edit_text(PROMOS_TEXT, reply_markup=back_to_main_kb())
        await callback.answer()

    elif data == "discount_day":
        caption = (
            f"{DISCOUNT_DAY_ITEM['name']}\n"
            f"Ціна зі знижкою: {DISCOUNT_DAY_ITEM['discount_price']} грн (звичайна {DISCOUNT_DAY_ITEM['original_price']} грн)"
        )
        photo_url = DISCOUNT_DAY_ITEM['photo']
        # Оновлюємо повідомлення фото + текст + кнопка "Додати до кошика"
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("➕ Додати до кошика", callback_data=f"add_{DISCOUNT_DAY_ITEM['id']}"),
            InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")
        )
        await callback.message.edit_media(
            media=types.InputMediaPhoto(media=photo_url, caption=caption),
            reply_markup=kb
        )
        await callback.answer()

    elif data == "how_to_order":
        await callback.message.edit_text(HOW_TO_ORDER_TEXT, reply_markup=back_to_main_kb())
        await callback.answer()

    elif data == "contact_us":
        await callback.message.edit_text(CONTACT_US_TEXT, reply_markup=back_to_main_kb())
        await callback.answer()

# --- Обробка додавання "Знижка дня" до кошика ---
@dp.callback_query_handler(lambda c: c.data == f"add_{DISCOUNT_DAY_ITEM['id']}")
async def add_discount_day_to_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    # Формуємо товар зі знижкою
    perfume_item = {
        'id': DISCOUNT_DAY_ITEM['id'],
        'name': DISCOUNT_DAY_ITEM['name'],
        'price': DISCOUNT_DAY_ITEM['discount_price'],
        'photo': DISCOUNT_DAY_ITEM['photo']
    }
    user_carts.setdefault(user_id, [])
    user_carts[user_id].append(perfume_item)
    await callback.answer(f"Товар '{perfume_item['name']}' доданий до кошика зі знижкою!", show_alert=True)

# --- Додаємо обробку повернення в головне меню для існуючих обробників ---
@dp.callback_query_handler(lambda c: c.data == "main_menu")
async def go_main_menu(callback: types.CallbackQuery):
    await send_main_menu(callback)
    await callback.answer()
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loader import dp
from utils.cart import get_cart, calculate_cart_total, clear_cart
from data.config import SHEET_NAME
from loader import sheet, bot

class OrderState(StatesGroup):
    full_name = State()
    phone = State()
    city = State()
    delivery_type = State()
    address = State()
    post_service = State()
    post_number = State()

@dp.message_handler(text="Оформити замовлення")
async def start_order(message: types.Message, state: FSMContext):
    cart = get_cart(message.from_user.id)
    if not cart:
        await message.answer("Ваш кошик порожній.")
        return
    await message.answer("✍ Напишіть ваше ПІБ")
    await OrderState.full_name.set()

@dp.message_handler(state=OrderState.full_name)
async def get_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("📞 Вкажіть Ваш номер телефону")
    await OrderState.phone.set()

@dp.message_handler(state=OrderState.phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("🏙 Вкажіть місто доставки")
    await OrderState.city.set()

@dp.message_handler(state=OrderState.city)
async def get_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📦 Доставка на пошту", callback_data="delivery_post"),
        InlineKeyboardButton("🚚 Адресна доставка", callback_data="delivery_address")
    )

    await message.answer("🚚 Оберіть зручну для вас доставку", reply_markup=keyboard)
    await OrderState.delivery_type.set()

@dp.callback_query_handler(lambda c: c.data == "delivery_address", state=OrderState.delivery_type)
async def address_delivery(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_reply_markup()
    await bot.send_message(callback_query.from_user.id, "📝 Введіть повну адресу доставки")
    await state.update_data(delivery_type="Адресна доставка")
    await OrderState.address.set()

@dp.message_handler(state=OrderState.address)
async def get_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await finish_order(message, state)

@dp.callback_query_handler(lambda c: c.data == "delivery_post", state=OrderState.delivery_type)
async def post_delivery(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_reply_markup()

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Нова Пошта", callback_data="nova_poshta"),
        InlineKeyboardButton("Укрпошта", callback_data="ukrposhta")
    )

    await bot.send_message(callback_query.from_user.id, "📮 Оберіть поштову службу", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data in ["nova_poshta", "ukrposhta"], state=OrderState.delivery_type)
async def get_post_service(callback_query: types.CallbackQuery, state: FSMContext):
    service = "Нова Пошта" if callback_query.data == "nova_poshta" else "Укрпошта"
    await callback_query.message.edit_reply_markup()
    await bot.send_message(callback_query.from_user.id, f"🔢 Введіть номер відділення {service}")
    await state.update_data(delivery_type="Поштова доставка", post_service=service)
    await OrderState.post_number.set()

@dp.message_handler(state=OrderState.post_number)
async def get_post_number(message: types.Message, state: FSMContext):
    await state.update_data(post_number=message.text)
    await finish_order(message, state)

async def finish_order(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cart = get_cart(message.from_user.id)
    total = calculate_cart_total(cart)

    items = "\n".join([f"- {item['name']} x{item['quantity']} = {item['price']*item['quantity']} грн" for item in cart])

    order_text = (
        f"🧾 <b>Ваше замовлення:</b>\n"
        f"{items}\n\n"
        f"💰 <b>Разом:</b> {total} грн\n\n"
        f"👤 ПІБ: {data.get('full_name')}\n"
        f"📞 Телефон: {data.get('phone')}\n"
        f"🏙 Місто: {data.get('city')}\n"
        f"🚚 Доставка: {data.get('delivery_type')}\n"
    )

    if data.get("delivery_type") == "Адресна доставка":
        order_text += f"🏡 Адреса: {data.get('address')}\n"
    else:
        order_text += (
            f"📮 Служба: {data.get('post_service')}\n"
            f"🏤 Відділення №: {data.get('post_number')}\n"
        )

    await message.answer(order_text, parse_mode="HTML")
    
    # Запис до Google Sheets
    sheet.append_row([
        message.from_user.id,
        data.get('full_name'),
        data.get('phone'),
        data.get('city'),
        data.get('delivery_type'),
        data.get('address') or f"{data.get('post_service')} №{data.get('post_number')}",
        str(total)
    ], table_range=SHEET_NAME)

    clear_cart(message.from_user.id)
    await state.finish()
    await message.answer("✅ Дякуємо за замовлення! Менеджер зв’яжеться з вами найближчим часом.")
