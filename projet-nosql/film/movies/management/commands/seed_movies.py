import os
import random
from django.core.management.base import BaseCommand
from django.core.files import File
from django.contrib.auth.models import User
from django.conf import settings
import requests

from movies.models import Movie, Genre, Tag, Rating, Review, Watchlist


SAMPLE_MOVIES = [
    # title, year, duration(min), suggested_genres, suggested_tags
    ("The Matrix", 1999, 136, ["Action", "Sci-Fi", "Thriller"], ["classic", "cult", "blockbuster"]),
    ("Inception", 2010, 148, ["Action", "Sci-Fi", "Thriller"], ["blockbuster", "award-winning"]),
    ("Interstellar", 2014, 169, ["Drama", "Sci-Fi"], ["blockbuster", "award-winning"]),
    ("The Shawshank Redemption", 1994, 142, ["Drama"], ["classic", "award-winning"]),
    ("The Godfather", 1972, 175, ["Drama", "Thriller"], ["classic", "award-winning"]),
    ("Pulp Fiction", 1994, 154, ["Drama", "Thriller", "Comedy"], ["classic", "cult", "indie"]),
    ("The Dark Knight", 2008, 152, ["Action", "Drama", "Thriller"], ["blockbuster", "award-winning"]),
    ("Fight Club", 1999, 139, ["Drama", "Thriller"], ["cult", "classic"]),
    ("Forrest Gump", 1994, 142, ["Drama", "Comedy"], ["classic", "family", "award-winning"]),
    ("The Lord of the Rings: The Fellowship of the Ring", 2001, 178, ["Action", "Fantasy", "Drama"], ["classic", "blockbuster"]),
]

PLACEHOLDER_URL = "https://picsum.photos/400/600"


