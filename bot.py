import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from telebot.types import ForceReply

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)
spreadsheet = client.open("perfume")
worksheet = spreadsheet.sheet1

# Bot setup
bot = telebot.TeleBot("TOKEN")

# Data structures
user_cart = {}
user_discount = {}
user_state = {}
user_delivery = {}
discount_codes = {"SALE20": 0.2, "DISCOUNT15": 0.15}
user_phone = {}

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_cart[user_id] = []
    user_discount[user_id] = 0
    user_state[user_id] = None
    user_delivery[user_id] = "Самовивіз"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Категорії", "Кошик")
    markup.row("Знижка", "Доставка")
    markup.row("Оформити замовлення")

    bot.send_message(user_id, "Ласкаво просимо до нашого магазину парфумів! Оберіть дію:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Категорії")
def show_categories(message):
    user_id = message.chat.id
    rows = worksheet.get_all_values()
    categories = list(set(row[0] for row in rows if len(row) >= 3))

    markup = types.InlineKeyboardMarkup()
    for category in categories:
        markup.add(types.InlineKeyboardButton(text=category, callback_data=f"category_{category}"))

    bot.send_message(user_id, "Оберіть категорію:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("category_"))
def show_products(call):
    user_id = call.message.chat.id
    category = call.data.split("_", 1)[1]
    rows = worksheet.get_all_values()
    products = [row for row in rows if len(row) >= 3 and row[0] == category]

    if not products:
        bot.send_message(user_id, "У цій категорії наразі немає товарів.")
        return

    markup = types.InlineKeyboardMarkup()
    for product in products:
        markup.add(types.InlineKeyboardButton(text=product[1], callback_data=f"product_{product[1]}"))

    bot.send_message(user_id, f"Товари в категорії {category}:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("product_"))
def add_to_cart(call):
    user_id = call.message.chat.id
    product_name = call.data.split("_", 1)[1]
    rows = worksheet.get_all_values()

    for row in rows:
        if len(row) >= 3 and row[1] == product_name:
            try:
                price = float(row[2])
            except ValueError:
                bot.send_message(user_id, "Помилка у форматі ціни товару. Зверніться до менеджера.")
                return

            if user_id not in user_cart:
                user_cart[user_id] = []

            for item in user_cart[user_id]:
                if item["name"] == product_name:
                    if item["quantity"] < 99:
                        item["quantity"] += 1
                    else:
                        bot.answer_callback_query(call.id, "Досягнуто максимальної кількості для цього товару")
                    break
            else:
                user_cart[user_id].append({"name": product_name, "price": price, "quantity": 1})

            bot.answer_callback_query(call.id, text="Товар додано до кошика")
            return

    bot.send_message(user_id, "Товар не знайдено.")

@bot.message_handler(func=lambda message: message.text == "Кошик")
def view_cart(message):
    user_id = message.chat.id
    if not user_cart.get(user_id):
        bot.send_message(user_id, "Ваш кошик порожній.")
        return

    text = "Ваш кошик:\n"
    total = 0
    for item in user_cart[user_id]:
        item_total = item['price'] * item['quantity']
        text += f"{item['name']} - {item['quantity']} шт. - {item_total} грн\n"
        total += item_total

    discount = user_discount.get(user_id, 0)
    if discount:
        discount_amount = total * discount
        total -= discount_amount
        text += f"\nЗнижка: -{discount_amount} грн ({int(discount*100)}%)"

    text += f"\n\nСума до сплати: {total} грн"
    bot.send_message(user_id, text)

@bot.message_handler(func=lambda message: message.text == "Знижка")
def enter_discount(message):
    user_id = message.chat.id
    user_state[user_id] = "awaiting_discount"
    bot.send_message(user_id, "Введіть промокод:", reply_markup=ForceReply())

@bot.message_handler(func=lambda message: user_state.get(message.chat.id) == "awaiting_discount")
def apply_discount(message):
    user_id = message.chat.id
    promo_code = message.text.upper()
    if promo_code in discount_codes:
        if user_discount.get(user_id) == discount_codes[promo_code]:
            bot.send_message(user_id, "Цей промокод вже активований.")
        else:
            user_discount[user_id] = discount_codes[promo_code]
            bot.send_message(user_id, f"Знижка {int(discount_codes[promo_code]*100)}% застосована!")
    else:
        bot.send_message(user_id, "Невірний промокод.")
    user_state[user_id] = None

@bot.message_handler(func=lambda message: message.text == "Доставка")
def choose_delivery(message):
    user_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Самовивіз", "Нова Пошта")
    bot.send_message(user_id, "Оберіть спосіб доставки:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["Самовивіз", "Нова Пошта"])
def set_delivery(message):
    user_id = message.chat.id
    user_delivery[user_id] = message.text
    bot.send_message(user_id, f"Спосіб доставки обрано: {message.text}")

@bot.message_handler(func=lambda message: message.text == "Оформити замовлення")
def checkout(message):
    user_id = message.chat.id
    if not user_cart.get(user_id):
        bot.send_message(user_id, "Ваш кошик порожній. Додайте товари перед оформленням замовлення.")
        return
    if user_id not in user_phone:
        bot.send_message(user_id, "Будь ласка, спочатку надайте номер телефону. Напишіть його у форматі +380XXXXXXXXX")
        user_state[user_id] = "awaiting_phone"
        return

    order = user_cart[user_id]
    total = sum(item['price'] * item['quantity'] for item in order)
    discount = user_discount.get(user_id, 0)
    discount_amount = total * discount
    total -= discount_amount

    order_summary = "\n".join([f"{item['name']} - {item['quantity']} шт." for item in order])

    try:
        worksheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            message.from_user.username or "N/A",
            user_phone.get(user_id, "Невідомо"),
            user_delivery.get(user_id, "Самовивіз"),
            order_summary,
            f"{total} грн"
        ])
    except Exception as e:
        bot.send_message(user_id, f"Сталася помилка при збереженні замовлення: {e}")
        return

    bot.send_message(user_id, f"Дякуємо за замовлення! Загальна сума: {total} грн. Ми зв'яжемось з вами найближчим часом.")

    user_cart[user_id] = []
    user_discount[user_id] = 0
    user_state[user_id] = None
    user_delivery[user_id] = "Самовивіз"

@bot.message_handler(func=lambda message: user_state.get(message.chat.id) == "awaiting_phone")
def save_phone(message):
    user_id = message.chat.id
    user_phone[user_id] = message.text
    user_state[user_id] = None
    bot.send_message(user_id, "Номер телефону збережено. Тепер можете натиснути 'Оформити замовлення'.")

bot.polling(none_stop=True)
