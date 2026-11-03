import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
with open("schema.sql") as f:
    sql = f.read()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
with conn, conn.cursor() as cur:
    cur.execute(sql)
    cur.execute("""SELECT table_name FROM information_schema.tables
                   WHERE table_schema = 'public' ORDER BY table_name;""")
    print("Tables created ", [r[0] for r in cur.fetchall()])
conn.close()