import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'film.settings')
import django
django.setup()

from movies.db_backends import get_neo4j_driver

try:
    drv = get_neo4j_driver()
except Exception as e:
    print('Failed to import or create Neo4j driver:', e)
    sys.exit(2)

try:
    with drv.session() as s:
        total = s.run('MATCH (n) RETURN count(n) AS c').single().get('c')
        movies = s.run("MATCH (m:Movie) RETURN count(m) AS c").single().get('c')
        users = s.run("MATCH (u:User) RETURN count(u) AS c").single().get('c')
        rels = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single().get('c')
    print(f'Neo4j reachable. Nodes total={total}, movies={movies}, users={users}, relationships={rels}')
    drv.close()
    sys.exit(0)
except Exception as e:
    print('Neo4j query failed or Neo4j not reachable:', e)
    try:
        drv.close()
    except Exception:
        pass
    sys.exit(3)