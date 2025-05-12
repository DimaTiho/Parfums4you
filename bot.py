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

# Перевірка та створення листа "ТТН" для автоматичних сповіщень
try:
    ttn_sheet = workbook.worksheet("ТТН")
except:
    ttn_sheet = workbook.add_worksheet(title="ТТН", rows="100", cols="4")
    ttn_sheet.update("A1:D1", [["Чат ID", "Місто", "Адреса/Відділення", "Номер ТТН"]])

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
