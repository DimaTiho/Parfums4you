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
from gspread.utils import rowcol_to_a1
from collections import defaultdict
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

sheet_header = [
    "Дата", "Час", "Ім’я", "Телефон", "Місто", "Тип доставки", "Адреса / Відділення",
    "Замовлення", "Загальна сума", "Знижка", "Суми", "Оплата",
    "ID клієнта", "Номер ТТН", "Підтвердження доставки"
]
if sheet.row_values(1) != sheet_header:
    sheet.update("A1", [sheet_header])


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
  
user_carts = {}  # Словник користувачів з їхніми кошиками
user_discounts = {} 
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
    [InlineKeyboardButton("✒️Зв'язатися з менеджером", url="https://t.me/parfum_vibes"), InlineKeyboardButton("🛒 Кошик", callback_data="show_cart")]
]
main_menu = InlineKeyboardMarkup(inline_keyboard=main_menu_buttons)

# === Каталог парфумів ===
catalog_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton("🌸Жіночі", callback_data="cat_women"), InlineKeyboardButton("🥥🍓Унісекс", callback_data="cat_unisex")],
    [InlineKeyboardButton("🔝💣Топ продаж", callback_data="cat_top")],
    [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
])

perfume_catalog = {
    "cat_women": [
        {"name": "Victoria`s Secret Bombshell Isle", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1},
        {"name": "Victoria`s Secret Compassion", "price": 200, "photo": "https://i.postimg.cc/c4y5cmzc/photo-2025-05-30-14-53-53-23.jpg.","quantity": 1},
        {"name": "Lattafa Yara Tous", "price": 200, "photo": "https://i.postimg.cc/7PQgNYQM/photo-2025-05-30-14-53-53-14.jpg.","quantity": 1},
        {"name": "Lattafa Yara Candy", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1},
        {"name": "Lattafa Haya", "price": 200, "photo": "https://i.postimg.cc/ydjHcG1W/photo-2025-05-30-14-53-46-3.jpg.","quantity": 1},
        {"name": "Lattafa Noble Blush", "price": 200, "photo": "https://i.postimg.cc/qMyxMHjs/photo-2025-05-30-14-53-53-16.jpg.","quantity": 1},
        {"name": "Lattafa Eclaire", "price": 200, "photo": "https://i.postimg.cc/W4F3TT7j/photo-2025-05-30-14-53-53-18.jpg.","quantity": 1},
        {"name": "Chanel Chance eau Fraiche", "price": 200, "photo": "https://i.postimg.cc/jj5xvK1P/photo-2025-05-30-14-53-53-5.jpg.jpg","quantity": 1},
        {"name": "Chanel Chance eau Tendre", "price": 200, "photo": "https://i.postimg.cc/q7nmP6WT/photo-2025-05-30-14-53-53-10.jpg.","quantity": 1},
        {"name": "Giorgio Armani Si Passione", "price": 200, "photo": "https://i.postimg.cc/pVBSV8rV/photo-2025-05-30-14-53-53-9.jpg.","quantity": 1},
        {"name": "Giorgio Armani My Way Nectar", "price": 200, "photo": "https://i.postimg.cc/L5z2hsqK/photo-2025-05-30-14-53-53-6.jpg.","quantity": 1},
        {"name": "Yves Saint Laurent Black Opium", "price": 200, "photo": "https://i.postimg.cc/pL3zMGt9/photo-2025-05-30-14-53-53-2.jpg.","quantity": 1},
        {"name": "Yves Saint Laurent Libre", "price": 200, "https://i.postimg.cc/fRWDTDDp/photo-2025-05-30-14-53-53-7.jpg.","quantity": 1},
        {"name": "Yves Saint Laurent Mon Paris", "price": 200, "photo": "https://i.postimg.cc/3x8xq2qs/photo-2025-05-30-14-53-43-5.jpg.","quantity": 1},
        {"name": "Haute Fragrance Company Wear Love Everywhere", "price": 200, "photo": "https://i.postimg.cc/WbQQFVGX/photo-2025-05-30-14-53-46-5.jpg.","quantity": 1},
        {"name": "Haute Fragrance Company Devil`s Intrigue", "price": 200, "photo": "https://i.postimg.cc/9MLyKWX2/photo-2025-05-30-14-53-53-13.jpg.","quantity": 1},
        {"name": "Carolina Herrera Good Girl Blush", "price": 200, "photo": "https://i.postimg.cc/902DFKxM/photo-2025-05-30-14-53-45-5.jpg.","quantity": 1},
        {"name": "Carolina Herrera Good Girl Velvet Fatale", "price": 200, "photo": "https://i.postimg.cc/N0zrgycN/photo-2025-05-30-14-53-43-2.jpg.","quantity": 1},
        {"name": "Montale Roses Musk", "price": 200, "photo": "https://i.postimg.cc/vBby1ydp/photo-2025-05-30-14-53-46-2.jpg.","quantity": 1},
        {"name": "Montale Fruity", "price": 200, "photo": "https://i.postimg.cc/3RVy5WGg/photo-2025-05-30-14-53-43-3.jpg.","quantity": 1},
        {"name": "Escada Candy Love", "price": 200, "photo": "https://i.postimg.cc/XvV8z1Kw/photo-2025-05-30-14-53-53-21.jpg.","quantity": 1},
        {"name": "Escada Sorbetto Rosso", "price": 200, "photo": "https://i.postimg.cc/bJZFmF8m/photo-2025-05-30-14-53-53-22.jpg.","quantity": 1},
        {"name": "Dolce & Gabbana Anthology l`Imperatrice 3", "price": 200, "photo": "https://i.postimg.cc/pdGD1WLH/photo-2025-05-30-14-53-53-17.jpg.","quantity": 1},
        {"name": "Ariana Grande Cloud Pink", "price": 200, "photo": "https://i.postimg.cc/sfPc9rCT/photo-2025-05-30-14-53-47-8.jpg.","quantity": 1},
        {"name": "Attar Collection Crystal Love for her", "price": 200, "photo": "https://i.postimg.cc/bJ0qwJSX/photo-2025-05-30-14-53-53-20.jpg.","quantity": 1},
        {"name": "Cacharel Amor Amor", "price": 200, "photo": "https://i.postimg.cc/mr0wVZr5/photo-2025-05-30-14-53-47-7.jpg.","quantity": 1},
        {"name": "Elizabeth Arden White Tea", "price": 200, "photo": "https://i.postimg.cc/1tfkV3j7/photo-2025-05-30-14-53-47-5.jpg.","quantity": 1},
        {"name": "Labcome La Vie Est Belle", "price": 200, "photo": "https://i.postimg.cc/QdT0RWWq/photo-2025-05-30-14-53-44-6.jpg.","quantity": 1},
        {"name": "Gritti Tutu", "price": 200, "photo": "https://i.postimg.cc/x1J4n4BM/photo-2025-05-30-14-53-44-4.jpg.","quantity": 1},
        {"name": "Versace Bright Crystal", "price": 200, "photo": "https://i.postimg.cc/zXtT0DtF/photo-2025-05-30-14-53-48.jpg.","quantity": 1},
        {"name": "Chloe Nomade", "price": 200, "photo": "https://i.postimg.cc/HkYP7LJ0/photo-2025-05-30-14-53-47-6.jpg.","quantity": 1},
        {"name": "Billie Eilish Eilish", "price": 200, "photo": "https://i.postimg.cc/Y2RV3g1G/photo-2025-05-30-14-53-44-3.jpg.","quantity": 1},
        {"name": "Jean Paul Gaultier Scandal", "price": 200, "photo": "https://i.postimg.cc/P5WFCwr5/photo-2025-05-30-14-53-47-2.jpg.","quantity": 1},
        {"name": "Christian Dior Miss Dior Cherie Blooming Boquet", "price": 200, "photo": "https://i.postimg.cc/xddqXLyv/photo-2025-05-30-14-53-43-4.jpg.","quantity": 1},
        {"name": "Prada Paradoxe", "price": 200, "photo": "https://i.postimg.cc/7bvm6xFz/photo-2025-05-30-14-53-47-3.jpg.","quantity": 1},
        {"name": "Moschino Toy 2", "price": 200, "photo": "https://i.postimg.cc/4dkdBjR5/photo-2025-05-30-14-53-45.jpg.","quantity": 1},
        {"name": "By Kajal Dahab", "price": 200, "photo": "https://i.postimg.cc/26bQBsF7/photo-2025-05-30-14-53-45-2.jpg.","quantity": 1},
        {"name": "Givenchy Ange ou Demon Le Secret", "price": 200, "photo": "https://i.postimg.cc/MpwJ3xnX/photo-2025-05-30-14-53-47-4.jpg.","quantity": 1}
],
    "cat_unisex": 
 [
        {"name": "RicHard White Chocola", "price": 200, "photo": "https://i.postimg.cc/T1Wh0GpC/photo-2025-05-30-14-53-53-15.jpg.","quantity": 1},
        {"name": "Montale Starry Nights", "price": 200, "photo": "https://i.postimg.cc/KzSPB9qX/photo-2025-05-30-14-53-47.jpg.","quantity": 1},
        {"name": "Montale Intense Cafe", "price": 200, "photo": "https://i.postimg.cc/zv8sfFT5/photo-2025-05-30-14-53-43.jpg.","quantity": 1},
        {"name": "Montale  Chocolate Greedy", "price": 200, "photo": "https://i.postimg.cc/Bnn1FWJP/photo-2025-05-30-14-53-45-4.jpg.","quantity": 1},
        {"name": "Attar Collection Azalea", "price": 200, "photo": "https://i.postimg.cc/ZnZK83zK/photo-2025-05-30-14-53-53-19.jpgs.","quantity": 1},
        {"name": "Attar Collection Hayati", "price": 200, "photo": "https://i.postimg.cc/qv6QKCJ3/photo-2025-05-30-14-53-53-11.jpg.","quantity": 1},
        {"name": "Attar Collection Al Rayhan", "price": 200, "photo": "https://i.postimg.cc/9FKYcFdF/photo-2025-05-30-14-53-53-12.jpg.","quantity": 1},
        {"name": "Tom Ford Cherry Smoke", "price": 200, "photo": "https://i.postimg.cc/d14bLT6y/photo-2025-05-30-14-53-46-4.jpg.","quantity": 1},
        {"name": "Tom Ford Lost Cherry", "price": 200, "photo": "https://i.postimg.cc/rFQ7jW2Z/photo-2025-05-30-14-53-53-8.jpg.","quantity": 1},
        {"name": "Marc-Antoine Barrois Tilia","price": 200, "photo": "https://i.postimg.cc/ZnNxXGW5/photo-2025-05-30-14-53-44.jpg.","quantity": 1},
        {"name": "Kilian Apple Brandy on the Rocks", "price": 200, "photo": "https://i.postimg.cc/kgzLSmWT/photo-2025-05-30-14-53-44-2.jpg.","quantity": 1},
        {"name": "Kilian Angel`s Share", "price": 200, "photo": "https://i.postimg.cc/jS3tkmPf/photo-2025-05-30-14-53-43-6.jpg.","quantity": 1},
        {"name": "Tiziana Terenzi Cassiopea", "price": 200, "photo": "https://i.postimg.cc/8ckrmxLY/photo-2025-05-30-14-53-53-3.jpg.","quantity": 1},
        {"name": "Escentric Molecules Molecule 02", "price": 200, "photo": "https://i.postimg.cc/s2Xn20B3/photo-2025-05-30-14-53-53.jpg.","quantity": 1},
        {"name": "Zarkoperfume Pink Molecule 090.09", "price": 200, "photo": "https://i.postimg.cc/nV6XzsP5/photo-2025-05-30-14-53-53-4.jpg.","quantity": 1},
        {"name": "Maison Francis Kurkdjian Baccarat Rouge 540", "price": 200, "photo": "https://i.postimg.cc/KzFq7vjD/photo-2025-05-30-14-53-44-5.jpg.","quantity": 1},
        {"name": "Maison Francis Kurkdjian 724", "price": 200, "photo": "https://i.postimg.cc/DZ9qQxxk/photo-2025-05-30-14-53-45-3.jpg.","quantity": 1}
                

],
    "cat_top": [
        {"name": "Creed Aventus", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1},
        {"name": "Chanel Coco Mademoiselle", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1},
        {"name": "Chanel Coco Mademoiselle", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1},
        {"name": "Chanel Coco Mademoiselle", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1},
        {"name": "Chanel Coco Mademoiselle", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1},
        {"name": "Chanel Coco Mademoiselle", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1},
        {"name": "Chanel Coco Mademoiselle", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1},
        {"name": "Maison Francis Kurkdjian Baccarat Rouge", "price": 200, "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg?cs=srgb&dl=pexels-valeriya-965731.jpg&fm=jpg&_gl=1*5lwmep*_ga*MTMzNzc3NDI2LjE3NDY4ODA2NzY.*_ga_8JE65Q40S6*czE3NDY4ODA2NzUkbzEkZzEkdDE3NDY4ODA2ODAkajAkbDAkaDA.","quantity": 1}
    ]
}
@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))

