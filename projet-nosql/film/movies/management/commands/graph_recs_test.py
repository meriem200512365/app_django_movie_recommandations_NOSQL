from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from movies.db_backends import get_neo4j_driver
from movies.models import Movie

class Command(BaseCommand):
    help = 'Run the graph recommendation query for a user and print recommended movies'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=int, required=True, help='User ID to test')

    def handle(self, *args, **options):
        uid = options['user']
        try:
            drv = get_neo4j_driver()
        except Exception as e:
            self.stderr.write(f'Neo4j driver error: {e}')
            return
        query = (
            "MATCH (u:User {user_id:$uid})-[:LIKED]->(:Movie)<-[:LIKED]-(other:User)-[:LIKED]->(rec:Movie) "
            "WHERE NOT (u)-[:LIKED]->(rec) "
            "RETURN rec.movie_id AS movie_id, count(*) AS score ORDER BY score DESC LIMIT 20"
        )
        try:
            with drv.session() as s:
                res = s.run(query, uid=uid)
                movie_ids = [record['movie_id'] for record in res]
            if not movie_ids:
                self.stdout.write('No graph recommendations found for user {}'.format(uid))
                return
            movies = Movie.objects.filter(pk__in=movie_ids)
            movies_ordered = sorted(movies, key=lambda m: movie_ids.index(m.pk))
            for m in movies_ordered:
                self.stdout.write(f'{m.pk}: {m.title} ({m.year})')
        except Exception as e:
            self.stderr.write(f'Graph query failed: {e}')
        finally:
            try:
                drv.close()
            except Exception:
                pass
