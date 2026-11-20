import os
import sys
from random import choice, randint

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'film.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from movies.models import Movie, Genre, Tag, Rating
User = get_user_model()

# Disable backend sync signals during seeding to avoid blocking external DB calls
try:
    from movies import signals as movie_signals
    from django.db.models.signals import m2m_changed, post_save, post_delete
    # disconnect known receivers if present
    try:
        m2m_changed.disconnect(movie_signals.movie_genres_m2m_changed, sender=Movie.genres.through)
    except Exception:
        pass
    try:
        m2m_changed.disconnect(movie_signals.movie_tags_m2m_changed, sender=Movie.tags.through)
    except Exception:
        pass
    try:
        post_save.disconnect(movie_signals.movie_post_save, sender=Movie)
    except Exception:
        pass
    try:
        post_delete.disconnect(movie_signals.movie_post_delete, sender=Movie)
    except Exception:
        pass
    try:
        post_save.disconnect(movie_signals.rating_post_save, sender=Rating)
    except Exception:
        pass
    try:
        post_delete.disconnect(movie_signals.rating_post_delete, sender=Rating)
    except Exception:
        pass
except Exception:
    pass

# Simple sample data
GENRES = ['Action', 'Adventure', 'Drama', 'Sci-Fi', 'Fantasy', 'Comedy', 'Thriller']
TAGS = ['epic', 'classic', 'award-winning', 'family', 'cult', 'blockbuster']
MOVIES = [
    ('The Shawshank Redemption', 1994, 142, 'https://via.placeholder.com/300x450/1a73e8/ffffff?text=Shawshank+Redemption'),
    ('The Godfather', 1972, 175, 'https://via.placeholder.com/300x450/dc2626/ffffff?text=The+Godfather'),
    ('The Dark Knight', 2008, 152, 'https://via.placeholder.com/300x450/1e40af/ffffff?text=The+Dark+Knight'),
    ('Inception', 2010, 148, 'https://via.placeholder.com/300x450/7c3aed/ffffff?text=Inception'),
    ('The Lord of the Rings: The Fellowship of the Ring', 2001, 178, 'https://via.placeholder.com/300x450/059669/ffffff?text=LOTR'),
    ('Pulp Fiction', 1994, 154, 'https://via.placeholder.com/300x450/d97706/ffffff?text=Pulp+Fiction'),
    ('Interstellar', 2014, 169, 'https://via.placeholder.com/300x450/0891b2/ffffff?text=Interstellar'),
    ('The Matrix', 1999, 136, 'https://via.placeholder.com/300x450/15803d/ffffff?text=The+Matrix'),
    ('Forrest Gump', 1994, 142, 'https://via.placeholder.com/300x450/ea580c/ffffff?text=Forrest+Gump'),
    ('The Empire Strikes Back', 1980, 124, 'https://via.placeholder.com/300x450/6366f1/ffffff?text=Empire+Strikes'),
]


def ensure_genres_tags():
    genre_objs = []
    tag_objs = []
    for g in GENRES:
        obj, _ = Genre.objects.get_or_create(name=g)
        genre_objs.append(obj)
    for t in TAGS:
        obj, _ = Tag.objects.get_or_create(name=t)
        tag_objs.append(obj)
    return genre_objs, tag_objs


def create_movies(genre_objs, tag_objs):
    created = []
    for title, year, duration, poster_url in MOVIES:
        m, created_flag = Movie.objects.get_or_create(title=title, defaults={'release_year': year, 'duration': duration, 'description': f'A great film from {year}', 'poster_url': poster_url})
        # attach 1-3 genres and 0-2 tags
        m.genres.set([choice(genre_objs) for _ in range(randint(1, 3))])
        m.tags.set([choice(tag_objs) for _ in range(randint(0, 2))])
        m.save()
        created.append(m)
    return created


def create_users_and_ratings(movies):
    # create demo users
    users = []
    for i in range(3):
        username = f'demo{i+1}'
        user, _ = User.objects.get_or_create(username=username, defaults={'email': f'{username}@example.com'})
        user.set_password('password')
        user.save()
        users.append(user)

    # add random ratings so collaborative recommendations have data
    for u in users:
        for m in movies:
            if randint(0, 1):
                score = randint(6, 10)
                Rating.objects.update_or_create(user=u, movie=m, defaults={'score': score})

    print('Created users:', [u.username for u in users])


if __name__ == '__main__':
    genres, tags = ensure_genres_tags()
    movies = create_movies(genres, tags)
    create_users_and_ratings(movies)
    print('Seed completed. Movies in DB:', Movie.objects.count())