@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))
async def handle_category(callback: types.CallbackQuery):
    perfumes = perfume_catalog.get(callback.data, [])
    for i in range(0, len(perfumes), 2):
        row = perfumes[i:i+2]
        media = []
        buttons = []
        for p in row:
            text = f"*{p['name']}*\n💸 {p['price']} грн"
            media.append((p['photo'], text))
            buttons.append(InlineKeyboardButton(f"➕ {p['name']}", callback_data=f"add_{p['name']}"))
        for m in media:
            await bot.send_photo(callback.from_user.id, m[0], caption=m[1])
        await bot.send_message(callback.from_user.id, "Оберіть:", reply_markup=InlineKeyboardMarkup(row_width=2).add(*buttons).add(
            InlineKeyboardButton("🔙 Назад до каталогу", callback_data="catalog"),
            InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")
        ))
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
    user_carts.setdefault(user_id, []).append({"name": name + " (зі знижкою)", "price": discounted_price, "quantity": 1})
    await callback.answer("✅ Додано до кошика зі знижкою!")

# Блок: Акції та бонуси
@dp.callback_query_handler(lambda c: c.data == "promotions")
async def promotions_callback(callback: types.CallbackQuery):
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

    await callback.message.answer(promo_text, reply_markup=keyboard)
    await callback.answer()

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


