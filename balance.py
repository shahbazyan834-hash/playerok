# handlers/balance.py
"""Финансовый флоу."""

from datetime import datetime
import bot_core
import bot_ui
from bot_lang import get_text


@bot_core.bot.callback_query_handler(func=lambda call: call.data == 'pay_verification_card')
def handle_pay_verification_card(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    bot_core.init_user(user_id)
    bot_core.update_user_activity(user_id)

    if bot_core.is_user_verified(user_id):
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'already_verified', bot_core.users), show_alert=True
        )
        return

    bot_core.users[user_id]['awaiting_verification_payment'] = True
    bot_core.users[user_id]['current_verification_method'] = 'card_ru'
    payment_text = get_text(user_id, 'verif_pay_card_msg', bot_core.users).format(
        price=bot_core.VERIFICATION_PRICE,
        details=bot_core.DEPOSIT_REQUISITES['card_ru']['details'],
    )
    keyboard = bot_ui.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        bot_ui.InlineKeyboardButton(
            get_text(user_id, 'btn_send_receipt', bot_core.users),
            callback_data='send_verification_receipt'
        ),
        bot_ui.InlineKeyboardButton(
            get_text(user_id, 'btn_cancel', bot_core.users),
            callback_data='verification_info'
        )
    )
    bot_ui.send_photo_message(chat_id, message_id, payment_text, keyboard)
    bot_core.bot.answer_callback_query(call.id)


@bot_core.bot.callback_query_handler(func=lambda call: call.data == 'pay_verification_usdt')
def handle_pay_verification_usdt(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    bot_core.init_user(user_id)
    bot_core.update_user_activity(user_id)
    if bot_core.is_user_verified(user_id):
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'already_verified', bot_core.users), show_alert=True
        )
        return

    bot_core.users[user_id]['awaiting_verification_payment'] = True
    bot_core.users[user_id]['current_verification_method'] = 'crypto_usdt'
    payment_text = get_text(user_id, 'verif_pay_usdt_msg', bot_core.users).format(
        price=bot_core.VERIFICATION_PRICE_USDT,
        details=bot_core.DEPOSIT_REQUISITES['crypto_usdt']['details'],
    )
    keyboard = bot_ui.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        bot_ui.InlineKeyboardButton(
            get_text(user_id, 'btn_send_receipt', bot_core.users),
            callback_data='send_verification_receipt'
        ),
        bot_ui.InlineKeyboardButton(
            get_text(user_id, 'btn_cancel', bot_core.users),
            callback_data='verification_info'
        )
    )
    bot_ui.send_photo_message(chat_id, message_id, payment_text, keyboard)
    bot_core.bot.answer_callback_query(call.id)


def _verification_pay_simple(call, method: str, price: float, currency: str,
                             stars_layout: bool = False) -> None:
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    bot_core.init_user(user_id)
    bot_core.update_user_activity(user_id)
    if bot_core.is_user_verified(user_id):
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'already_verified', bot_core.users), show_alert=True
        )
        return

    bot_core.users[user_id]['awaiting_verification_payment'] = True
    bot_core.users[user_id]['current_verification_method'] = method

    key = 'verif_pay_stars_msg' if stars_layout else 'verif_pay_simple_msg'
    payment_text = get_text(user_id, key, bot_core.users).format(
        price=price, currency=currency, method=currency,
    )

    keyboard = bot_ui.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        bot_ui.InlineKeyboardButton(
            get_text(user_id, 'btn_send_receipt', bot_core.users),
            callback_data='send_verification_receipt'
        ),
        bot_ui.InlineKeyboardButton(
            get_text(user_id, 'btn_support', bot_core.users),
            url='https://t.me/your_support'
        ),
    )
    keyboard.add(
        bot_ui.InlineKeyboardButton(
            get_text(user_id, 'btn_cancel', bot_core.users),
            callback_data='verification_info'
        ),
    )
    bot_ui.send_photo_message(chat_id, message_id, payment_text, keyboard)
    bot_core.bot.answer_callback_query(call.id)


@bot_core.bot.callback_query_handler(func=lambda call: call.data == 'pay_verification_kzt')
def handle_pay_verification_kzt(call):
    _verification_pay_simple(call, 'kzt', bot_core.VERIFICATION_PRICE_KZT, 'KZT')


