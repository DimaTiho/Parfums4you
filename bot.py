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
