import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, ReplyKeyboardRemove
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
DELIVERY_COST = 70

# === Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
workbook = client.open(Parfums)
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

# === Ініціалізація бота ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
user_data = {}
# === Дані ===

perfumes = {
"Жіночі": [
        {"name": "Chanel Chance", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Dior J'adore", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Lancôme La Vie Est Belle", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "YSL Mon Paris", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"}
    ],
    "Чоловічі": [
        {"name": "Dior Sauvage", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Versace Eros", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Bleu de Chanel", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Paco Rabanne Invictus", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"}
    ],
    "Унісекс": [
        {"name": "Tom Ford Black Orchid", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Creed Aventus", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Molecule 01", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Byredo Gypsy Water", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"}
    ],
    "ТОП продаж": [
        {"name": "Dior Sauvage", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Chanel Chance", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"},
        {"name": "Tom Ford Black Orchid", "photo": "https://images.pexels.com/photos/965731/pexels-photo-965731.jpeg"}
    ]
}
# Ціни на парфуми

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
    photo_url = "https://fleurparfum.net.ua/images/blog/shleifovie-duhi-woman.jpg.pagespeed.ce.3PKNQ9Vn2Z.jpg"
    caption = (
        "🧴 *Ласкаво просимо до нашого ароматного світу!*\n\n"
        "🌺 У нашому магазині ви знайдете брендові жіночі, чоловічі та унісекс парфуми — обрані з любов'ю.\n"
        "💸 Ми пропонуємо найкращі ціни та щедрі знижки для нових і постійних клієнтів.\n"
        "🎁 Усі покупці можуть скористатися акціями та отримати приємні подарунки.\n"
        "🚚 Доставка по всій Україні. Безкоштовна — при замовленні від 500 грн.\n\n"
        "👇 Оберіть розділ нижче, щоб почати замовлення або переглянути наші пропозиції.")
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📦 Каталог парфумів", callback_data="show_perfumes"),
        InlineKeyboardButton("🔥 Акції та Бонуси", callback_data="promotions")
    )
    kb.add(
        InlineKeyboardButton("⭐ Знижка дня", callback_data="daily_deal"),
        InlineKeyboardButton("ℹ️ Як замовити?", callback_data="how_to_order")
    )
    kb.add(
        InlineKeyboardButton("💬 Відгуки", callback_data="reviews"),
        InlineKeyboardButton("📞 Зв'язок з менеджером", url="https://t.me/your_manager_username")
    )
    await message.answer_photo(photo=photo_url, caption=caption, parse_mode="Markdown", reply_markup=kb)

@dp.message_handler(commands=['start_old'])
async def start_old(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📦 Каталог парфумів", callback_data="show_perfumes"),
        InlineKeyboardButton("🔥 Акції / Знижки", callback_data="promotions")
    )
    kb.add(
        InlineKeyboardButton("ℹ️ Як замовити?", callback_data="how_to_order"),
        InlineKeyboardButton("💬 Відгуки", callback_data="reviews")
    )
    kb.add(
        InlineKeyboardButton("📞 Зв'язок з менеджером", url="https://t.me/your_manager_username")
    )
    await message.answer("🌿 Вітаємо! Натхнення у кожному ароматі.", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "show_perfumes")
async def choose_category(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("👨 Чоловічі", callback_data="cat_Чоловічі"),
        InlineKeyboardButton("👩 Жіночі", callback_data="cat_Жіночі")
    )
    kb.add(
        InlineKeyboardButton("🌿 Унісекс", callback_data="cat_Унісекс"),
        InlineKeyboardButton("🔝 ТОП продаж", callback_data="top_sales")
    )
    kb.add(InlineKeyboardButton("🔎 Знайти назву", callback_data="search_perfume"))
    kb.add(
        InlineKeyboardButton("↩️ Назад", callback_data="start"),
        InlineKeyboardButton("🏠 Головна", callback_data="start")
    )
    await call.message.answer("🎲 Оберіть категорію або пошук:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "search_perfume")
async def search_perfume_prompt(call: types.CallbackQuery):
    user_data.setdefault(call.from_user.id, {})["search_mode"] = True
    await call.message.answer("🔎 Введіть назву аромату для пошуку:")


@dp.message_handler(lambda m: user_data.get(m.from_user.id, {}).get("search_mode"))
async def perform_search(message: types.Message):
    query = message.text.lower()
    results = []
    for category in perfumes.values():
        for perfume in category:
            if query in perfume["name"].lower():
                results.append(perfume)

    if results:
        for p in results:
            caption = f"{p['name']} — {perfume_prices.get(p['name'], 200)} грн"
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton("➕ Додати до замовлення", callback_data=f"add_{p['name']}")
            )
            await message.answer_photo(p["photo"], caption=caption, reply_markup=kb)
    else:
        await message.answer("❌ Нічого не знайдено. Спробуйте іншу назву.")

    del user_data[message.from_user.id]["search_mode"]

