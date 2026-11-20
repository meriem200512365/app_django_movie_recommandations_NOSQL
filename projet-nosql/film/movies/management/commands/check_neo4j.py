from django.core.management.base import BaseCommand
from movies.db_backends import get_neo4j_driver

class Command(BaseCommand):
    help = 'Check Neo4j connectivity and print basic node/relationship counts'

    def handle(self, *args, **options):
        try:
            drv = get_neo4j_driver()
        except Exception as e:
            self.stderr.write(f'Failed to create Neo4j driver: {e}')
            return
        try:
            with drv.session() as s:
                total = s.run('MATCH (n) RETURN count(n) AS c').single().get('c')
                movies = s.run("MATCH (m:Movie) RETURN count(m) AS c").single().get('c')
                users = s.run("MATCH (u:User) RETURN count(u) AS c").single().get('c')
                rels = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single().get('c')
            self.stdout.write(f'Neo4j reachable. Nodes total={total}, movies={movies}, users={users}, relationships={rels}')
        except Exception as e:
            self.stderr.write(f'Neo4j query failed or Neo4j not reachable: {e}')
        finally:
            try:
                drv.close()
            except Exception:
                pass
