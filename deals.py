# handlers/deals.py
"""Сделочный флоу."""

import bot_core
import bot_ui
from bot_lang import get_text

# Предполагаем, что функции инициализации лежат в system.py. 
# Если это не так, поменяй .system на нужный модуль (например, .profile)
from .system import (
    _is_team_admin_or_owner, 
    _audit_profit_decision,
    init_user,
    update_user_activity
)


@bot_core.bot.callback_query_handler(
    func=lambda c: c.data and c.data.startswith('prf_accept:')
)
def handle_profit_accept(call):
    user_id = call.from_user.id
    if not _is_team_admin_or_owner(user_id):
        bot_core.bot.answer_callback_query(
            call.id, "Только для admin команды.", show_alert=True
        )
        return
    deal_id = call.data.split(':', 1)[1]
    deal = bot_core.deals.get(deal_id)
    if not deal:
        bot_core.bot.answer_callback_query(
            call.id, "Сделка не найдена.", show_alert=True
        )
        return
    proposal = deal.get('profit_proposal') or {}
    auto_profit = proposal.get('auto_profit_ton')
    if auto_profit is None:
        bot_core.bot.answer_callback_query(
            call.id, "Авто-профит не посчитан, выбери «Ввести».",
            show_alert=True
        )
        return
    if not bot_core.finalize_profit_decision(deal_id, user_id, 'accepted', auto_profit):
        bot_core.bot.answer_callback_query(
            call.id, "Решение по этой сделке уже принято.", show_alert=True
        )
        return
    try:
        bot_core.bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=None
        )
    except Exception:
        pass
    bot_core.bot.answer_callback_query(call.id, f"✅ Принято: {auto_profit} TON")
    _audit_profit_decision(deal_id, user_id, "✅ Принято (auto)", auto_profit)


@bot_core.bot.callback_query_handler(
    func=lambda c: c.data and c.data.startswith('prf_zero:')
)
def handle_profit_zero(call):
    user_id = call.from_user.id
    if not _is_team_admin_or_owner(user_id):
        bot_core.bot.answer_callback_query(
            call.id, "Только для admin команды.", show_alert=True
        )
        return
    deal_id = call.data.split(':', 1)[1]
    if deal_id not in bot_core.deals:
        bot_core.bot.answer_callback_query(
            call.id, "Сделка не найдена.", show_alert=True
        )
        return
    if not bot_core.finalize_profit_decision(deal_id, user_id, 'zero', 0.0):
        bot_core.bot.answer_callback_query(
            call.id, "Решение уже принято.", show_alert=True
        )
        return
    try:
        bot_core.bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=None
        )
    except Exception:
        pass
    bot_core.bot.answer_callback_query(call.id, "🚫 Без профита")
    _audit_profit_decision(deal_id, user_id, "🚫 Без профита", 0.0)


@bot_core.bot.callback_query_handler(
    func=lambda c: c.data and c.data.startswith('prf_manual:')
)
def handle_profit_manual(call):
    """Запрашиваем у admin ввод суммы профита текстом."""
    user_id = call.from_user.id
    if not _is_team_admin_or_owner(user_id):
        bot_core.bot.answer_callback_query(
            call.id, "Только для admin команды.", show_alert=True
        )
        return
    deal_id = call.data.split(':', 1)[1]
    deal = bot_core.deals.get(deal_id)
    if not deal:
        bot_core.bot.answer_callback_query(
            call.id, "Сделка не найдена.", show_alert=True
        )
        return
    if (deal.get('profit_decision') or 'pending') != 'pending':
        bot_core.bot.answer_callback_query(
            call.id, "Решение уже принято.", show_alert=True
        )
        return
        
    init_user(user_id)
    bot_core.users[user_id]['awaiting_profit_input'] = deal_id
    bot_core.save_data()
    try:
        bot_core.bot.send_message(
            call.message.chat.id,
            f"✏️ Введи сумму профита по сделке <code>#{deal_id[:8]}</code> "
            "в TON (например <code>12.5</code> или <code>0</code>).\n\n"
            "Отмена — /cancel_profit_input",
            parse_mode='HTML',
        )
    except Exception as e:
        bot_core.logger.exception("profit_manual prompt failed: %s", e)
    bot_core.bot.answer_callback_query(call.id)


@bot_core.bot.message_handler(commands=['cancel_profit_input'])
def handle_cancel_profit_input(message):
    user_id = message.from_user.id
    if user_id in bot_core.users and bot_core.users[user_id].get('awaiting_profit_input'):
        bot_core.users[user_id]['awaiting_profit_input'] = None
        bot_core.save_data()
        bot_core.bot.reply_to(message, "Окей, отменил ввод профита.")