@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))
async def show_perfumes(call: types.CallbackQuery):
    category = call.data[4:]
    selected = perfumes.get(category, [])
    for p in selected:
        caption = f"{p['name']} — {perfume_prices[p['name']]} грн"
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("➕ Додати до замовлення", callback_data=f"add_{p['name']}"))
        await call.message.answer_photo(photo=p["photo"], caption=caption, reply_markup=kb)

    nav_kb = InlineKeyboardMarkup(row_width=2)
    nav_kb.add(
        InlineKeyboardButton("↩️ Назад", callback_data="show_perfumes"),
        InlineKeyboardButton("🏠 Головна", callback_data="start")
    )
    await call.message.answer("⬅️ Оберіть іншу категорію або поверніться:", reply_markup=nav_kb)

@dp.callback_query_handler(lambda c: c.data.startswith("promo_"))
async def confirm_order_prompt(call: types.CallbackQuery):
    uid = call.from_user.id
    promo_key = call.data[6:]
    data = user_data.get(uid, {})

    if "cart" not in data or not data["cart"]:
        await call.message.answer("❗ Ваш кошик порожній.")
        return

    user_data[uid]["promotion"] = promo_key
    discount = promotions[promo_key]["discount"]

    cart = data["cart"]
    subtotal = sum(perfume_prices.get(name, 200) * qty for name, qty in cart.items())
    discount_text = ""
    discount_amount = 0

    if promo_key == "1+1=Подарунок":
        total_items = sum(cart.values())
        free_items = total_items // 3
        if free_items > 0:
            cheapest_price = min(perfume_prices.get(name, 200) for name in cart)
            discount_amount = cheapest_price * free_items
            discount_text = f"\n🎁 Акція '1+1=Подарунок': -{discount_amount} грн"
    elif promo_key == "Перший клієнт":
        discount_amount = subtotal * 0.10
        discount_text = f"\n🟢 Знижка 10%: -{int(discount_amount)} грн"
    elif promo_key == "Парфум дня":
        discount_amount = 20
        discount_text = f"\n🌟 Знижка на аромат дня: -{discount_amount} грн"
    elif promo_key == "Таємне слово":
        discount_amount = 15
        discount_text = f"\n🗝 Таємне слово: -{discount_amount} грн"

    total = subtotal - discount_amount

    if total < FREE_DELIVERY_THRESHOLD:
        total += DELIVERY_COST
        delivery_text = f"\n🚚 Доставка: +{DELIVERY_COST} грн"
    else:
        delivery_text = "\n🚚 Доставка: безкоштовно"

    items_list = "\n".join([f"{qty} × {name} — {perfume_prices.get(name, 200) * qty} грн" for name, qty in cart.items()])
    summary = f"🛍 Ваше замовлення:\n{items_list}\n\nСума: {subtotal} грн{discount_text}{delivery_text}\n\n💰 До оплати: {int(total)} грн"

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Підтвердити замовлення", callback_data="confirm_order"),
        InlineKeyboardButton("↩️ Назад", callback_data="view_cart")
    )
    await call.message.answer(summary, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "order")
async def start_order(call: types.CallbackQuery):
    user_data[call.from_user.id] = user_data.get(call.from_user.id, {})
    user_data[call.from_user.id]["cart"] = {}
    kb = InlineKeyboardMarkup(row_width=2)
    for cat in perfumes.values():
        for p in cat:
            kb.add(InlineKeyboardButton(f"➕ {p['name']}", callback_data=f"add_{p['name']}"))
    kb.add(InlineKeyboardButton("🛒 Переглянути кошик", callback_data="view_cart"))
    kb.add(InlineKeyboardButton("↩️ Назад", callback_data="show_perfumes"))
    await call.message.answer("Обери аромати, які хочеш додати до замовлення:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("add_"))
async def ask_quantity(call: types.CallbackQuery):
    perfume_name = call.data[4:]
    user_data[call.from_user.id]["selected_perfume"] = perfume_name
    await call.message.answer(f"Скільки одиниць '{perfume_name}' додати до замовлення?")

@dp.message_handler(lambda m: "selected_perfume" in user_data.get(m.from_user.id, {}))
async def save_quantity_to_cart(message: types.Message):
    if not message.text.isdigit():
        await message.answer("❗ Введи кількість числом.")
        return
    qty = int(message.text)
    uid = message.from_user.id
    perfume = user_data[uid].pop("selected_perfume")
    cart = user_data[uid].setdefault("cart", {})
    cart[perfume] = cart.get(perfume, 0) + qty
    await message.answer(f"✅ Додано {qty} × {perfume} до кошика.")
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ Додати ще", callback_data="order"),
        InlineKeyboardButton("🛒 Переглянути кошик", callback_data="view_cart")
    )
    kb.add(InlineKeyboardButton("↩️ Назад", callback_data="show_perfumes"))
    await message.answer("Оберіть наступну дію:", reply_markup=kb)
  
