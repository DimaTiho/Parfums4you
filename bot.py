import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text

API_TOKEN = '7511346484:AAEm89gjBctt55ge8yEqrfHrxlJ-yS4d56U'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.MARKDOWN)
dp = Dispatcher(bot, storage=MemoryStorage())

# --- Google Sheets Setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google_credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Perfume Orders").sheet1

# --- Стан машини для майбутніх етапів ---
class OrderForm(StatesGroup):
    name = State()
    phone = State()
    city = State()
    delivery_type = State()
    address = State()
    promo = State()

# --- Тимчасове зберігання кошика (по user_id) ---
user_carts = {}

# --- Головне меню ---
main_menu = InlineKeyboardMarkup(row_width=2).add(
    InlineKeyboardButton("Каталог парфум", callback_data="catalog"),
    InlineKeyboardButton("Акції та бонуси", callback_data="actions"),
    InlineKeyboardButton("Знижка дня", callback_data="day_discount"),
    InlineKeyboardButton("Як замовити?", callback_data="how_to_order"),
    InlineKeyboardButton("Відгуки", callback_data="reviews"),
    InlineKeyboardButton("Зв'язатися з менеджером", callback_data="contact"),
    InlineKeyboardButton("🛒 Кошик", callback_data="view_cart")
)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    photo = types.InputFile("images/main_photo.jpg")
    text = ("\U0001F9F4 *Ласкаво просимо до нашого ароматного світу!*")
    text += ("\n\n\U0001F33A У нашому магазині ви знайдете брендові жіночі, чоловічі та унісекс парфуми — обрані з любов'ю.")
    text += ("\n\U0001F4B8 Ми пропонуємо найкращі ціни та щедрі знижки для нових і постійних клієнтів.")
    text += ("\n\U0001F381 Усі покупці можуть скористатися акціями та отримати приємні подарунки.")
    text += ("\n\U0001F69A Доставка по всій Україні. Безкоштовна — при замовленні від 500 грн.")
    text += ("\n\n⬇ Оберіть розділ нижче, щоб почати замовлення або переглянути наші пропозиції.")
    await message.answer_photo(photo=photo, caption=text, reply_markup=main_menu)

@dp.message_handler(lambda message: message.text.lower() in ["привіт", "hi", "hello"])
async def intro(message: types.Message):
    await message.reply("Привіт, я твій чат-бот! Щоб мене запустити, натисни /start")

# --- Кошик ---
@dp.callback_query_handler(Text(equals="view_cart"))
async def view_cart(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await callback_query.message.edit_text("Ваш кошик порожній. Додайте парфуми з каталогу!", reply_markup=main_menu)
        return

    text = "🛒 *Ваш кошик:*\n"
    total = 0
    for idx, item in enumerate(cart):
        text += f"{idx+1}. {item['name']} — {item['price']} грн\n"
        total += item['price']

    text += f"\n💰 *Загальна сума:* {total} грн"
    keyboard = InlineKeyboardMarkup(row_width=2)
    for idx in range(len(cart)):
        keyboard.insert(InlineKeyboardButton(f"❌ {idx+1}", callback_data=f"remove_{idx}"))
    keyboard.add(
        InlineKeyboardButton("⬅ Головне меню", callback_data="back_main"),
        InlineKeyboardButton("✅ Оформити замовлення", callback_data="checkout")
    )
    await callback_query.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query_handler(Text(startswith="remove_"))
async def remove_item(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    idx = int(callback_query.data.split("_")[1])
    cart = user_carts.get(user_id, [])
    if 0 <= idx < len(cart):
        cart.pop(idx)
        user_carts[user_id] = cart
    await view_cart(callback_query)

@dp.callback_query_handler(Text(equals="checkout"))
async def checkout(callback_query: types.CallbackQuery, state: FSMContext):
    await OrderForm.name.set()
    await callback_query.message.answer("Введіть ваше ім’я:")

@dp.message_handler(state=OrderForm.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await OrderForm.phone.set()
    await message.answer("Введіть ваш номер телефону:")

@dp.message_handler(state=OrderForm.phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await OrderForm.city.set()
    await message.answer("Введіть місто доставки:")

@dp.message_handler(state=OrderForm.city)
async def get_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await OrderForm.address.set()
    await message.answer("Введіть адресу або номер відділення:")

@dp.message_handler(state=OrderForm.address)
async def get_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
    cart_items = ", ".join([item['name'] for item in cart])
    total = sum(item['price'] for item in cart)

    order_data = await state.get_data()

    sheet.append_row([
        order_data['name'],
        order_data['phone'],
        order_data['city'],
        order_data['address'],
        cart_items,
        total
    ])

    await message.answer("✅ Ваше замовлення прийнято та надіслано! Ми з вами зв'яжемося найближчим часом.", reply_markup=main_menu)
    await state.finish()
    user_carts[user_id] = []

# --- Додати до кошика (буде використовуватись у каталозі) ---
async def add_to_cart(user_id: int, item: dict):
    cart = user_carts.setdefault(user_id, [])
    cart.append(item)

# --- Хендлер для кнопок головного меню ---
@dp.callback_query_handler(Text(equals="catalog"))
async def catalog_section(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("Жіночі", callback_data="cat_women"),
        InlineKeyboardButton("Унісекс", callback_data="cat_unisex"),
        InlineKeyboardButton("Топ продаж", callback_data="cat_top")
    ).add(
        InlineKeyboardButton("⬅ Повернутися", callback_data="back_main")
    )
    await callback_query.message.edit_text("Оберіть категорію парфумів:", reply_markup=keyboard)

# --- Категорії парфумів (Жіночі, Унісекс, Топ продаж) ---
# (код тут залишено без змін)

# --- Хендлер акцій ---
@dp.callback_query_handler(Text(equals="actions"))
async def show_promotions(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🎉 Третій парфум у подарунок", callback_data="promo1"),
        InlineKeyboardButton("🚚 Безкоштовна доставка від 500 грн", callback_data="promo2"),
        InlineKeyboardButton("🕒 Ранкова знижка -10%", callback_data="promo3"),
        InlineKeyboardButton("🎁 Парфум-сюрприз у подарунок", callback_data="promo4"),
        InlineKeyboardButton("⬅ Головне меню", callback_data="back_main"))
    await callback_query.message.edit_text("Обери акцію, щоб дізнатись більше:", reply_markup=keyboard)

@dp.callback_query_handler(Text(equals="promo4"))
async def promo_gift_details(callback_query: types.CallbackQuery):
    text = ("🎁 *Парфум-сюрприз у подарунок*"\            "

Отримайте рандомний міні-парфум у подарунок при покупці від 3-х товарів на суму від 600 грн."\
            "
Знижка не сумується з іншими акціями."\
            "
Подарунок додається автоматично під час обробки замовлення.")
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🛍 Перейти до каталогу", callback_data="catalog"),
        InlineKeyboardButton("⬅ Назад до акцій", callback_data="actions")    )
    await callback_query.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query_handler(Text(startswith="back_main"))
async def back_to_main(callback_query: types.CallbackQuery):
    await send_welcome(callback_query.message)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
