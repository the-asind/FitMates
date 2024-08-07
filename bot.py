import logging
import json
import os
from datetime import datetime, timedelta
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler
)
from db import init_db, add_user, get_user, get_leaderboard, update_user, get_today_tasks, add_task, mark_task_done

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

# Task details
TASKS = {
    "task_pushups": {"base": 10, "difficulty": 1.0},
    "task_squats": {"base": 15, "difficulty": 0.8},
    "task_diamond_pushups": {"base": 5, "difficulty": 1.2},
    "task_lunges": {"base": 10, "difficulty": 0.9},
    "task_plank": {"base": 30, "difficulty": 0.7, "is_time": True},
    "task_mountain_climbers": {"base": 20, "difficulty": 0.9},
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
    add_user(user_id, query.from_user.username, context.user_data['lang'])
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

    for i, task in enumerate(tasks):
        task_text = task[1]
        task_buttons = [
            [InlineKeyboardButton(translation['task_instruction'], callback_data=f"INSTRUCTION_{i}")],
            [InlineKeyboardButton(translation['task_done'], callback_data=f"DONE_{i}")]
        ]
        reply_markup = InlineKeyboardMarkup(task_buttons)
        await query.message.reply_text(text=task_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)


def create_daily_tasks(user_id):
    user = get_user(user_id)
    strength_modifier = user["strength_modifier"]
    tasks_keys = list(TASKS.keys())
    random.shuffle(tasks_keys)
    daily_tasks = tasks_keys[:3]

    for task_key in daily_tasks:
        task_info = TASKS[task_key]
        base_amount = task_info['base']
        difficulty = task_info['difficulty']
        is_time = task_info.get('is_time', False)
        amount = int(base_amount * difficulty * strength_modifier * random.uniform(0.8, 1.5))

        if is_time:
            task_text = translations[user["lang"]][task_key].format(time=amount)
        else:
            task_text = translations[user["lang"]][task_key].format(number=amount)

        add_task(user_id, task_text)


async def mark_task_done_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    task_index = int(query.data.split('_')[1])
    tasks = get_today_tasks(user_id)
    task_id = tasks[task_index][0]
    mark_task_done(user_id, task_id)
    update_user_points_and_streak(user_id)
    await send_profile(query, context, user_id)


def update_user_points_and_streak(user_id):
    user = get_user(user_id)
    streak = user[4]
    points = user[3]
    tasks_completed = user[5]

    streak_multiplier = 1 + 0.1 * streak
    tasks = get_today_tasks(user_id)
    for task in tasks:
        if task[3] == 'completed':
            points += int(10 * streak_multiplier)
            tasks_completed += 1

    streak += 1
    update_user(user_id, points, streak, tasks_completed)


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
                CallbackQueryHandler(mark_task_done_handler, pattern=f"^{MARK_TASK_DONE}_\\d+$"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("leaderboard", leaderboard))

    application.run_polling()


if __name__ == "__main__":
    main()