def calculate_cart(cart):
    # Поділ на товари зі знижкою дня та звичайні
    discount_items = [item for item in cart if "(зі знижкою)" in item["name"]]
    normal_items = [item for item in cart if "(зі знижкою)" not in item["name"]]

    def summarize(items):
        counts = defaultdict(int)
        prices = {}
        for item in items:
            counts[item['name']] += item.get('quantity', 1)
            prices[item['name']] = item['price']
        summary = []
        for name, count in counts.items():
            summary.append({
                'name': name,
                'quantity': count,
                'price': prices[name]
            })
        return summary

    normal_summary = summarize(normal_items)
    discount_summary = summarize(discount_items)
    full_summary = normal_summary + discount_summary

    total_price_normal = sum(i['price'] * i['quantity'] for i in normal_summary)
    total_price_discount = sum(i['price'] * i['quantity'] for i in discount_summary)
    day_discount_amount = 0

    # === Акції тільки на звичайні товари ===
    normal_total_items = sum(i['quantity'] for i in normal_summary)

    # 1. -50% на 3-й
    discount_3rd = 0
    if normal_total_items >= 3:
        all_prices = []
        for item in normal_summary:
            all_prices.extend([item['price']] * item['quantity'])
        all_prices.sort()
        discount_3rd = all_prices[2] * 0.5

    # 2. Пакет 4 за 680
    package_discount = 0
    if normal_total_items == 4:
        if total_price_normal > 680:
            package_discount = total_price_normal - 680

    # 3. 20% від 5 од.
    discount_20 = 0
    if normal_total_items >= 5:
        discount_20 = total_price_normal * 0.2

    # 4. 1+1 -30% (перероблено на будь-які товари)
    discount_bogo = 0
    all_unit_prices = []
    for item in normal_summary:
        all_unit_prices.extend([item['price']] * item['quantity'])
    all_unit_prices.sort()
    discount_bogo = sum(price * 0.3 for price in all_unit_prices[1::2])

    best_discount = max(discount_3rd, package_discount, discount_20, discount_bogo)

    final_normal_price = total_price_normal - best_discount
    final_total_price = final_normal_price + total_price_discount


    # Доставка
    free_shipping = final_total_price >= 600

    return {
        'cart': full_summary,
        'total_price': final_total_price,
        'total_discount': round(best_discount, 2),
        'day_discount_amount': round(total_price_discount * (1/0.85 * 0.15), 2),  # щоб показати економію
        'free_shipping': free_shipping
    }
