from django.apps import AppConfig
import threading
import sys
import os


class MoviesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'movies'

    def ready(self):
        # Import signal handlers to enable automatic backend synchronization
        try:
            from . import signals  # noqa: F401
        except Exception:
            # keep startup resilient if signals fail
            print('Failed to import signals for auto-sync')
        # Run one-time initial sync when using `runserver` main process to bootstrap other DBs
        run_main = os.environ.get('RUN_MAIN')
        if 'runserver' in sys.argv and run_main in ('true', 'True', '1'):
            def _auto_sync():
                try:
                    import time
                    time.sleep(1)
                    from .management.commands.sync_helpers import sync_movies
                    sync_movies()
                except Exception as e:
                    # Log but don't raise to avoid blocking startup
                    print('Auto-sync failed:', e)

            t = threading.Thread(target=_auto_sync, daemon=True)
            t.start()
