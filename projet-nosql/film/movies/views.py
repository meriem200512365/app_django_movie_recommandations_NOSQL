from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Movie, Rating, Review, Watchlist, Genre, Tag
from .forms import MovieForm, ReviewForm, RatingForm
from django.db.models import Avg, Q, Count
from django.core.paginator import Paginator
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login as auth_login, authenticate
from django.shortcuts import HttpResponse
from .db_backends import get_mongo_db, get_neo4j_driver
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.core.cache import cache
from functools import wraps
from django.contrib.auth import get_user_model

User = get_user_model()


def home(request):
    """Home/welcome page with stats and navigation."""
    context = {
        'movie_count': Movie.objects.count(),
        'user_count': User.objects.count(),
        'rating_count': Rating.objects.count(),
    }
    return render(request, 'movies/home.html', context)


def is_staff(user):
    return user.is_staff


def role_required(*roles):
    """
    Decorator to check if user has one of the required roles.
    Roles: 'staff' (is_staff=True), 'user' (any authenticated user)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if 'user' in roles:
                # Any authenticated user is OK
                return view_func(request, *args, **kwargs)
            if 'staff' in roles and request.user.is_staff:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('movies:list')
        return wrapper
    return decorator


def movie_list(request):
    q = request.GET.get('q')
    year = request.GET.get('year')
    min_rating = request.GET.get('min_rating')
    genre = request.GET.get('genre')
    tag = request.GET.get('tag')
    movies = Movie.objects.all()
    if q:
        movies = movies.filter(Q(title__icontains=q))
    if year:
        try:
            movies = movies.filter(year=int(year))
        except ValueError:
            pass
    # resolve genre/tag to objects (prefer id, fallback to name) so template can show names
    active_genre_name = None
    active_tag_name = None
    if genre:
        try:
            g = Genre.objects.get(pk=int(genre))
        except (ValueError, Genre.DoesNotExist):
            g = Genre.objects.filter(name__iexact=genre).first()
        if g:
            movies = movies.filter(genres=g)
            active_genre_name = g.name
    if tag:
        try:
            t = Tag.objects.get(pk=int(tag))
        except (ValueError, Tag.DoesNotExist):
            t = Tag.objects.filter(name__iexact=tag).first()
        if t:
            movies = movies.filter(tags=t)
            active_tag_name = t.name
    # annotate average rating for filtering and display
    movies = movies.annotate(avg_rating=Avg('ratings__score'))
    if min_rating:
        try:
            mr = float(min_rating)
            movies = movies.filter(avg_rating__gte=mr)
        except ValueError:
            pass

    # pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(movies.order_by('-avg_rating', 'title'), 10)
    page_obj = paginator.get_page(page)
    return render(request, 'movies/movie_list.html', {
        'page_obj': page_obj,
        'q': q,
        'year': year,
        'min_rating': min_rating,
        'active_genre': genre,
        'active_tag': tag,
        'active_genre_name': active_genre_name,
        'active_tag_name': active_tag_name,
    })


def movie_detail(request, pk):
    # Preload related data to avoid extra queries in the template
    qs = Movie.objects.prefetch_related('genres', 'tags', 'reviews__user', 'ratings__user')
    movie = get_object_or_404(qs, pk=pk)
    review_form = ReviewForm()
    rating_form = RatingForm()
    reviews = movie.reviews.select_related('user').all()
    ratings = movie.ratings.select_related('user').all()
    avg_rating = ratings.aggregate(avg=Avg('score'))['avg'] if ratings.exists() else None
    in_watchlist = False
    if request.user.is_authenticated:
        in_watchlist = Watchlist.objects.filter(user=request.user, movie=movie).exists()
    # Recommendations
    content_recs = []
    collaborative_recs = []
    graph_recs = []

    # compute set of movie ids the current user has watched or rated to exclude
    excluded_ids = {movie.pk}
    if request.user.is_authenticated:
        rated_ids = list(request.user.ratings.values_list('movie_id', flat=True))
        watched_ids = list(request.user.watchlist.values_list('movie_id', flat=True))
        excluded_ids.update(rated_ids)
        excluded_ids.update(watched_ids)

    # Content-based: shared genres (SQL)
    try:
        genre_ids = list(movie.genres.values_list('id', flat=True))
        if genre_ids:
            # initial queryset may return duplicates due to joins; compute ordered unique ids first
            raw_qs = Movie.objects.filter(genres__in=genre_ids).exclude(pk__in=excluded_ids).annotate(shared=Count('genres')).order_by('-shared', '-ratings__score')
            raw_ids = list(raw_qs.values_list('pk', flat=True))
            # preserve order but remove duplicates
            unique_ids = []
            for mid in raw_ids:
                if mid not in unique_ids:
                    unique_ids.append(mid)
                if len(unique_ids) >= 10:
                    break
            if unique_ids:
                movies_qs = Movie.objects.filter(pk__in=unique_ids)
                # order movies according to unique_ids
                ordered = sorted(movies_qs, key=lambda m: unique_ids.index(m.pk))
                content_recs = ordered
    except Exception:
        content_recs = []

    # Collaborative: users who liked this movie -> other highly-rated movies
    try:
        # find users who rated this movie highly
        liked_users = Rating.objects.filter(movie=movie, score__gte=7).values_list('user_id', flat=True)
        if liked_users:
            qs2 = Rating.objects.filter(user_id__in=liked_users).exclude(movie=movie).values('movie').annotate(avg=Avg('score')).order_by('-avg')[:10]
            movie_ids = [item['movie'] for item in qs2]
            collaborative_recs = list(Movie.objects.filter(pk__in=movie_ids).exclude(pk__in=excluded_ids))
    except Exception:
        collaborative_recs = []

    # Graph-based: Neo4j recommendations (if available)
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            q = (
                "MATCH (m:Movie {movie_id:$mid})<-[:LIKED]-(u:User)-[:LIKED]->(rec:Movie) "
                "WHERE rec.movie_id <> $mid RETURN rec.movie_id AS movie_id, count(*) AS score ORDER BY score DESC LIMIT 10"
            )
            res = session.run(q, mid=int(movie.pk))
            ids = [r['movie_id'] for r in res]
            if ids:
                graph_recs = list(Movie.objects.filter(pk__in=ids).exclude(pk__in=excluded_ids))
        try:
            driver.close()
        except Exception:
            pass
    except Exception:
        # skip graph recs if neo4j unavailable
        graph_recs = []

    return render(request, 'movies/movie_detail.html', {
        'movie': movie,
        'review_form': review_form,
        'rating_form': rating_form,
        'reviews': reviews,
        'ratings': ratings,
        'avg_rating': avg_rating,
        'in_watchlist': in_watchlist,
        'content_recs': content_recs,
        'collaborative_recs': collaborative_recs,
        'graph_recs': graph_recs,
    })


@user_passes_test(is_staff)
def movie_create(request):
    if request.method == 'POST':
        form = MovieForm(request.POST)
        if form.is_valid():
            movie = form.save()
            messages.success(request, 'Movie created.')
            return redirect('movies:detail', pk=movie.pk)
    else:
        form = MovieForm()
    return render(request, 'movies/movie_form.html', {'form': form})


@user_passes_test(is_staff)
def movie_update(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    if request.method == 'POST':
        form = MovieForm(request.POST, instance=movie)
        if form.is_valid():
            form.save()
            messages.success(request, 'Movie updated.')
            return redirect('movies:detail', pk=movie.pk)
    else:
        form = MovieForm(instance=movie)
    return render(request, 'movies/movie_form.html', {'form': form, 'movie': movie})


@user_passes_test(is_staff)
def movie_delete(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    if request.method == 'POST':
        movie.delete()
        messages.success(request, 'Movie deleted.')
        return redirect('movies:list')
    return render(request, 'movies/movie_confirm_delete.html', {'movie': movie})


@login_required
def add_to_watchlist(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    Watchlist.objects.get_or_create(user=request.user, movie=movie)
    messages.success(request, 'Added to watchlist.')
    return redirect('movies:detail', pk=pk)


@login_required
def remove_from_watchlist(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    Watchlist.objects.filter(user=request.user, movie=movie).delete()
    messages.success(request, 'Removed from watchlist.')
    return redirect('movies:detail', pk=pk)


@login_required
def watchlist_view(request):
    # order by most recently added first and select related movie to avoid extra queries
    items = Watchlist.objects.filter(user=request.user).select_related('movie').order_by('-added_at')
    return render(request, 'movies/watchlist.html', {'items': items})


@login_required
def add_review(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.movie = movie
            review.save()
            messages.success(request, 'Review added.')
    return redirect('movies:detail', pk=pk)


@login_required
def add_rating(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            rating, created = Rating.objects.update_or_create(
                user=request.user, movie=movie,
                defaults={'score': form.cleaned_data['score']}
            )
            messages.success(request, 'Rating saved.')
    return redirect('movies:detail', pk=pk)


def register(request):
    """Register new user and redirect to user dashboard on success."""
    if request.user.is_authenticated:
        return redirect('movies:user_dashboard')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, 'Registration successful. Welcome!')
            return redirect('movies:user_dashboard')  # Redirect new users to dashboard
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def custom_login(request):
    """Secure form-based login with role-based redirect."""
    if request.user.is_authenticated:
        # Already logged in, redirect to dashboard
        return redirect('movies:admin_dashboard' if request.user.is_staff else 'movies:user_dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                auth_login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                # Role-based redirect
                if user.is_staff:
                    return redirect('movies:admin_dashboard')
                else:
                    return redirect('movies:user_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})


@login_required
def profile(request):
    user = request.user
    ratings = user.ratings.select_related('movie').all()
    watchlist = user.watchlist.select_related('movie').all()
    reviews = user.reviews.select_related('movie').all()
    return render(request, 'movies/profile.html', {'ratings': ratings, 'watchlist': watchlist, 'reviews': reviews})


@login_required
def user_dashboard(request):
    # Dashboard for normal users (non-staff)
    if request.user.is_staff:
        return redirect('movies:admin_dashboard')
    user = request.user
    ratings = user.ratings.select_related('movie').all()
    watchlist = user.watchlist.select_related('movie').all()
    reviews = user.reviews.select_related('movie').all()
    return render(request, 'movies/user_dashboard.html', {'ratings': ratings, 'watchlist': watchlist, 'reviews': reviews})


@staff_member_required
def admin_dashboard(request):
    # Simple admin dashboard with counts and recent syncs
    from django.contrib.auth import get_user_model
    from movies.models import SyncLog
    User = get_user_model()
    movie_count = Movie.objects.count()
    user_count = User.objects.count()
    rating_count = Rating.objects.count()
    review_count = Review.objects.count()
    recent_syncs = SyncLog.objects.order_by('-started_at')[:10]
    return render(request, 'movies/admin_dashboard.html', {
        'movie_count': movie_count,
        'user_count': user_count,
        'rating_count': rating_count,
        'review_count': review_count,
        'recent_syncs': recent_syncs,
    })


def recommendations(request):
    # Redirect to the smart recommendations dashboard so users
    # immediately see recommendations without choosing buttons.
    return redirect('movies:recommendations_dashboard')


def recommendations_dashboard(request):
    user = request.user
    limit = request.GET.get('limit')
    try:
        limit = int(limit) if limit is not None else 10
    except ValueError:
        limit = 10
    limit = max(1, min(limit, 50))

    last_liked = None
    has_history = False
    if user.is_authenticated:
        last_liked = Rating.objects.filter(user=user, score__gte=7).order_by('-created_at').first()
        has_history = last_liked is not None or Watchlist.objects.filter(user=user).exists() or Rating.objects.filter(user=user).exists()

    context = {
        'has_history': has_history,
        'neo4j_section_title': '',
        'neo4j_movies': [],
        'neo4j_scores': {},
        'neo4j_items': [],
        'mongo_section_title': '',
        'mongo_movies': [],
    }

    # =========================================================
    # PART A: Neo4j collaborative OR global top rated
    # =========================================================
    neo4j_movie_ids = []
    neo4j_scores = {}

    driver = None
    try:
        driver = get_neo4j_driver()
    except Exception:
        driver = None

    try:
        if driver is not None:
            with driver.session() as session:
                if has_history and user.is_authenticated:
                    context['neo4j_section_title'] = 'Users Like You Also Watched'
                    query = (
                        "MATCH (u:User {user_id:$uid})-[:LIKED]->(:Movie)<-[:LIKED]-(other:User)-[:LIKED]->(rec:Movie) "
                        "WHERE NOT (u)-[:LIKED]->(rec) "
                        "RETURN rec.movie_id AS movie_id, count(*) AS score ORDER BY score DESC LIMIT $limit"
                    )
                    res = session.run(query, uid=int(user.pk), limit=int(limit))
                    for r in res:
                        mid = int(r['movie_id'])
                        neo4j_movie_ids.append(mid)
                        neo4j_scores[mid] = int(r['score'])

                if not neo4j_movie_ids:
                    context['neo4j_section_title'] = 'Global Top Rated (Community Favorites)'
                    cache_key = f'neo4j_global_top_{limit}'
                    cached = cache.get(cache_key)
                    if cached is not None:
                        neo4j_movie_ids, neo4j_scores = cached
                    else:
                        query = (
                            "MATCH (m:Movie)<-[:LIKED]-(u:User) "
                            "RETURN m.movie_id AS movie_id, count(u) AS popularity ORDER BY popularity DESC LIMIT $limit"
                        )
                        res = session.run(query, limit=int(limit))
                        tmp_ids = []
                        tmp_scores = {}
                        for r in res:
                            mid = int(r['movie_id'])
                            tmp_ids.append(mid)
                            tmp_scores[mid] = int(r['popularity'])
                        neo4j_movie_ids, neo4j_scores = tmp_ids, tmp_scores
                        cache.set(cache_key, (neo4j_movie_ids, neo4j_scores), 60)
    except Exception:
        neo4j_movie_ids = []
        neo4j_scores = {}
    finally:
        try:
            if driver is not None:
                driver.close()
        except Exception:
            pass

    if neo4j_movie_ids:
        movies_qs = Movie.objects.filter(pk__in=neo4j_movie_ids)
        ordered_movies = sorted(movies_qs, key=lambda m: neo4j_movie_ids.index(m.pk))
        context['neo4j_movies'] = ordered_movies
        context['neo4j_scores'] = neo4j_scores
        context['neo4j_items'] = [{'movie': m, 'score': neo4j_scores.get(m.pk)} for m in ordered_movies]
    else:
        # SQL fallback if Neo4j isn't available
        context['neo4j_section_title'] = 'Popular Right Now'
        qs = Movie.objects.annotate(popularity=Count('ratings')).order_by('-popularity', 'title')[:limit]
        ordered_movies = list(qs)
        context['neo4j_movies'] = ordered_movies
        context['neo4j_items'] = [{'movie': m, 'score': None} for m in ordered_movies]

    # =========================================================
    # PART B: Mongo content similarity OR global explore
    # =========================================================
    db = None
    try:
        db = get_mongo_db()
    except Exception:
        db = None

    if db is not None:
        coll = db.movies

        if has_history and last_liked is not None:
            context['mongo_section_title'] = f"Because you liked '{last_liked.movie.title}'"
            try:
                source_doc = coll.find_one({'movie_id': int(last_liked.movie_id)})
            except Exception:
                source_doc = None

            if source_doc and source_doc.get('genres'):
                try:
                    pipeline = [
                        {
                            '$match': {
                                'genres': {'$in': list(source_doc.get('genres', []))},
                                'movie_id': {'$ne': int(source_doc['movie_id'])},
                            }
                        },
                        {'$limit': int(limit)},
                    ]
                    context['mongo_movies'] = list(coll.aggregate(pipeline))
                except Exception:
                    context['mongo_movies'] = []

        if not context['mongo_movies']:
            context['mongo_section_title'] = 'Explore Our Collection'
            try:
                context['mongo_movies'] = list(coll.find().limit(int(limit)))
            except Exception:
                context['mongo_movies'] = []
    else:
        # SQL fallback if MongoDB isn't available
        if has_history and last_liked is not None:
            context['mongo_section_title'] = f"Because you liked '{last_liked.movie.title}'"
            try:
                genre_ids = list(last_liked.movie.genres.values_list('id', flat=True))
                if genre_ids:
                    qs = Movie.objects.filter(genres__in=genre_ids).exclude(pk=last_liked.movie.pk).distinct()[:limit]
                    context['mongo_movies'] = list(qs)
            except Exception:
                context['mongo_movies'] = []

        if not context['mongo_movies']:
            context['mongo_section_title'] = 'Explore Our Collection'
            context['mongo_movies'] = list(Movie.objects.order_by('title')[:limit])

    return render(request, 'movies/recommendations_dashboard.html', context)


def content_recommendations(request):
    """Use MongoDB text search on movie descriptions and titles."""
    try:
        db = get_mongo_db()
    except RuntimeError as e:
        return HttpResponse(f'MongoDB not configured: {e}', status=500)

    q = request.GET.get('q') or request.GET.get('q', '')
    coll = db.movies
    if not q:
        docs = list(coll.find().limit(20))
    else:
        # try text search if available
        try:
            docs = list(coll.find({'$text': {'$search': q}}, {'score': {'$meta': 'textScore'}}).sort([('score', {'$meta': 'textScore'})]).limit(20))
        except Exception:
            # fallback to title/description regex
            docs = list(coll.find({'$or': [{'title': {'$regex': q, '$options': 'i'}}, {'description': {'$regex': q, '$options': 'i'}}]}).limit(20))

    return render(request, 'movies/recommendations_results.html', {'method': 'Content-based (MongoDB)', 'items': docs})


def collaborative_recommendations(request):
    if not request.user.is_authenticated:
        return redirect('login')
    # simple collaborative: top avg-rated movies by others that the user hasn't rated
    from django.db.models import Avg
    user_rated = Rating.objects.filter(user=request.user).values_list('movie_id', flat=True)
    qs = Rating.objects.exclude(user=request.user).values('movie').annotate(avg=Avg('score')).exclude(movie__in=list(user_rated)).order_by('-avg')[:20]
    movie_ids = [item['movie'] for item in qs]
    movies = Movie.objects.filter(pk__in=movie_ids)
    # preserve order
    movies_ordered = sorted(movies, key=lambda m: movie_ids.index(m.pk))
    return render(request, 'movies/recommendations_results.html', {'method': 'Collaborative', 'items': movies_ordered})


def graph_recommendations(request):
    if not request.user.is_authenticated:
        return redirect('login')
    try:
        driver = get_neo4j_driver()
    except RuntimeError as e:
        return HttpResponse(f'Neo4j not configured: {e}', status=500)

    user_id = int(request.user.pk)
    query = (
        "MATCH (u:User {user_id:$uid})-[:LIKED]->(:Movie)<-[:LIKED]-(other:User)-[:LIKED]->(rec:Movie) "
        "WHERE NOT (u)-[:LIKED]->(rec) "
        "RETURN rec.movie_id AS movie_id, count(*) AS score ORDER BY score DESC LIMIT 20"
    )
    movies = []
    try:
        with driver.session() as session:
            res = session.run(query, uid=user_id)
            movie_ids = [record['movie_id'] for record in res]
        if movie_ids:
            movies_qs = Movie.objects.filter(pk__in=movie_ids)
            movies = sorted(movies_qs, key=lambda m: movie_ids.index(m.pk))
    except Exception as e:
        # Provide a helpful message for authentication/authorization errors
        try:
            from neo4j.exceptions import AuthError
            if isinstance(e, AuthError) or 'Unauthorized' in str(e) or 'Access denied' in str(e):
                return HttpResponse('Neo4j authentication failed. Check NEO4J_USER and NEO4J_PASSWORD environment variables and Neo4j user permissions.', status=500)
        except Exception:
            pass
        return HttpResponse(f'Neo4j error: {e}', status=500)
    finally:
        try:
            driver.close()
        except Exception:
            pass

    return render(request, 'movies/recommendations_results.html', {'method': 'Graph (Neo4j)', 'items': movies})