@dp.callback_query_handler(lambda c: c.data == "checkout")
async def start_checkout(call: types.CallbackQuery):
    uid = call.from_user.id
    if "cart" not in user_data.get(uid, {}):
        await call.message.answer("🛒 Ваш кошик порожній.")
        return
    user_data[uid]["step"] = "get_name"
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 На головну", callback_data="start"))
    await call.message.answer("🧑 Введіть ваше ім'я:")

@dp.message_handler(lambda m: "name" not in user_data.get(m.from_user.id, {}))
async def get_phone(message: types.Message):
    
    user_data[message.from_user.id]["name"] = message.text
    user_data[message.from_user.id]["step"] = "get_phone"
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 На головну", callback_data="start"))
    await message.answer("📞Номер телефону:", reply_markup=kb)

@dp.message_handler(lambda m: "phone" not in user_data.get(m.from_user.id, {}))
async def get_city(message: types.Message):
    if message.from_user.id not in user_data:
        await message.answer("⚠️ Будь ласка, почніть замовлення з /start або натисніть '📝 Замовити'")
        return
    user_data[message.from_user.id]["phone"] = message.text
    user_data[message.from_user.id]["step"] = "get_city"
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 На головну", callback_data="start"))
    await message.answer("🏙 Введіть місто, куди буде здійснена доставка:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data in ["delivery_address", "delivery_np"])
async def ask_for_address(call: types.CallbackQuery):
    method = "Адресна доставка" if call.data == "delivery_address"else "Нова Пошта"
    user_data[call.from_user.id]["delivery_method"] = method
    note = "📍 Введіть місто та повну адресу доставки:" if method == "Адресна доставка" else "🏤 Введіть місто та номер відділення НП:"
    await call.message.answer(note + "‼️ Перевірте уважно правильність даних перед підтвердженням.")

@dp.message_handler(lambda m: user_data.get(m.from_user.id, {}).get("step") == "get_city")
async def get_city(message: types.Message):
    uid = message.from_user.id
    user_data[uid]["city"] = message.text
    user_data[uid]["step"] = None  # або "get_delivery_method" якщо хочете уточнити
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📦 Нова Пошта", callback_data="delivery_np"),
        InlineKeyboardButton("✉️ Укрпошта", callback_data="delivery_ukr"),
    )
    kb.add(InlineKeyboardButton("🏠 Адресна доставка", callback_data="delivery_address"))
    kb.add(InlineKeyboardButton("🔙 На головну", callback_data="start"))
    await message.answer("📬Оберіть тип доставки:", reply_markup=kb)




@dp.callback_query_handler(lambda c: c.data.startswith("promo_"))
async def confirm_order_prompt(call: types.CallbackQuery):
    uid = call.from_user.id
    promo_key = call.data[6:]
    data = user_data.get(uid, {})
  
    if "cart" not in data or not data["cart"]:
        await call.message.answer("❗ Ваш кошик порожній.")
        return

    user_data[uid]["promotion"] = promo_key
    discount = promotions[promo_key]["discount"]
    
    # Підрахунок вартості
    subtotal = 0
    summary_lines = []
    for perfume, qty in data["cart"].items():
        price = perfume_prices.get(perfume, 200)
        line_total = max(0, price * qty - discount * qty)
        subtotal += line_total
        summary_lines.append(f"{perfume} × {qty} = {line_total:.2f} грн")
        subtotal += line_total
    # Знижка
    discount_value = 0
    if promo_key == "1+1=Подарунок":
        total_qty = sum(data["cart"].values())
        free_items = total_qty // 3
        discount_value = free_items * 200  # вартість одного аромату
    elif promo_key == "Перший клієнт":
        discount_value = subtotal * 0.10
    elif promo_key == "Парфум дня":
        discount_value = 20
    elif promo_key == "Таємне слово":
        discount_value = 15
    else:
        discount_amount = int(discount)
      

    delivery_fee = 0 if total_after_discount >= FREE_DELIVERY_THRESHOLD else DELIVERY_COST
    final_total = total_after_discount + delivery_fee

    # Збереження суми
    user_data[uid]["total"] = final_total

    promo_text = promotions[promo_key]["description"]
    summary = "\n".join(summary_lines)
    delivery_text = "🚚 Безкоштовна доставка" if delivery_fee == 0 else f"🚚 Доставка: {DELIVERY_COST} грн"
    final_msg = (
        f"🧾 *Підсумок замовлення:*\n\n"
        f"{summary}\n"
        f"💰 Сума: {subtotal} грн\n"
        f"🎁 Знижка ({promo_text}): -{discount_amount} грн\n"
        f"🚚 Доставка {delivery_text}\n"
        f"✅ *До сплати: {final_total} грн*\n\n"
        f"Підтвердити замовлення?"
    )

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Підтвердити замовлення", callback_data="confirm_order"),
        InlineKeyboardButton("🔙 Назад", callback_data="view_cart")
    )
    await call.message.answer(order_summary, parse_mode="Markdown", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data == "finalize_order")
