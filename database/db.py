import sqlite3

db_file = "database/AI_birthday_frames_info_v2.db"

connection = sqlite3.connect(db_file)

cursor = connection.cursor()

create_table_sql = """
CREATE TABLE IF NOT EXISTS frame_data (
    frame_id INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_x_start INTEGER,
    frame_x_end INTEGER,
    frame_y INTEGER,
    frame_text_color INTEGER,
    frame_image_path TEXT,
    gender TEXT  -- New "gender" column
);
"""

cursor.execute(create_table_sql)

connection.commit()
connection.close()

print("Database and table created successfully.")