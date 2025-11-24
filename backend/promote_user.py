import sqlite3
import sys
db = r"d:\diploma\backend\chat.db"
email = sys.argv[1] if len(sys.argv) > 1 else "antonbabi@gmail.com"
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("UPDATE users SET is_admin = 1 WHERE email = ?", (email,))
conn.commit()
print(cur.rowcount, "rows updated")
conn.close()