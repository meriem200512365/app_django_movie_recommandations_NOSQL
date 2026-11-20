from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.conf import settings
from django.db import transaction
from .models import Movie, Rating, Review, Watchlist
from .db_backends import get_mongo_db, get_neo4j_driver
import traceback


def safe_get_mongo():
    try:
        return get_mongo_db()
    except Exception:
        return None


def safe_get_neo4j():
    try:
        drv = get_neo4j_driver()
        if drv is None:
            return None
        return drv
    except Exception as e:
        print(f"[Neo4j Connection Error] {str(e)}")
        return None


def upsert_movie_to_backends(movie):
    # MongoDB
    db = safe_get_mongo()
    doc = {
        'movie_id': int(movie.pk),
        'title': movie.title,
        'year': movie.year,
        'duration': movie.duration,
        'description': movie.description or '',
        'poster': getattr(movie.poster, 'url', None),
        'poster_url': movie.poster_url,
        'genres': [g.name for g in movie.genres.all()],
        'tags': [t.name for t in movie.tags.all()],
    }
    try:
        if db is not None:
            coll = db.movies
            coll.update_one({'movie_id': doc['movie_id']}, {'$set': doc}, upsert=True)
    except Exception:
        traceback.print_exc()

    # Neo4j
    drv = safe_get_neo4j()
    if drv is None:
        return
    try:
        with drv.session() as session:
            session.run(
                "MERGE (m:Movie {movie_id:$id}) SET m.title=$title, m.year=$year, m.duration=$duration, m.description=$description",
                id=int(movie.pk), title=movie.title, year=movie.year, duration=movie.duration, description=doc['description']
            )
            session.run(
                "MATCH (m:Movie {movie_id:$id})-[r:HAS_GENRE|HAS_TAG]->() DELETE r",
                id=int(movie.pk),
            )
            for g in movie.genres.all():
                session.run("MERGE (g:Genre {name:$name})", name=g.name)
                session.run(
                    "MATCH (m:Movie {movie_id:$id}),(g:Genre {name:$name}) MERGE (m)-[:HAS_GENRE]->(g)",
                    id=int(movie.pk),
                    name=g.name,
                )
            for t in movie.tags.all():
                session.run("MERGE (t:Tag {name:$name})", name=t.name)
                session.run(
                    "MATCH (m:Movie {movie_id:$id}),(t:Tag {name:$name}) MERGE (m)-[:HAS_TAG]->(t)",
                    id=int(movie.pk),
                    name=t.name,
                )
    except Exception as e:
        print(f"[Neo4j Sync Error] Failed to sync movie {movie.pk}: {str(e)}")
    finally:
        try:
            drv.close()
        except Exception:
            pass


def delete_movie_from_backends(movie_id):
    db = safe_get_mongo()
    try:
        if db is not None:
            db.movies.delete_one({'movie_id': int(movie_id)})
    except Exception:
        traceback.print_exc()

    drv = safe_get_neo4j()
    if drv is None:
        return
    try:
        with drv.session() as session:
            session.run("MATCH (m:Movie {movie_id:$id}) DETACH DELETE m", id=int(movie_id))
    except Exception:
        traceback.print_exc()
    finally:
        try:
            drv.close()
        except Exception:
            pass


@receiver(m2m_changed, sender=Movie.genres.through)
def movie_genres_m2m_changed(sender, instance, action, **kwargs):
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    try:
        upsert_movie_to_backends(instance)
    except Exception:
        traceback.print_exc()


@receiver(m2m_changed, sender=Movie.tags.through)
def movie_tags_m2m_changed(sender, instance, action, **kwargs):
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    try:
        upsert_movie_to_backends(instance)
    except Exception:
        traceback.print_exc()


@receiver(post_save, sender=Movie)
def movie_post_save(sender, instance, created, **kwargs):
    def _sync():
        try:
            upsert_movie_to_backends(instance)
        except Exception:
            traceback.print_exc()

    try:
        transaction.on_commit(_sync)
    except Exception:
        _sync()


@receiver(post_delete, sender=Movie)
def movie_post_delete(sender, instance, **kwargs):
    try:
        delete_movie_from_backends(instance.pk)
    except Exception:
        traceback.print_exc()


