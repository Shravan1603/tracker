import sqlite3

# Initialize DB
def init_db():
    conn = sqlite3.connect('2.db', check_same_thread=False)
    c = conn.cursor()
    # Create tables if they don't exist
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    password TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    topic TEXT,
                    subtopics TEXT,
                    due_date TEXT,
                    status TEXT,
                    priority TEXT,
                    progress INTEGER,
                    category TEXT,
                    recurrence TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS slot (
                    id INTEGER ,
                    date TEXT PRIMARY KEY,
                    slot TEXT 
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS schedule (
                    id INTEGER PRIMARY KEY,
                    date TEXT,
                    slot TEXT,
                    task_id INTEGER,
                    subtopics TEXT,  -- Add this column
                    FOREIGN KEY(task_id) REFERENCES tasks(id)
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS time_logs (
                    id INTEGER PRIMARY KEY,
                    task_id INTEGER,
                    start_time TEXT,
                    end_time TEXT,
                    time_spent INTEGER,  -- Time spent in seconds
                    FOREIGN KEY(task_id) REFERENCES tasks(id)
                )''')
    conn.commit()
    
    return conn

