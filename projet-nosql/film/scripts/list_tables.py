import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'film.settings')
import sys
# Ensure project root is on sys.path so the `film` package imports correctly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

import django
django.setup()
from django.db import connection
print(connection.introspection.table_names())
