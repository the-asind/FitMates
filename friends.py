from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from encryption import encrypt_number, decrypt_number
from translations import translations
from db import get_friends, accept_friend


def generate_referral_link(user_id):
    code = encrypt_number(user_id)
    return f"https://t.me/fitmatesbot?start={code}"


def handle_invite_code(invite_code, user_id):
    code = decrypt_number(invite_code)
    accept_friend(code, user_id)


async def add_friends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    friends = get_friends(user_id)
    referral_link = generate_referral_link(user_id)
    lang = context.user_data.get('lang', 'en')
    translation = translations[lang]
    if len(friends) == 0:
        friends_text = translation['no_friends'] + "\n\n" + translation['referral_link'] + referral_link
    else:
        friends_text = translation['your_friends'] + "\n" + "\n".join(friends) + "\n\n" + \
                       translation['referral_link'] + "\n<code>" + referral_link + "</code>"

    keyboard = [
        [InlineKeyboardButton(translation['go_to_profile'], callback_data="GO_PROFILE")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=friends_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