@bot_core.bot.message_handler(func=lambda m: bool(
    m.from_user and m.from_user.id in bot_core.users
    and bot_core.users[m.from_user.id].get('awaiting_profit_input')
))
def handle_profit_input_message(message):
    """Ловим число от admin после нажатия «✏️ Ввести»."""
    user_id = message.from_user.id
    if not _is_team_admin_or_owner(user_id):
        bot_core.users[user_id]['awaiting_profit_input'] = None
        bot_core.save_data()
        return
    deal_id = bot_core.users[user_id].get('awaiting_profit_input')
    if not deal_id or deal_id not in bot_core.deals:
        bot_core.users[user_id]['awaiting_profit_input'] = None
        bot_core.save_data()
        bot_core.bot.reply_to(message, "Сделки уже нет — отменяю ввод.")
        return
    raw = (message.text or '').strip().replace(',', '.')
    try:
        value = float(raw)
    except ValueError:
        bot_core.bot.reply_to(
            message,
            "Это не число. Введи цифрами, например <code>12.5</code>",
            parse_mode='HTML'
        )
        return
    if value < 0:
        bot_core.bot.reply_to(message, "Профит не может быть отрицательным.")
        return

    deal = bot_core.deals[deal_id]
    deal_amount = deal.get('amount') or 0
    if (deal.get('currency') or '').upper() == 'TON' and value > deal_amount * 50:
        bot_core.bot.reply_to(
            message,
            f"⚠️ Подозрительно много ({value} TON). "
            f"Если точно — введи ещё раз: <code>{value} ok</code>",
            parse_mode='HTML'
        )
        return

    if not bot_core.finalize_profit_decision(deal_id, user_id, 'manual', value):
        bot_core.bot.reply_to(message, "Решение по сделке уже принято кем-то ещё.")
        bot_core.users[user_id]['awaiting_profit_input'] = None
        bot_core.save_data()
        return

    bot_core.users[user_id]['awaiting_profit_input'] = None
    bot_core.save_data()
    bot_core.bot.reply_to(
        message, f"✅ Профит зафиксирован: <b>{value}</b> TON", parse_mode='HTML'
    )
    _audit_profit_decision(deal_id, user_id, "✏️ Введено вручную", value)


@bot_core.bot.callback_query_handler(func=lambda call: call.data == 'warning_show')
def handle_warning_show(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if bot_core.is_user_blocked(user_id):
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'blocked_alert', bot_core.users), show_alert=True
        )
        return

    init_user(user_id)
    update_user_activity(user_id)

    user = bot_core.users[user_id]
    has_requisites = (
        user.get('ton_wallet', 'Не указан') != 'Не указан' or
        user.get('card_details', 'Не указана') != 'Не указана' or
        user.get('phone_number', 'Не указан') != 'Не указан' or
        user.get('usdt_wallet', 'Не указан') != 'Не указан'
    )

    if not has_requisites:
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'no_requisites_alert', bot_core.users),
            show_alert=True
        )
        wallet_text = get_text(user_id, 'bind_requisites', bot_core.users)
        bot_ui.send_photo_message(
            chat_id, message_id, wallet_text, bot_ui.wallet_menu_keyboard(user_id)
        )
        return

    create_text = get_text(user_id, 'create_deal_text', bot_core.users)
    bot_ui.send_photo_message(
        chat_id, message_id, create_text, bot_ui.create_deal_keyboard(user_id)
    )
    bot_core.bot.answer_callback_query(call.id)


@bot_core.bot.callback_query_handler(
    func=lambda call: call.data.startswith('admin_complete_deal_')
)
def handle_admin_complete_deal(call):
    user_id = call.from_user.id
    if not bot_core.can_complete_deal_with_profit(user_id):
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'admin_complete_only', bot_core.users),
            show_alert=True
        )
        return

    deal_id = call.data.split('_')[3]
    if deal_id not in bot_core.deals:
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'deal_not_found', bot_core.users), show_alert=True
        )
        return

    deal = bot_core.deals[deal_id]
    if deal.get('status') != 'paid':
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'deal_not_paid', bot_core.users), show_alert=True
        )
        return

    bot_core.ask_admin_for_scam_info(deal_id, user_id)


