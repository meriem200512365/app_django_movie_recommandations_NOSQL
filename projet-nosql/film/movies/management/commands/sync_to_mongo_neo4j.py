from django.core.management.base import BaseCommand
from django.conf import settings
from movies.models import Movie, Rating, Watchlist
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Sync movies to MongoDB and create basic graph data in Neo4j'

    def handle(self, *args, **options):
        # lazy imports so command can at least run without drivers
        try:
            from . import sync_helpers
        except Exception:
            # import from package
            from movies.management.commands import sync_helpers

        sync_helpers.sync_movies()
        self.stdout.write(self.style.SUCCESS('Sync complete'))
