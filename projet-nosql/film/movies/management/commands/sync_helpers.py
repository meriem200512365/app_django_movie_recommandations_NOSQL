from django.conf import settings
from movies.db_backends import get_mongo_db, get_neo4j_driver
from movies.models import Movie, Rating, Watchlist
from django.contrib.auth import get_user_model
from movies.models import SyncLog
from django.utils import timezone
import time


def sync_movies():
    log = SyncLog.objects.create(status='started', message='Starting sync')
    start = time.time()
    # Sync to MongoDB
    try:
        db = get_mongo_db()
    except RuntimeError as e:
        db = None
        err = f'Skipping MongoDB sync: {e}'
        print(err)
        log.message += '\n' + err

    if db is not None:
        coll = db.movies
        # create text index for title and description
        try:
            coll.create_index([('title', 'text'), ('description', 'text')], default_language='english')
        except Exception:
            pass

    # Sync to Neo4j
    try:
        driver = get_neo4j_driver()
    except RuntimeError as e:
        driver = None
        err = f'Skipping Neo4j sync: {e}'
        print(err)
        log.message += '\n' + err

    User = get_user_model()

    try:
        # iterate movies
        for m in Movie.objects.all():
            doc = {
                'movie_id': int(m.pk),
                'title': m.title,
                'year': m.year,
                'duration': m.duration,
                    'description': getattr(m, 'description', None) or '',
                    'poster': getattr(m.poster, 'url', None),
                    'poster_url': getattr(m, 'poster_url', None) or '',
                'tags': [],
                'genres': [],
            }
            if db is not None:
                coll.update_one({'movie_id': doc['movie_id']}, {'$set': doc}, upsert=True)

            if driver is not None:
                with driver.session() as session:
                    session.run(
                        "MERGE (m:Movie {movie_id: $id}) SET m.title=$title, m.year=$year, m.duration=$duration, m.description=$description",
                        id=int(m.pk), title=m.title, year=m.year, duration=m.duration, description=doc['description']
                    )

        # create user nodes and relationships from ratings and watchlist
        if driver is not None:
            with driver.session() as session:
                # users
                for u in User.objects.all():
                    session.run("MERGE (u:User {user_id:$uid, username:$uname})", uid=int(u.pk), uname=u.username)
                # ratings -> LIKED if score>=7 else RATED
                for r in Rating.objects.all():
                    rel = 'LIKED' if r.score >= 7 else 'RATED'
                    session.run(
                        "MATCH (u:User {user_id:$uid}), (m:Movie {movie_id:$mid}) MERGE (u)-[rel:%s {score:$score}]->(m)" % rel,
                        uid=int(r.user_id), mid=int(r.movie_id), score=int(r.score)
                    )
                # watchlist -> WATCHED
                for w in Watchlist.objects.all():
                    session.run(
                        "MATCH (u:User {user_id:$uid}), (m:Movie {movie_id:$mid}) MERGE (u)-[:WATCHED]->(m)",
                        uid=int(w.user_id), mid=int(w.movie_id)
                    )

        status = 'success'
        msg = 'Sync completed successfully'
    except Exception as e:
        status = 'failed'
        msg = f'Sync failed: {e}'
        print(msg)
        log.message += '\n' + msg

    finally:
        if driver is not None:
            driver.close()
        end = time.time()
        log.status = status
        log.finished_at = timezone.now()
        log.duration_seconds = end - start
        if hasattr(log, 'message'):
            log.message = log.message
        else:
            log.message = msg
        log.save()