@bot_core.bot.callback_query_handler(
    func=lambda call: call.data.startswith('admin_confirm_item_')
)
def handle_admin_confirm_item(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if not bot_core.can_confirm_item_receipt(user_id):
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'admin_confirm_only', bot_core.users),
            show_alert=True
        )
        return

    deal_id = call.data.split('_')[3]
    if deal_id not in bot_core.deals:
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'deal_not_found', bot_core.users), show_alert=True
        )
        return

    deal = bot_core.deals[deal_id]
    seller_id = deal['seller_id']
    buyer_id = deal.get('buyer_id')

    if not buyer_id:
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'deal_no_buyer', bot_core.users), show_alert=True
        )
        return

    try:
        ws = bot_core.gift_watcher_status()
        watcher_alive = ws.get('thread_alive') and ws.get('started')
    except Exception:
        watcher_alive = False

    if watcher_alive:
        try:
            ok, missing = bot_core.check_gifts_received(deal_id)
        except Exception:
            ok, missing = True, []
        if not ok:
            received = deal.get('received_gifts') or []
            gift_links = deal.get('gift_links') or []
            warn_msg = (
                f"⚠️ <b>WARNING: расхождение по подаркам</b>\n"
                f"Сделка <code>#{deal_id[:8]}</code>\n"
                f"Админ <code>{user_id}</code> подтвердил получение, но\n"
                f"watcher зафиксировал только {len(received)}/{len(gift_links)} ссылок.\n\n"
                f"<b>Не сматчилось:</b>\n" +
                "\n".join(f"  • <code>{m}</code>" for m in missing[:20]) +
                "\n\n<i>Сделка закрывается — это лог для аудита.</i>"
            )
            try:
                bot_core.admin_forum_send(bot_core.ADMIN_TOPIC_DEALS_DISPUTES, warn_msg)
            except Exception as _e:
                bot_core.logger.warning("dispute warning failed: %s", _e)

    bot_core.log_activity(user_id, 'Подтвердил получение товара', deal_id)
    admin_text = f"""
✅ <b>ТОВАР ПОДТВЕРЖДЁН</b>

📋 <b>Сделка:</b> #{deal_id[:8]}
👤 <b>Продавец:</b> @{bot_core.users[seller_id]['username']}
👤 <b>Покупатель:</b> @{bot_core.users[buyer_id]['username']}
💰 <b>Сумма:</b> {deal['amount']} {deal['currency']}

<b>Товар успешно получен от менеджера.</b>
"""
    keyboard = bot_ui.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        bot_ui.InlineKeyboardButton(
            get_text(user_id, 'btn_deal_complete_profit', bot_core.users),
            callback_data=f'admin_complete_deal_{deal_id}'
        ),
        bot_ui.InlineKeyboardButton(
            get_text(user_id, 'btn_cancel', bot_core.users),
            callback_data=f'admin_view_deal_{deal_id}'
        )
    )
    bot_ui.send_photo_message(chat_id, message_id, admin_text, keyboard)

    s_txt = f"✅ <b>ТОВАР ПОДТВЕРЖДЁН</b>\n\n📋 Сделка: #{deal_id[:8]}\n" \
            f"👤 Покупатель: @{bot_core.users[buyer_id]['username']}\n\nАдмин подтвердил."
    b_txt = f"✅ <b>ТОВАР ПОДТВЕРЖДЁН</b>\n\n📋 Сделка: #{deal_id[:8]}\n" \
            f"👤 Продавец: @{bot_core.users[seller_id]['username']}\n\nАдмин подтвердил."
    bot_ui.send_photo_message(seller_id, None, s_txt)
    bot_ui.send_photo_message(buyer_id, None, b_txt)


@bot_core.bot.callback_query_handler(
    func=lambda call: call.data.startswith('admin_item_not_received_')
)
def handle_admin_item_not_received(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if not bot_core.is_admin_any_team(user_id):
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'access_denied', bot_core.users), show_alert=True
        )
        return

    deal_id = call.data.split('_')[4]
    if deal_id not in bot_core.deals:
        bot_core.bot.answer_callback_query(
            call.id, get_text(user_id, 'deal_not_found', bot_core.users), show_alert=True
        )
        return

    deal = bot_core.deals[deal_id]
    seller_id = deal['seller_id']
    buyer_id = deal.get('buyer_id')
    bot_core.log_activity(user_id, 'Товар не получен от менеджера', deal_id)

    admin_text = f"""
⚠️ <b>ТОВАР НЕ ПОЛУЧЕН</b>

📋 <b>Сделка:</b> #{deal_id[:8]}
👤 <b>Продавец:</b> @{bot_core.users[seller_id]['username']}
👤 <b>Покупатель:</b> @{bot_core.users[buyer_id]['username']}
💰 <b>Сумма:</b> {deal['amount']} {deal['currency']}

<b>Товар не получен от менеджера.</b>
"""
    keyboard = bot_ui.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        bot_ui.InlineKeyboardButton(
            get_text(user_id, 'btn_contact_manager', bot_core.users),
            url=f'https://t.me/{bot_core.MANAGER_USERNAME[1:]}'
        ),
        bot_ui.InlineKeyboardButton(
            get_text(user_id, 'btn_to_deal', bot_core.users),
            callback_data=f'admin_view_deal_{deal_id}'
        )
    )
    bot_ui.send_photo_message(chat_id, message_id, admin_text, keyboard)


