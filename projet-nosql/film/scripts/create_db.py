import os
import sys
try:
    import MySQLdb
except Exception as e:
    print('MySQLdb import failed:', e)
    sys.exit(1)

DB_HOST = os.environ.get('DB_HOST','127.0.0.1')
DB_PORT = int(os.environ.get('DB_PORT','3306'))
DB_USER = os.environ.get('DB_USER','root')
DB_PASSWORD = os.environ.get('DB_PASSWORD','')
DB_NAME = os.environ.get('DB_NAME','film_db')

print('Connecting to MySQL on', DB_HOST, DB_PORT, 'as', DB_USER)
conn = MySQLdb.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, passwd=DB_PASSWORD)
conn.autocommit(True)
cur = conn.cursor()
cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
print('Created or verified database', DB_NAME)
cur.close()
conn.close()
