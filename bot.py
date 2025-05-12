@dp.callback_query_handler(lambda c: c.data in ["nova_post", "ukr_post"], state=OrderStates.delivery_type)
async def get_post_service(callback: types.CallbackQuery, state: FSMContext):
    logging.info("📦 Обрано доставку: %s", callback.data)
    await state.update_data(post_service=callback.data)
    await callback.message.answer("📮 Введіть *номер відділення або поштомату* (тільки цифри):")
    await state.set_state(OrderStates.address_or_post)  # Явно встановлюємо стан
    logging.info("🔄 Стан встановлено: address_or_post")
    await callback.answer()

@dp.message_handler(state=OrderStates.address_or_post)
async def get_address_or_post(message: types.Message, state: FSMContext):
    logging.info("📩 Отримано адресу/відділення: %s", message.text)
    data = await state.get_data()
    delivery_type = data['delivery_type']

    if delivery_type == "delivery_post" and not message.text.isdigit():
        await message.answer("❗ Введіть лише номер відділення цифрами.")
        return

    if delivery_type == "delivery_post":
        post_service = data.get('post_service', '-')
        address_or_post = f"{post_service.upper()} {message.text}"
    else:
        address_or_post = message.text

    await state.update_data(address_or_post=address_or_post)

    # Далі: формування order_summary, підтвердження, запис у таблицю

    data = await state.get_data()
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
    cart = apply_third_item_discount(cart)

    text_items = ""
    total = 0
    for i, item in enumerate(cart, 1):
        text_items += f"{i}. {item['name']} — {item['price']} грн\n"
        total += item['price']

    discount = user_discounts.get(user_id, 0)
    final = total - discount

    order_summary = (
    f"📦 *Перевірте замовлення перед підтвердженням:*\n"
    f"👤 *ПІБ:* {data['name']}\n"
    f"📞 *Телефон:* {data['phone']}\n"
    f"🏙 *Місто:* {data['city']}\n"
    f"📍 *Адреса / Відділення:* {data['address_or_post']}\n"
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