@bot_core.bot.message_handler(commands=['start'])
def handle_start(message):
    try:
        _handle_start_impl(message)
    except Exception as _e:
        try:
            uid = message.from_user.id if message and message.from_user else '?'
            bot_core.logger.exception("/start crashed for user %s: %s", uid, _e)
        except Exception:
            pass
        try:
            bot_core.bot.send_message(
                message.chat.id, "⚠️ Временная ошибка. Попробуйте ещё раз."
            )
        except Exception:
            pass


def _handle_start_impl(message):
    user_id = message.from_user.id

    try:
        new_uname = message.from_user.username
        if new_uname and user_id in bot_core.users:
            cur = bot_core.users[user_id].get('username')
            if cur != new_uname:
                bot_core.users[user_id]['username'] = new_uname
                bot_core.save_data()
    except Exception as _e:
        bot_core.logger.debug("username refresh failed: %s", _e)

    if bot_core.is_user_blocked(user_id):
        bot_core.bot.send_message(
            message.chat.id, get_text(user_id, "bot_error", bot_core.users),
            parse_mode='HTML'
        )
        return

    referrer_id = None

    if len(message.text.split()) > 1:
        ref_or_deal = message.text.split()[1]

        if len(ref_or_deal) == 36 and ref_or_deal.count('-') == 4:
            deal_id = ref_or_deal

            if deal_id in bot_core.deals:
                deal = bot_core.deals[deal_id]

                if deal['seller_id'] == user_id:
                    bot_core.bot.send_message(
                        message.chat.id, get_text(user_id, 'error_own_deal', bot_core.users),
                        parse_mode='HTML'
                    )
                    return

                if deal.get('buyer_id') and deal['buyer_id'] != user_id:
                    bot_core.bot.send_message(
                        message.chat.id, get_text(user_id, 'error_deal_taken', bot_core.users),
                        parse_mode='HTML'
                    )
                    return

                init_user(user_id)

                if not deal.get('buyer_id'):
                    deal['buyer_id'] = user_id
                    bot_core.users[user_id]['current_deal'] = deal_id
                    bot_core.save_data()
                    bot_core.log_activity(user_id, 'Присоединился как покупатель', deal_id)
                    s_text = get_text(
                        deal['seller_id'], 'buyer_joined_seller', bot_core.users
                    ).format(
                        deal_id=deal_id[:8],
                        buyer=bot_core.users[user_id]['username'],
                        success_deals=bot_core.users[deal['seller_id']]['success_deals'],
                        manager=bot_core.MANAGER_USERNAME
                    )
                    bot_ui.send_photo_message(deal['seller_id'], None, s_text)

                b_text = get_text(user_id, 'buyer_joined_buyer', bot_core.users).format(
                    deal_id=deal_id[:8],
                    seller=bot_core.users[deal['seller_id']]['username'],
                    success_deals=bot_core.users[deal['seller_id']]['success_deals'],
                    manager=bot_core.MANAGER_USERNAME,
                    description=deal['description'],
                    amount=deal['amount'],
                    currency=deal['currency']
                )
                keyboard = bot_ui.InlineKeyboardMarkup(row_width=1)
                keyboard.add(
                    bot_ui.InlineKeyboardButton(
                        get_text(user_id, 'btn_pay_balance', bot_core.users),
                        callback_data=f'pay_balance_{deal_id}'
                    ),
                    bot_ui.InlineKeyboardButton(
                        get_text(user_id, 'btn_open_dispute', bot_core.users),
                        callback_data=f'dispute_{deal_id}'
                    ),
                    bot_ui.InlineKeyboardButton(
                        get_text(user_id, 'btn_back_menu', bot_core.users),
                        callback_data='main_menu'
                    )
                )
                bot_ui.send_photo_message(user_id, None, b_text, keyboard)
                return
        else:
            try:
                referrer_id = int(ref_or_deal)
            except ValueError:
                referrer_id = None

    init_user(user_id, referrer_id)
    welcome_text, keyboard = bot_ui.main_menu(user_id)
    bot_ui.send_photo_message(message.chat.id, None, welcome_text, keyboard)