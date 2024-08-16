import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
import random
from math import log

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler
)
from db import init_db, add_user, get_user, get_leaderboard, update_user, get_today_tasks, add_task, mark_task_done, \
    get_streak_timestamp, update_streak_timestamp

import re


class RemoveLinkFilter(logging.Filter):
    def filter(self, record):
        # Remove links starting with "https://" and ending with a space
        record.msg = re.sub(r'https:\S+ ', 'SECRET', record.msg)
        return True


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Add the filter to the logger
logger.addFilter(RemoveLinkFilter())

# Load translations
translations = {}
for lang in ['en', 'ru']:
    with open(f'translations/{lang}.json', 'r', encoding='utf-8') as f:
        translations[lang] = json.load(f)

# Stages and Callback data
SELECTING_LANGUAGE, SHOWING_PROFILE = range(2)
LANG_EN, LANG_RU, ADD_FRIENDS, GET_TASKS, MARK_TASK_DONE = range(5)

profile_message_query = None

# Task details
TASKS = {
    "task_pushups": {"base": 10, "difficulty": 1.0},
    "task_squats": {"base": 15, "difficulty": 0.8},
    "task_diamond_pushups": {"base": 5, "difficulty": 1.2},
    "task_lunges": {"base": 10, "difficulty": 0.9},
    "task_plank": {"base": 30, "difficulty": 0.7, "is_time": True},
    "task_mountain_climbers": {"base": 16, "difficulty": 0.9},
    "task_high_knees": {"base": 30, "difficulty": 0.5, "is_time": True},
    "task_jump_squats": {"base": 10, "difficulty": 1.1},
    "task_crunches": {"base": 20, "difficulty": 0.7},
    "task_burpees": {"base": 5, "difficulty": 1.5}
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send message on `/start`."""
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)

    keyboard = [
        [InlineKeyboardButton("🇺🇸 English", callback_data=str(LANG_EN))],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data=str(LANG_RU))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please choose your language\nПожалуйста, выберите ваш язык:',
                                    reply_markup=reply_markup)
    return SELECTING_LANGUAGE


async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = LANG_EN if query.data == str(LANG_EN) else LANG_RU
    context.user_data['lang'] = 'en' if lang == LANG_EN else 'ru'
    user_id = query.from_user.id
    add_user(user_id, query.from_user.first_name, context.user_data['lang'])
    await send_profile(query, context, user_id)
    return SHOWING_PROFILE


def get_user_rank(user_id):
    return "coming soon"


async def send_profile(query, context, user_id):
    user = get_user(user_id)
    lang = context.user_data.get('lang', 'en')
    translation = translations[lang]
    keyboard = [
        [InlineKeyboardButton(translation['add_friends'], callback_data=str(ADD_FRIENDS))],
        [InlineKeyboardButton(translation['get_tasks'], callback_data=str(GET_TASKS))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    profile_text = translation['profile'].format(
        name=user['username'],
        points=user['points'],
        streak=user['streak'],
        tasks_completed=user['tasks_completed'],
        rank=get_user_rank(user_id)
    )
    await query.edit_message_text(text=profile_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

    global profile_message_query
    profile_message_query = query


async def add_friends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Feature not implemented yet.")


async def get_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    tasks = get_today_tasks(user_id)
    if not tasks:
        create_daily_tasks(user_id)
        tasks = get_today_tasks(user_id)

    lang = context.user_data.get('lang', 'en')
    translation = translations[lang]

    for i, (task_code, number, created_at, task_index) in enumerate(tasks):
        task_text = translation[task_code].format(number=number)
        task_buttons = [
            [InlineKeyboardButton(translation['task_done'], callback_data=f"MARK_TASK_DONE_{i}")]
        ]
        reply_markup = InlineKeyboardMarkup(task_buttons)
        await query.message.reply_text(text=task_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


def create_daily_tasks(user_id):
    user = get_user(user_id)
    strength_modifier = user["strength_modifier"]
    tasks_keys = list(TASKS.keys())
    random.shuffle(tasks_keys)
    daily_tasks = tasks_keys[:3]

    for task_index, task_key in enumerate(daily_tasks):
        task_info = TASKS[task_key]
        base_amount = task_info['base']
        difficulty = task_info['difficulty']
        is_time = task_info.get('is_time', False)
        ran = random.uniform(0.8, 1.5)
        amount = int(base_amount * difficulty * strength_modifier * ran)
        multiplier = difficulty * strength_modifier * ran
        created_at = int(datetime.now().timestamp())

        add_task(user_id, task_key, amount, multiplier, created_at, task_index)


async def mark_task_done_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # Extract task index from callback data
    task_index = int(query.data.split('_')[3])

    user_id = query.from_user.id
    tasks = get_today_tasks(user_id)

    # Check if the task is already marked as done
    task = next((task for task in tasks if task[3] == task_index), None)

    if task is None:
        lang = context.user_data.get('lang', 'en')
        translation = translations[lang]
        await query.edit_message_text(translation['task_does_not_exist'])
        await asyncio.sleep(1)
        await query.message.delete()
        return

    task_code, number, multiplier, _ = task

    check_new_streak(user_id)

    # Get language and translation
    lang = context.user_data.get('lang', 'en')
    translation = translations[lang]

    score = await add_points_for_task(multiplier, task_code, user_id)

    # Mark task as done
    await query.edit_message_text(text=translation['task_completed'].format(score=score), parse_mode=ParseMode.HTML)

    # Mark task in db
    mark_task_done(user_id, task_code)

    global profile_message_query
    if profile_message_query is None:
        await send_profile(query, context, user_id)
    else:
        # noinspection PyTypeChecker
        await send_profile(profile_message_query, context, user_id)
        # delete message after 3 seconds
        await asyncio.sleep(3)
        await query.message.delete()


async def add_points_for_task(multiplier, task_code, user_id):
    # Add points of completed task to user
    user = get_user(user_id)
    task_info = TASKS[task_code]
    points = int(25 * multiplier * user['strength_modifier'] * (1 + (log(user['streak'] + 1, 1.1))))
    user['points'] += points
    user['tasks_completed'] += 1
    update_user(user_id, user['points'], user['streak'], user['tasks_completed'])
    return points


def check_new_streak(user_id):
    current_timestamp = int(datetime.now().timestamp())
    streak_timestamp = get_streak_timestamp(user_id)[0]

    if streak_timestamp is None:
        update_streak_timestamp(user_id, current_timestamp)
        return

    time_diff = current_timestamp - streak_timestamp

    if 86400 < time_diff < 172800 or streak_timestamp == 0:  # between 24 and 48 hours
        user = get_user(user_id)
        user['streak'] = 1
        update_user(user_id, user['points'], user['streak'], user['tasks_completed'])
    elif time_diff > 172800:  # more than 48 hours
        user = get_user(user_id)
        user['streak'] = 0
        update_user(user_id, user['points'], user['streak'], user['tasks_completed'])

    update_streak_timestamp(user_id, current_timestamp)


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    leaderboard = get_leaderboard()
    lang = context.user_data.get('lang', 'en')
    translation = translations[lang]
    leaderboard_text = translation['leaderboard_header'] + "\n"
    for rank, user in enumerate(leaderboard, start=1):
        leaderboard_text += f"{rank}. {user['username']} - {user['points']} points, streak: {user['streak']}\n"
    await update.message.reply_text(leaderboard_text)


def read_token_from_file(file_name='token'):
    try:
        with open(file_name, 'r') as file:
            token = file.read().strip()  # Читаем содержимое файла и удаляем лишние пробелы в начале и конце
        return token
    except FileNotFoundError:
        print(f"Файл '{file_name}' не найден.")
        return None


def main() -> None:
    """Run the bot."""
    init_db()
    token = read_token_from_file()
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_LANGUAGE: [
                CallbackQueryHandler(select_language, pattern=f"^{LANG_EN}$|^{LANG_RU}$"),
            ],
            SHOWING_PROFILE: [
                CallbackQueryHandler(add_friends, pattern=f"^{ADD_FRIENDS}$"),
                CallbackQueryHandler(get_tasks, pattern=f"^{GET_TASKS}$"),
                CallbackQueryHandler(mark_task_done_handler, pattern=f"^MARK_TASK_DONE_\\d+$"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("leaderboard", leaderboard))

    application.run_polling()


if __name__ == "__main__":
    main()