@receiver(post_save, sender=Rating)
def rating_post_save(sender, instance, created, **kwargs):
    # Update Neo4j relationship and write activity to Mongo
    drv = safe_get_neo4j()
    try:
        if drv is not None:
            rel = 'LIKED' if instance.score >= 7 else 'RATED'
            with drv.session() as session:
                session.run("MERGE (u:User {user_id:$uid}) SET u.user_id=$uid", uid=int(instance.user_id))
                session.run("MERGE (m:Movie {movie_id:$mid}) SET m.movie_id=$mid", mid=int(instance.movie_id))
                session.run(
                    "MATCH (u:User {user_id:$uid}), (m:Movie {movie_id:$mid}) MERGE (u)-[r:%s]->(m) SET r.score=$score" % rel,
                    uid=int(instance.user_id), mid=int(instance.movie_id), score=int(instance.score)
                )
    except Exception as e:
        print(f"[Neo4j Rating Sync Error] {str(e)}")
    finally:
        try:
            if drv is not None:
                drv.close()
        except Exception:
            pass

    # Mongo activity log
    db = safe_get_mongo()
    try:
        if db is not None:
            db.activity.insert_one({
                'type': 'rating',
                'user_id': int(instance.user_id),
                'movie_id': int(instance.movie_id),
                'score': int(instance.score),
                'created_at': instance.created_at.isoformat() if hasattr(instance, 'created_at') else None,
            })
    except Exception as e:
        print(f"[MongoDB Activity Log Error] {str(e)}")


@receiver(post_delete, sender=Rating)
def rating_post_delete(sender, instance, **kwargs):
    drv = safe_get_neo4j()
    try:
        if drv is not None:
            with drv.session() as session:
                session.run("MATCH (u:User {user_id:$uid})-[r]->(m:Movie {movie_id:$mid}) DELETE r", uid=int(instance.user_id), mid=int(instance.movie_id))
    except Exception as e:
        print(f"[Neo4j Rating Delete Error] {str(e)}")
    finally:
        try:
            if drv is not None:
                drv.close()
        except Exception:
            pass
            pass


@receiver(post_save, sender=Watchlist)
def watchlist_post_save(sender, instance, created, **kwargs):
    # Treat as WATCHED relationship for graph
    drv = safe_get_neo4j()
    try:
        if drv is not None:
            with drv.session() as session:
                session.run("MERGE (u:User {user_id:$uid})", uid=int(instance.user_id))
                session.run("MERGE (m:Movie {movie_id:$mid})", mid=int(instance.movie_id))
                session.run("MATCH (u:User {user_id:$uid}),(m:Movie {movie_id:$mid}) MERGE (u)-[:WATCHED]->(m)", uid=int(instance.user_id), mid=int(instance.movie_id))
    except Exception:
        traceback.print_exc()
    finally:
        try:
            if drv is not None:
                drv.close()
        except Exception:
            pass

    db = safe_get_mongo()
    try:
        if db is not None:
            db.activity.insert_one({
                'type': 'watchlist_add',
                'user_id': int(instance.user_id),
                'movie_id': int(instance.movie_id),
                'added_at': instance.added_at.isoformat() if hasattr(instance, 'added_at') else None,
            })
    except Exception:
        traceback.print_exc()


@receiver(post_save, sender=Review)
def review_post_save(sender, instance, created, **kwargs):
    db = safe_get_mongo()
    try:
        if db is not None:
            db.reviews.update_one({'review_id': int(instance.pk)}, {'$set': {
                'review_id': int(instance.pk),
                'user_id': int(instance.user_id),
                'movie_id': int(instance.movie_id),
                'content': instance.content,
                'created_at': instance.created_at.isoformat() if hasattr(instance, 'created_at') else None,
            }}, upsert=True)
    except Exception:
        traceback.print_exc()


@receiver(post_delete, sender=Review)
def review_post_delete(sender, instance, **kwargs):
    db = safe_get_mongo()
    try:
        if db is not None:
            db.reviews.delete_one({'review_id': int(instance.pk)})
    except Exception:
        traceback.print_exc()