class Command(BaseCommand):
    help = "Seed sample movies + users + posters + genres/tags + ratings/reviews/watchlist (fill the site)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing sample users/movies data before seeding (careful).",
        )

    def handle(self, *args, **options):
        random.seed(42)

        if options.get("reset"):
            self._reset_sample_data()

        self._ensure_media_dirs()

        # 1) Create users
        users = self._create_users()

        # 2) Create genres & tags globally
        genres, tags = self._create_genres_and_tags_from_samples()

        # 3) Create movies + posters
        movies = self._create_movies_with_posters()

        # 4) Attach genres/tags for each movie (deterministic + a bit random)
        self._attach_genres_tags(movies, genres, tags)

        # 5) Create ratings/reviews/watchlist entries
        self._create_user_activity(movies, users)

        self.stdout.write(self.style.SUCCESS("✅ Seeding complete: movies + posters + genres/tags + users + ratings/reviews/watchlist"))

    # -----------------------
    # Helpers
    # -----------------------

    def _reset_sample_data(self):
        """
        Soft reset: removes sample users user1..user8 and testuser.
        Does not delete all users. Also deletes all movies (if you only use sample movies).
        Adjust if you have real data.
        """
        # Delete sample users
        usernames = ["testuser"] + [f"user{i}" for i in range(1, 9)]
        User.objects.filter(username__in=usernames).delete()

        # Delete sample movies by titles
        titles = [t for (t, *_rest) in SAMPLE_MOVIES]
        Movie.objects.filter(title__in=titles).delete()

        self.stdout.write(self.style.WARNING("Reset done (sample users + sample movies removed)."))

    def _ensure_media_dirs(self):
        posters_dir = os.path.join(settings.MEDIA_ROOT, "posters")
        os.makedirs(posters_dir, exist_ok=True)

    def _create_users(self):
        """
        Creates:
        - testuser / testpass
        - user1..user8 / testpass
        """
        users = []

        # test user
        user, created = User.objects.get_or_create(username="testuser")
        if created:
            user.set_password("testpass")
            user.save()
            self.stdout.write(self.style.SUCCESS("Created user testuser (password: testpass)"))
        else:
            self.stdout.write("User testuser already exists")
        users.append(user)

        # additional users
        for i in range(1, 9):
            uname = f"user{i}"
            u, created = User.objects.get_or_create(username=uname)
            if created:
                u.set_password("testpass")
                u.save()
            users.append(u)

        self.stdout.write(self.style.SUCCESS(f"Users ready: {len(users)}"))
        return users

    def _create_genres_and_tags_from_samples(self):
        # gather from SAMPLE_MOVIES + some extras
        genre_names = set()
        tag_names = set()

        for _title, _year, _dur, g_list, t_list in SAMPLE_MOVIES:
            genre_names.update(g_list)
            tag_names.update(t_list)

        # extras to diversify
        genre_names.update(["Comedy", "Fantasy", "Thriller", "Drama", "Action", "Sci-Fi"])
        tag_names.update(["indie", "family", "cult", "classic", "award-winning", "blockbuster"])

        genres = []
        tags = []

        for g in sorted(genre_names):
            obj, _ = Genre.objects.get_or_create(name=g)
            genres.append(obj)

        for t in sorted(tag_names):
            obj, _ = Tag.objects.get_or_create(name=t)
            tags.append(obj)

        self.stdout.write(self.style.SUCCESS(f"Genres ready: {len(genres)} | Tags ready: {len(tags)}"))
        return genres, tags

    def _create_movies_with_posters(self):
        posters_dir = os.path.join(settings.MEDIA_ROOT, "posters")
        movies = []

        for title, year, duration, _g, _t in SAMPLE_MOVIES:
            movie, created = Movie.objects.get_or_create(
                title=title,
                defaults={"year": year, "duration": duration},
            )

            # If existed, keep year/duration updated
            changed = False
            if movie.year != year:
                movie.year = year
                changed = True
            if movie.duration != duration:
                movie.duration = duration
                changed = True
            if changed:
                movie.save(update_fields=["year", "duration"])

            # poster
            if created or not movie.poster:
                self._download_and_attach_poster(movie, posters_dir)

            movies.append(movie)

        self.stdout.write(self.style.SUCCESS(f"Movies ready: {len(movies)}"))
        return movies

    def _download_and_attach_poster(self, movie, posters_dir):
        """
        Downloads random placeholder image and saves as poster.
        If download fails, we still save movie without crashing.
        """
        try:
            r = requests.get(PLACEHOLDER_URL, timeout=10)
            if r.status_code == 200:
                fname = f"{movie.title.replace(' ', '_').replace(':', '').replace('/', '_')}.jpg"
                path = os.path.join(posters_dir, fname)

                with open(path, "wb") as f:
                    f.write(r.content)

                with open(path, "rb") as f:
                    movie.poster.save(fname, File(f), save=True)

                self.stdout.write(self.style.SUCCESS(f"Poster attached for: {movie.title}"))
            else:
                movie.save()
                self.stdout.write(self.style.WARNING(f"Poster download failed for {movie.title} (status {r.status_code})"))
        except Exception as e:
            movie.save()
            self.stdout.write(self.style.WARNING(f"Poster error for {movie.title}: {e}"))

    def _attach_genres_tags(self, movies, genres, tags):
        """
        For each movie:
        - attach its suggested genres/tags
        - add a small random extra genre/tag to increase overlap for recommendations
        """
        # quick lookup by name
        genre_by_name = {g.name: g for g in genres}
        tag_by_name = {t.name: t for t in tags}

        for title, _year, _dur, suggested_genres, suggested_tags in SAMPLE_MOVIES:
            movie = Movie.objects.filter(title=title).first()
            if not movie:
                continue

            # suggested
            for gname in suggested_genres:
                g = genre_by_name.get(gname)
                if g:
                    movie.genres.add(g)

            for tname in suggested_tags:
                t = tag_by_name.get(tname)
                if t:
                    movie.tags.add(t)

            # add extra random overlap
            if random.random() < 0.7:
                movie.genres.add(random.choice(genres))
            if random.random() < 0.7:
                movie.tags.add(random.choice(tags))

        # ensure all movies have at least 1 genre + 1 tag (important for "More Like This")
        for movie in movies:
            if movie.genres.count() == 0:
                movie.genres.add(random.choice(genres))
            if movie.tags.count() == 0:
                movie.tags.add(random.choice(tags))

        self.stdout.write(self.style.SUCCESS("Genres/tags attached to all movies."))

    def _create_user_activity(self, movies, users):
        """
        Creates:
        - ratings for many movies by many users
        - reviews for some ratings
        - watchlist for some users/movies
        """
        sample_review_texts = [
            "Amazing movie, highly recommend.",
            "Good watch, had some slow parts but overall great.",
            "Not my cup of tea, but well made.",
            "A masterpiece — excellent acting and pacing.",
            "Entertaining and fun, perfect for a weekend.",
            "Great cinematography and soundtrack.",
            "Story was solid and characters were memorable.",
        ]

        for movie in movies:
            for u in users:
                # Rating probability
                if random.random() < 0.70:
                    score = random.randint(4, 10)
                    Rating.objects.update_or_create(
                        user=u,
                        movie=movie,
                        defaults={"score": score},
                    )

                    # Review probability (only if rated)
                    if random.random() < 0.45:
                        # avoid creating endless duplicates: if your Review model has unique constraints,
                        # this is safe; otherwise we can "get_or_create" with a short content.
                        Review.objects.create(
                            user=u,
                            movie=movie,
                            content=random.choice(sample_review_texts),
                        )

                # Watchlist probability
                if random.random() < 0.25:
                    Watchlist.objects.get_or_create(user=u, movie=movie)

        self.stdout.write(self.style.SUCCESS("User activity created: ratings + reviews + watchlist."))