@dp.callback_query_handler(lambda c: c.data.startswith("add_"))
async def add_to_cart_callback(callback: types.CallbackQuery):
    perfume_name = callback.data[4:]
    user_id = callback.from_user.id
    if user_id not in user_carts:
        user_carts[user_id] = []
       # Перевіряємо, чи товар вже в кошику
    for item in user_carts[user_id]:
        if item["name"] == perfume_name:
            item["quantity"] += 1
            break
    else:
        # Якщо товару нема — додаємо з quantity=1
        user_carts[user_id].append({"name": perfume_name, "price": 200,"quantity": 1})
        print(f"User {callback.from_user.id} clicked show_cart")
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

@dp.callback_query_handler(lambda c: c.data == "show_cart")
async def show_cart_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cart = user_carts.get(user_id, [])
    if not cart:
        await callback.message.answer("🛒 Ваш кошик порожній.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton("🔙 Повернення", callback_data="main_menu")]]
            )
        )
        await callback.answer()
        return

    result = calculate_cart(cart)

    text = "*Ваш кошик:*\n"
    for i, item in enumerate(result["cart"], 1):
        text += f"{i}. {item['name']} — {item['quantity']} шт. x {item['price']} грн = {item['quantity'] * item['price']} грн\n"

    text += f"\n💵 Сума без знижок: {sum(i['price'] * i['quantity'] for i in result['cart'])} грн\n"
    if result['day_discount_amount'] > 0:
        text += f"🎉 Знижка дня: {result['day_discount_amount']} грн\n"
    text += f"🎁 Загальна знижка: {result['total_discount']} грн\n"
    text += f"✅ До сплати: {round(result['total_price'])} грн\n"
    if result['free_shipping']:
        text += "🚚 У вас безкоштовна доставка!\n"

    buttons = InlineKeyboardMarkup(row_width=2)
    for item in result['cart']:
        buttons.add(
            InlineKeyboardButton(f"➕ {item['name']}", callback_data=f"increase_{item['name']}"),
            InlineKeyboardButton(f"➖ {item['name']}", callback_data=f"decrease_{item['name']}")
        )
    buttons.add(
        InlineKeyboardButton("🧾 Оформити замовлення", callback_data="checkout"),
        InlineKeyboardButton("🧹 Очистити кошик", callback_data="clear_cart"),
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
    await callback.message.answer("✍️ Введіть ваше *ПІБ* для оформлення замовлення:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("🏠 Головне меню", callback_data="main_menu")]]))
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
@dp.callback_query_handler(lambda c: c.data == "main_menu", state="*")
async def fsm_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await back_to_main(callback)

@dp.message_handler(state=OrderStates.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("🏠 На головне меню", callback_data="main_menu"))
    await message.answer("📞Введіть ваш *номер телефону*:", reply_markup=keyboard)
    await OrderStates.phone.set()
@dp.message_handler(state=OrderStates.phone)
async def get_phone(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or len(message.text) != 10:
        await message.answer("❗ Номер телефону має містити 10 цифр без +38. Наприклад: 0931234567")
        return
    await state.update_data(phone=message.text)
    keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("🏠 На головне меню", callback_data="main_menu"))
    await message.answer("🏙Введіть *місто доставки*:", reply_markup=keyboard)
    await OrderStates.next()



@dp.message_handler(state=OrderStates.city)
async def get_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(OrderStates.delivery_type)
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("На відділення", callback_data="delivery_post"),
        InlineKeyboardButton("Кур'єром на адресу", callback_data="delivery_address")
    ).add(InlineKeyboardButton("🏠 На головне меню", callback_data="main_menu"))
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
    keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("🏠 На головне меню", callback_data="main_menu"))
    await callback.message.answer("📮 Введіть *номер відділення або поштомату* (тільки цифри):", reply_markup=keyboard)
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
    await OrderStates.next()
    # Формування та відображення замовлення
    data = await state.get_data()
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
  

    # після отримання адреси
    result = calculate_cart(cart)

    text_items = ""
    for i, item in enumerate(result['cart'], 1):
        text_items += f"{i}. {escape_md(item['name'])} — {item['price']} грн x {item['quantity']}\n"

    order_summary = (
        f"📦 *Перевірте замовлення перед підтвердженням:*\n"
        f"👤 *ПІБ:* {escape_md(data['name'])}\n"
        f"📞 *Телефон:* {escape_md(data['phone'])}\n"
        f"🏙 *Місто:* {escape_md(data['city'])}\n"
        f"📍 *Адреса / Відділення:* {escape_md(data['address_or_post'])}\n"
        f"🛍 *Товари в кошику:*\n{text_items}"
        f"💵 *Сума без знижок:* {sum(i['price'] * i['quantity'] for i in result['cart'])} грн\n"
        f"🎁 *Знижка:* {round(result['total_discount'])} грн\n"
        f"✅ *До сплати:* {round(result['total_price'])} грн"
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
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")
        name = data.get('name', '-')
        phone = data.get('phone', '-')
        city = data.get('city', '-')
        delivery_method = data.get('delivery_type', '-')
        address = data.get('address_or_post', '-')
        delivery_service = data.get('post_service', '-') if delivery_method == 'delivery_post' else 'Кур’єр'

        cart_items = user_carts.get(user_id, [])
        result = calculate_cart(cart_items)

        order_description = "; ".join([f"{item['name']} x{item['quantity']} ({item['price']} грн)" for item in result['cart']])
        total_sum = sum([item['price'] * item['quantity'] for item in result['cart']])
        total_discount = round(result['total_discount'] + result['day_discount_amount'], 2)
        final_price = round(result['total_price'], 2)
        shipping_payment = "Безкоштовна" if result['free_shipping'] else "Одержувач оплачує"

        sheet.append_row([
            date, time, name, phone, city,
            delivery_service, address, order_description,
            total_sum, total_discount, final_price,
            shipping_payment, str(user_id), "", ""
        ])

        await callback.message.answer("🎉 Замовлення підтверджено! Очікуйте повідомлення з номером ТТН після відправки.")
        user_carts[user_id] = []

    elif callback.data == "cancel_order":
        await callback.message.answer("❌ Замовлення скасовано.")

    await state.finish()
    await callback.answer()


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
        "👇 Оберіть розділ нижче, щоб почати замовлення або переглянути наші пропозиції."
        ),
        reply_markup=main_menu
    )

