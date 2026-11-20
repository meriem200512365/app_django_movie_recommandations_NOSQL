import os

# Optional: allow using PyMySQL as a drop-in replacement for MySQLdb
# Set environment variable USE_PYMYSQL=1 to enable.
if os.environ.get('USE_PYMYSQL', '1') == '1':
	try:
		import pymysql
		pymysql.install_as_MySQLdb()
	except Exception:
		# If PyMySQL isn't installed, we'll rely on mysqlclient instead.
		pass