async def finalize_order(call: types.CallbackQuery):
    uid = call.from_user.id
    data = user_data.get(uid, {})
    if not data:
        await call.message.answer("⚠️ Помилка! Дані замовлення не знайдені.")
        return

    # Зберігаємо в Google Sheets
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cart_summary = ", ".join([f"{k} × {v}" for k, v in data["cart"].items()])
    sheet.append_row([
        now,
        data.get("name", ""),
        data.get("phone", ""),
        data.get("city", ""),
        cart_summary,
        data.get("promotion", "Без знижки"),
        data.get("total", 0)
    ])
        
        

    for row in full_rows:
        sheet.append_row(row)

    analytics_sheet.update("B2", f"=COUNTA({sheet.title}!A2:A)")
    analytics_sheet.update("B3", f"=SUM({sheet.title}!G2:G)")
    analytics_sheet.update("B4", f"=SUM({sheet.title}!H2:H)")
    analytics_sheet.update("B5", f"=INDEX({sheet.title}!D2:D, MODE(MATCH({sheet.title}!D2:D, {sheet.title}!D2:D, 0)))")

    await call.message.answer("✅ Замовлення прийнято! Очікуйте на дзвінок або SMS.",reply_markup=kb)
    user_data.pop(uid, None)
                              
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

@dp.callback_query_handler(lambda c: c.data == "view_cart")
async def view_cart(call: types.CallbackQuery):
    uid = call.from_user.id
    cart = user_data.get(uid, {}).get("cart", {})
    if not cart:
        await call.message.answer("🛒 Кошик порожній.")
        return

    total = 0
    lines = ["🛍 *Ваш кошик:*"]
    for perfume, qty in cart.items():
        price = perfume_prices.get(perfume, 200)
        sum_price = qty * price
        total += sum_price
        lines.append(f"• {perfume} — {qty} шт × {price} грн = {sum_price} грн")

    delivery_note = "🚚 Доставка: Безкоштовна" if total >= FREE_DELIVERY_THRESHOLD else f"🚚 Доставка: +{DELIVERY_COST} грн"
    discount_key = user_data.get(uid, {}).get("promotion", "Без знижки")
    promo_desc = promotions.get(discount_key, {}).get("description", "Без акції")

    lines.append(f"💰 Підсумок: {total} грн")
    lines.append(delivery_note)
    lines.append(f"🎁 Акція/Бонус: {discount_key} ({promo_desc})")

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Оформити замовлення", callback_data="start_checkout"),
        InlineKeyboardButton("♻️ Очистити кошик", callback_data="clear_cart")
    )
    kb.add(
        InlineKeyboardButton("↩️ Назад", callback_data="show_perfumes"),
        InlineKeyboardButton("🏠 Головна", callback_data="start")
    )
    await call.message.answer("".join(lines), parse_mode="Markdown", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data == "clear_cart")
async def clear_cart(call: types.CallbackQuery):
    uid = call.from_user.id
    if uid in user_data:
        user_data[uid]["cart"] = {}
    await call.message.answer("🧹 Кошик очищено.")


@dp.callback_query_handler(lambda c: c.data == "start_checkout")
async def start_checkout(call: types.CallbackQuery):
    uid = call.from_user.id
    if uid not in user_data or not user_data[uid].get("cart"):
        await call.message.answer("❗ Ваш кошик порожній. Спочатку додайте товари.")
        return
    await call.message.answer("✍️ Введіть ім'я для оформлення замовлення:")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(notify_sent_orders())
    executor.start_polling(dp, skip_updates=True, loop=loop)
