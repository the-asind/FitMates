import sqlite3

def init_db():
    with sqlite3.connect("fitness_bot.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            lang TEXT,
            points INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            tasks_completed INTEGER DEFAULT 0,
            strength_modifier REAL DEFAULT 1.0
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            user_id INTEGER,
            task TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

def add_user(user_id, username, lang):
    with sqlite3.connect("fitness_bot.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (id, username, lang) VALUES (?, ?, ?)", (user_id, username, lang))
        conn.commit()

def get_user(id):
    conn = sqlite3.connect('fitness_bot.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (id,))
    user = c.fetchone()
    conn.close()
    return {
        'user_id': user[0],
        'username': user[1],
        'lang': user[2],
        'points': user[3],
        'streak': user[4],
        'tasks_completed': user[5],
        'strength_modifier': user[6]
    }

def get_leaderboard():
    with sqlite3.connect("fitness_bot.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, points, streak FROM users ORDER BY points DESC")
        return cursor.fetchall()

def update_user(user_id, points, streak, tasks_completed):
    with sqlite3.connect("fitness_bot.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE users
        SET points = ?, streak = ?, tasks_completed = ?
        WHERE id = ?
        """, (points, streak, tasks_completed, user_id))
        conn.commit()

def get_today_tasks(user_id):
    with sqlite3.connect("fitness_bot.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM tasks
        WHERE user_id = ? AND DATE(created_at) = DATE('now')
        """, (user_id,))
        return cursor.fetchall()

def add_task(user_id, task):
    with sqlite3.connect("fitness_bot.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (user_id, task) VALUES (?, ?)", (user_id, task))
        conn.commit()

def mark_task_done(user_id, task_id):
    with sqlite3.connect("fitness_bot.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET status = 'completed' WHERE user_id = ? AND rowid = ?", (user_id, task_id))
        conn.commit()