async def check_new_ttns():
    try:
        data = sheet.get_all_values()
        headers = data[0]
        rows = data[1:]

        tasks = []
        updates = []

        # Визначаємо індекси колонок
        col_id = headers.index("ID клієнта")
        col_ttn = headers.index("Номер ТТН")
        col_confirm = headers.index("Підтвердження доставки")
        confirm_col_number = col_confirm + 1  # бо нумерація з 1

        for i, row in enumerate(rows, start=2):  # з рядка 2, бо 1 — заголовки
            try:
                ttn = row[col_ttn]
                confirm = row[col_confirm]
                if ttn and confirm == "":
                    client_id = int(row[col_id])

                    # Створюємо таск для надсилання
                    async def notify(client_id=client_id, ttn=ttn, row_num=i):
                        try:
                            await bot.send_message(
                                client_id,
                                f"📦 Ваше замовлення відправлено!\nНомер ТТН: `{ttn}`"
                            )
                            updates.append(("✅", row_num))
                        except Exception:
                            logging.exception(f"Помилка надсилання ТТН клієнту ID {client_id}")
                            updates.append(("❌", row_num))

                    tasks.append(notify())

            except Exception:
                logging.exception(f"Помилка обробки рядка {i}")

        # Паралельна відправка
        await asyncio.gather(*tasks)

        # Масове оновлення Google Sheets
        if updates:
            cell_updates = []
            for value, row_num in updates:
                cell = rowcol_to_a1(row_num, confirm_col_number)
                cell_updates.append({'range': cell, 'values': [[value]]})
            sheet.batch_update([{
                'range': u['range'],
                'values': u['values']
            } for u in cell_updates])

    except Exception:
        logging.exception("Помилка при перевірці ТТН:")
        await asyncio.sleep(30)

async def periodic_check_new_ttns(interval=60):
    while True:
        await check_new_ttns()
        await asyncio.sleep(interval)
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(periodic_check_new_ttns())
    executor.start_polling(dp, skip_updates=True)