@bot_core.bot.callback_query_handler(func=lambda call: call.data == 'pay_verification_byn')
def handle_pay_verification_byn(call):
    _verification_pay_simple(call, 'byn', bot_core.VERIFICATION_PRICE_BYN, 'BYN')


@bot_core.bot.callback_query_handler(func=lambda call: call.data == 'pay_verification_stars')
def handle_pay_verification_stars(call):
    _verification_pay_simple(
        call, 'stars', bot_core.VERIFICATION_PRICE_STARS, 'Stars', stars_layout=True
    )


@bot_core.bot.callback_query_handler(func=lambda call: call.data == 'send_verification_receipt')
def handle_send_verification_receipt(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    bot_core.init_user(user_id)
    bot_core.update_user_activity(user_id)

    if not bot_core.users[user_id].get('awaiting_verification_payment'):
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'choose_payment_first', bot_core.users),
            show_alert=True
        )
        return

    bot_core.users[user_id]['awaiting_deposit_receipt'] = True
    bot_core.users[user_id]['receipt_type'] = 'verification'
    receipt_text = """
📤 <b>ОТПРАВКА ЧЕКА НА ВЕРИФИКАЦИЮ</b>

<b>Отправьте фото или документ с подтверждением перевода.</b>
"""
    keyboard = bot_ui.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        bot_ui.InlineKeyboardButton(
            get_text(user_id, 'btn_cancel', bot_core.users),
            callback_data='verification_info'
        )
    )
    bot_ui.send_photo_message(chat_id, message_id, receipt_text, keyboard)
    bot_core.bot.answer_callback_query(call.id)


@bot_core.bot.callback_query_handler(func=lambda call: call.data == 'withdraw_balance')
def handle_withdraw_balance(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    bot_core.init_user(user_id)
    bot_core.update_user_activity(user_id)
    bot_core.users[user_id]['awaiting_balance_withdrawal'] = True

    bot_core.schedule_balance_withdrawal_check(user_id)
    text, keyboard = bot_ui.withdraw_balance_menu(user_id)
    bot_ui.send_photo_message(chat_id, message_id, text, keyboard)


@bot_core.bot.callback_query_handler(func=lambda call: call.data == 'verification_info')
def handle_verification_info(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    bot_core.init_user(user_id)
    bot_core.update_user_activity(user_id)

    if bot_core.is_user_verified(user_id):
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'already_verified', bot_core.users), show_alert=True
        )
        return

    info_text = bot_ui.verification_info_text(user_id)
    bot_ui.send_photo_message(
        chat_id, message_id, info_text, bot_ui.verification_menu_keyboard(user_id)
    )


