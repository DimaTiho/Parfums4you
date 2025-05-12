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
                sheet.update_cell(i, 13, "✅ надіслано")
                await asyncio.sleep(1)

        except Exception as e:
            logging.error(f"❌ Помилка в рядку {i}: {e}")

async def on_startup(_):
    asyncio.create_task(check_for_ttn_updates())

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)
