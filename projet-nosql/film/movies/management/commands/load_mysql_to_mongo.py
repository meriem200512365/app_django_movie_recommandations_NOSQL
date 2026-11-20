from django.core.management.base import BaseCommand
from django.conf import settings
from movies.db_backends import get_mongo_db
from movies.models import Movie, Watchlist
from django.contrib.auth import get_user_model
from pymongo import UpdateOne

User = get_user_model()

class Command(BaseCommand):
    help = 'Bulk load Movies and Watchlist (from MySQL via Django ORM) into MongoDB for fast reads'

    def handle(self, *args, **options):
        try:
            db = get_mongo_db()
        except Exception as e:
            self.stderr.write(f'MongoDB connection failed: {e}')
            return

        movies_coll = db.movies
        watchlist_coll = db.watchlists

        # Bulk upsert movies
        ops = []
        for m in Movie.objects.all():
            doc = {
                'movie_id': int(m.pk),
                'title': m.title,
                'year': m.year,
                'duration': m.duration,
                'description': getattr(m, 'description', '') or '',
                'tags': getattr(m, 'tags', []) or [],
                'genres': getattr(m, 'genres', []) or [],
            }
            ops.append(UpdateOne({'movie_id': doc['movie_id']}, {'$set': doc}, upsert=True))
            if len(ops) >= 500:
                movies_coll.bulk_write(ops, ordered=False)
                ops = []
        if ops:
            movies_coll.bulk_write(ops, ordered=False)

        self.stdout.write(self.style.SUCCESS('Movies upserted into MongoDB'))

        # Bulk upsert watchlist entries: store per-user list for fast retrieval
        # We'll create documents like {user_id, username, watchlist: [movie_id,...]}
        users_ops = []
        for u in User.objects.all():
            movie_ids = list(Watchlist.objects.filter(user=u).values_list('movie_id', flat=True))
            users_ops.append(UpdateOne({'user_id': int(u.pk)}, {'$set': {'user_id': int(u.pk), 'username': u.username, 'watchlist': [int(x) for x in movie_ids]}}, upsert=True))
            if len(users_ops) >= 200:
                watchlist_coll.bulk_write(users_ops, ordered=False)
                users_ops = []
        if users_ops:
            watchlist_coll.bulk_write(users_ops, ordered=False)

        self.stdout.write(self.style.SUCCESS('Watchlist upserted into MongoDB'))
        self.stdout.write(self.style.SUCCESS('Load complete'))