@bot_core.bot.callback_query_handler(func=lambda call: call.data == 'deposit_balance')
def handle_deposit_balance(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    bot_core.init_user(user_id)
    bot_core.update_user_activity(user_id)
    deposit_text = f"""{get_text(user_id, 'deposit_title', bot_core.users)}

{get_text(user_id, 'deposit_choose', bot_core.users)}
• {get_text(user_id, 'deposit_card_ru', bot_core.users)}
• {get_text(user_id, 'deposit_card_ua', bot_core.users)}
• {get_text(user_id, 'deposit_crypto', bot_core.users)}
• {get_text(user_id, 'deposit_stars', bot_core.users)}"""
    keyboard = bot_ui.deposit_method_keyboard(user_id)
    bot_ui.send_photo_message(chat_id, message_id, deposit_text, keyboard)


@bot_core.bot.callback_query_handler(func=lambda call: call.data.startswith('deposit_method_'))
def handle_deposit_method(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    bot_core.init_user(user_id)
    bot_core.update_user_activity(user_id)
    method = call.data.replace('deposit_method_', '')
    method_names = {
        'card_ru': 'Карта РФ', 'card_ua': 'Карта UA',
        'crypto': 'Криптовалюта', 'stars': 'Telegram Stars'
    }

    if method == 'crypto':
        bot_core.users[user_id]['awaiting_deposit_method'] = True
        bot_core.awaiting_deposit[user_id] = {'method': 'crypto', 'amount': None}
        crypto_text = """
💰 <b>ВЫБЕРИТЕ КРИПТОВАЛЮТУ</b>
"""
        keyboard = bot_ui.crypto_method_keyboard(user_id)
        bot_ui.send_photo_message(chat_id, message_id, crypto_text, keyboard)
        return

    requisites_text = bot_core.DEPOSIT_REQUISITES.get(method, {}).get('details', '')
    bot_core.users[user_id]['awaiting_deposit_amount'] = True
    bot_core.users[user_id]['awaiting_deposit_receipt'] = False
    bot_core.awaiting_deposit[user_id] = {'method': method, 'amount': None}
    currency = 'RUB' if method == 'card_ru' else 'UAH' if method == 'card_ua' else 'STARS'
    min_display = 400 if method == 'card_ua' else 100
    amount_text = f"""
💰 <b>ВВЕДИТЕ СУММУ ПОПОЛНЕНИЯ</b>
<b>Способ:</b> {method_names.get(method)}
<b>Валюта:</b> {currency}
{requisites_text}
• Минимальная сумма: {min_display} {currency}
"""
    keyboard = bot_ui.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        bot_ui.InlineKeyboardButton(
            get_text(user_id, "btn_cancel", bot_core.users), callback_data='my_profile'
        )
    )
    bot_ui.send_photo_message(chat_id, message_id, amount_text, keyboard)


@bot_core.bot.callback_query_handler(func=lambda call: call.data.startswith('deposit_crypto_'))
def handle_deposit_crypto(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    bot_core.init_user(user_id)
    bot_core.update_user_activity(user_id)
    crypto = call.data.replace('deposit_crypto_', '')
    currency_map = {
        'btc': 'BTC', 'eth': 'ETH', 'usdt': 'USDT',
        'ton': 'TON', 'bnb': 'BNB', 'sol': 'SOL'
    }
    currency = currency_map.get(crypto, 'USDT')
    method_key = f'crypto_{crypto}'

    requisites_text = bot_core.DEPOSIT_REQUISITES.get(method_key, {}).get('details', '')
    bot_core.users[user_id]['awaiting_deposit_amount'] = True
    bot_core.users[user_id]['awaiting_deposit_receipt'] = False
    bot_core.awaiting_deposit[user_id] = {'method': method_key, 'amount': None}
    amount_text = f"""
💰 <b>ВВЕДИТЕ СУММУ ПОПОЛНЕНИЯ</b>
<b>Валюта:</b> {currency}
{requisites_text}
"""
    keyboard = bot_ui.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        bot_ui.InlineKeyboardButton(
            get_text(user_id, "btn_cancel", bot_core.users), callback_data='my_profile'
        )
    )
    bot_ui.send_photo_message(chat_id, message_id, amount_text, keyboard)


@bot_core.bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_deposit_'))
def handle_confirm_deposit(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if not bot_core.is_admin_any_team(user_id):
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, "access_denied", bot_core.users), show_alert=True
        )
        return

    parts = call.data.split('_')
    target_user_id = int(parts[2])
    amount = float(parts[3])
    currency = parts[4]
    success, _ = bot_core.complete_deposit(user_id, target_user_id, amount, currency)

    if success:
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'deposit_approved', bot_core.users), show_alert=True
        )
        try:
            bot_core.bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
        except Exception:
            pass
    else:
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'deposit_error', bot_core.users), show_alert=True
        )


@bot_core.bot.callback_query_handler(func=lambda call: call.data.startswith('reject_deposit_'))
def handle_reject_deposit(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if not bot_core.is_admin_any_team(user_id):
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, "access_denied", bot_core.users), show_alert=True
        )
        return

    target_user_id = int(call.data.split('_')[2])
    bot_core.bot.answer_callback_query(
        call.id, get_text(user_id, 'deposit_declined', bot_core.users), show_alert=True
    )

    try:
        bot_core.bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
    except Exception:
        pass

    reject_text = f"""
❌ <b>ПОПОЛНЕНИЕ ОТКЛОНЕНО</b>
<b>Пользователь:</b> @{bot_core.users[target_user_id]['username']}
<b>Время:</b> {datetime.now().strftime("%d.%m.%Y %H:%M")}
"""
    bot_core.bot.send_message(chat_id, reject_text, parse_mode='HTML')

    try:
        bot_core.bot.send_message(
            target_user_id, get_text(target_user_id, 'deposit_declined_user', bot_core.users),
            parse_mode='HTML'
        )
    except Exception:
        pass
