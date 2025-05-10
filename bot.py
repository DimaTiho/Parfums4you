@dp.callback_query_handler(lambda c: c.data == "view_cart")
async def view_cart(call: types.CallbackQuery):
    uid = call.from_user.id
    cart = user_data.get(uid, {}).get("cart", {})
    if not cart:
        await call.message.answer("🛒 Ваш кошик порожній.")
        return
    msg = "🛒 Ваш кошик:\n"
    for i, (name, qty) in enumerate(cart.items(), 1):
        msg += f"{i}. {name} × {qty} шт\n"
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✏️ Змінити кількість", callback_data="edit_cart"),
        InlineKeyboardButton("❌ Очистити кошик", callback_data="clear_cart")
    )
    kb.add(
        InlineKeyboardButton("✅ Продовжити оформлення", callback_data="next_step"),
        InlineKeyboardButton("↩️ Назад", callback_data="order")
    )
    await call.message.answer(msg, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "clear_cart")
async def clear_cart(call: types.CallbackQuery):
    uid = call.from_user.id
    user_data.get(uid, {}).pop("cart", None)
    await call.message.answer("🗑 Кошик очищено.")
    await view_cart(call)

@dp.callback_query_handler(lambda c: c.data == "edit_cart")
async def edit_cart(call: types.CallbackQuery):
    uid = call.from_user.id
    cart = user_data.get(uid, {}).get("cart", {})
    if not cart:
        await call.message.answer("Кошик порожній.")
        return
    kb = InlineKeyboardMarkup(row_width=1)
    for item in cart:
        kb.add(InlineKeyboardButton(f"✏️ {item}", callback_data=f"edit_{item}"))
    kb.add(InlineKeyboardButton("↩️ Назад", callback_data="view_cart"))
    await call.message.answer("Оберіть позицію для редагування:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("edit_"))
async def prompt_edit_quantity(call: types.CallbackQuery):
    perfume = call.data[5:]
    user_data[call.from_user.id]["selected_edit"] = perfume
    await call.message.answer(f"✏️ Введіть нову кількість для '{perfume}':")

@dp.message_handler(lambda m: "selected_edit" in user_data.get(m.from_user.id, {}))
async def save_edited_quantity(message: types.Message):
    uid = message.from_user.id
    perfume = user_data[uid].pop("selected_edit")
    if not message.text.isdigit():
        await message.answer("❗ Введи кількість числом")
        return
    qty = int(message.text)
    if qty <= 0:
        user_data[uid]["cart"].pop(perfume, None)
        await message.answer(f"❌ '{perfume}' видалено з кошика.")
    else:
        user_data[uid]["cart"][perfume] = qty
        await message.answer(f"✏️ Кількість '{perfume}' змінено на {qty}.")
    await view_cart(types.CallbackQuery(from_user=message.from_user, message=message))

@dp.callback_query_handler(lambda c: c.data == "next_step")
async def ask_name(call: types.CallbackQuery):
    uid = call.from_user.id
    user_data[uid]["order"] = {}
    await call.message.answer("👤 Введіть ваше імʼя:")

@dp.message_handler(lambda m: "name" not in user_data.get(m.from_user.id, {}).get("order", {}))
async def get_name(message: types.Message):
    uid = message.from_user.id
    user_data[uid].setdefault("order", {})["name"] = message.text
    await message.answer("📞 Введіть номер телефону:")

@dp.message_handler(lambda m: "phone" not in user_data.get(m.from_user.id, {}).get("order", {}))
async def get_phone(message: types.Message):
    uid = message.from_user.id
    user_data[uid]["order"]["phone"] = message.text
    await message.answer("🏙 Введіть місто доставки:")

@dp.message_handler(lambda m: "city" not in user_data.get(m.from_user.id, {}).get("order", {}))
async def get_city(message: types.Message):
    uid = message.from_user.id
    user_data[uid]["order"]["city"] = message.text
    await message.answer("📦 Введіть адресу або номер відділення пошти:")

@dp.message_handler(lambda m: "address" not in user_data.get(m.from_user.id, {}).get("order", {}))
async def get_address(message: types.Message):
    uid = message.from_user.id
    user_data[uid]["order"]["address"] = message.text
    await confirm_order_prompt(uid, message)

async def confirm_order_prompt(uid, message):
    cart = user_data[uid].get("cart", {})
    order = user_data[uid].get("order", {})
    if not cart or not order:
        await message.answer("❗ Помилка: неповне замовлення.")
        return

    total = 0
    items_text = ""
    for name, qty in cart.items():
        price = perfume_prices.get(name, 200)
        line_total = price * qty
        total += line_total
        items_text += f"- {name} × {qty} шт — {line_total} грн\n"

    delivery_note = "🚚 Доставка: "
    if total >= FREE_DELIVERY_THRESHOLD:
        delivery_note += "Безкоштовна"
    else:
        delivery_note += f"{DELIVERY_COST} грн"
        total += DELIVERY_COST

    summary = (
        f"🔍 Підтвердження замовлення:\n\n"
        f"👤 Імʼя: {order['name']}\n"
        f"📞 Телефон: {order['phone']}\n"
        f"🏙 Місто: {order['city']}\n"
        f"📦 Адреса/відділення: {order['address']}\n\n"
        f"🛍 Замовлення:\n{items_text}"
        f"{delivery_note}\n"
        f"💰 Загальна сума: {total} грн"
    )

    await message.answer(summary + "\n\n✅ Замовлення прийнято! Очікуйте підтвердження.")
