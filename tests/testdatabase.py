import unittest
import sqlite3
from db import init_db, add_user, get_user, update_user, add_task, mark_task_done, get_today_tasks, get_leaderboard


class TestDataBase(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect('fitness_bot.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('DELETE FROM users')
        self.cursor.execute('DELETE FROM tasks')
        self.conn.commit()
        init_db()

    def tearDown(self):
        self.conn.close()

    def test_add_user_creates_user(self):
        add_user(1, 'testuser', 'en')
        user = get_user(1)
        self.assertEqual(user['username'], 'testuser')
        self.assertEqual(user['lang'], 'en')
        self.assertEqual(user['points'], 0)
        self.assertEqual(user['streak'], 0)
        self.assertEqual(user['tasks_completed'], 0)
        self.assertEqual(user['strength_modifier'], 1.0)

    def test_get_user_returns_correct_user(self):
        add_user(2, 'anotheruser', 'fr')
        user = get_user(2)
        self.assertEqual(user['username'], 'anotheruser')
        self.assertEqual(user['lang'], 'fr')

    def test_update_user_updates_user(self):
        add_user(3, 'updateuser', 'es')
        update_user(3, 100, 5, 10)
        user = get_user(3)
        self.assertEqual(user['points'], 100)
        self.assertEqual(user['streak'], 5)
        self.assertEqual(user['tasks_completed'], 10)

    def test_add_task_creates_task(self):
        add_user(4, 'taskuser', 'de')
        add_task(4, 'task1', 1, 1.5, 1234567890)
        self.cursor.execute('SELECT * FROM tasks WHERE user_id = 4')
        task = self.cursor.fetchone()
        self.assertIsNotNone(task)
        self.assertEqual(task[1], 4)
        self.assertEqual(task[2], 'task1')
        self.assertEqual(task[3], 1)
        self.assertEqual(task[4], 1.5)
        self.assertEqual(task[5], 1234567890)
        self.assertEqual(task[6], 'pending')

    def test_mark_task_done_marks_task_as_completed(self):
        add_user(5, 'markuser', 'it')
        add_task(5, 'task2', 2, 2.0, 1234567891)
        self.cursor.execute('SELECT rowid FROM tasks WHERE user_id = 5 AND task_code = "task2"')
        task_id = self.cursor.fetchone()[0]
        mark_task_done(5, task_id)
        self.cursor.execute('SELECT status FROM tasks WHERE rowid = ?', (task_id,))
        status = self.cursor.fetchone()[0]
        self.assertEqual(status, 'completed')

    def test_get_today_tasks_returns_pending_tasks(self):
        add_user(6, 'todayuser', 'pt')
        add_task(6, 'task3', 3, 1.0, 1234567892)
        tasks = get_today_tasks(6)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0][0], 'task3')
        self.assertEqual(tasks[0][1], 3)
        self.assertEqual(tasks[0][2], 1.0)

    def test_get_leaderboard_returns_sorted_users(self):
        add_user(7, 'leader1', 'en')
        add_user(8, 'leader2', 'en')
        update_user(7, 200, 10, 20)
        update_user(8, 150, 5, 15)
        leaderboard = get_leaderboard()
        self.assertEqual(len(leaderboard), 2)
        self.assertEqual(leaderboard[0][0], 'leader1')
        self.assertEqual(leaderboard[0][1], 200)
        self.assertEqual(leaderboard[1][0], 'leader2')
        self.assertEqual(leaderboard[1][1], 150)


if __name__ == '__main__':
    unittest.main()