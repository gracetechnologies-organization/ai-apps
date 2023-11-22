import sqlite3

def get_db_cursor():
    db_file = "database/AI_birthday_frames_info_v2.db"
    conn = sqlite3.connect(db_file, check_same_thread=False)
    cursor = conn.cursor()
    return conn, cursor