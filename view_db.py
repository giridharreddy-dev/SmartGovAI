import sqlite3

conn = sqlite3.connect('feedback.db')
cursor = conn.cursor()

print("\n=== REQUESTS ===")
cursor.execute("SELECT * FROM requests ORDER BY id DESC")
for row in cursor.fetchall():
    print(f"ID:{row[0]} | Scheme:{row[1]} | Source:{row[2]} | Time:{row[3]}")

print("\n=== FEEDBACK with scheme names ===")
cursor.execute("""
    SELECT r.scheme_name, f.rating, f.comment, f.timestamp
    FROM feedback f
    JOIN requests r ON f.request_id = r.id
    ORDER BY f.timestamp DESC
""")
for row in cursor.fetchall():
    print(f"{row[0]} | Rating:{row[1]} | Comment:{row[2][:50]} | {row[3]}")

conn.close()
