# FilmApp – Architecture & Setup

## 1) What is the “Like” in this project?

### Source of truth (MySQL)
There is no separate `Like` table.

The **"like" is derived from a MySQL rating**:
- In `movies/models.py`, the table is `Rating(user, movie, score, created_at)`.
- In the Neo4j graph, we treat a rating as:
  - `LIKED` relationship if `score >= 7`
  - otherwise `RATED`

So:
- **MySQL stores ratings (1..10)**.
- **Neo4j stores a `LIKED` relationship** derived from those ratings.

### Where is the logic implemented?

#### Frontend (templates)
The UI that triggers the “like” is the **rating form** on the movie detail page:
- `movies/templates/movies/movie_detail.html`
  - The form posts to `movies:add_rating`
  - When you submit a high score (>=7), that rating becomes a "like" in Neo4j.

There is also a watchlist button:
- Add/remove watchlist in the same template.

#### Backend (Django views)
- `movies/views.py`
  - `add_rating()` creates/updates a `Rating` row in MySQL.
  - `add_to_watchlist()` creates a `Watchlist` row in MySQL.

#### Backend (Django signals → automatic sync)
- `movies/signals.py`
  - `rating_post_save`: writes/updates Neo4j relationships.
    - `LIKED` if `score >= 7`, else `RATED`.
  - `watchlist_post_save`: writes a `WATCHED` relationship to Neo4j.

So the pipeline is:
1. User submits rating in UI → `POST /movie/<id>/rate/`
2. Django saves `Rating` in **MySQL**
3. Signal `rating_post_save` converts it into `(:User)-[:LIKED|RATED]->(:Movie)` in **Neo4j**

## 2) Databases & Responsibilities

### MySQL (Primary DB / source of truth)
**Stores**:
- `Movie`
- `Genre`, `Tag`
- `Rating`
- `Review`
- `Watchlist`

### MongoDB (Document store for content search / content recs)
**Stores**:
- `movies` documents (synced from MySQL)
- `activity` (rating/watchlist events)
- `reviews` documents (synced)

Used for:
- quick content filtering (genres/tags/description)
- text search (optional index)

### Neo4j (Graph DB for collaborative / graph recs)
**Stores**:
- `(:User {user_id})`
- `(:Movie {movie_id})`
- Relationships:
  - `(:User)-[:LIKED {score}]->(:Movie)`
  - `(:User)-[:RATED {score}]->(:Movie)`
  - `(:User)-[:WATCHED]->(:Movie)`
  - `(:Movie)-[:HAS_GENRE]->(:Genre {name})`
  - `(:Movie)-[:HAS_TAG]->(:Tag {name})`

Used for:
- collaborative traversal recommendations ("users like you")
- global popularity (count of likes)

## 3) Automatic Synchronization Design

### Why signals?
Signals remove manual steps. Any change in MySQL is automatically reflected in MongoDB / Neo4j.

### What syncs automatically?
- Movie create/update/delete
- Movie genres/tags changes (ManyToMany)
- Rating create/update/delete
- Watchlist add
- Review create/delete

Main file:
- `movies/signals.py`

Important note:
- Movie sync is executed after DB commit via `transaction.on_commit()` to avoid syncing rolled-back data.

## 4) Recommendation System

### A) Smart Hybrid Page (Cold start safe)
Route:
- `/recommendations/smart/`

View:
- `movies/views.py::recommendations_dashboard`

Logic:
- If user has history (ratings/watchlist):
  - Neo4j: collaborative recommendations
  - MongoDB: similar-by-genre to last liked movie
- If user has no history:
  - Neo4j: global top rated (cached)
  - MongoDB: explore collection

Fallbacks:
- If Neo4j is down, uses SQL popularity.
- If MongoDB is down, uses SQL shared-genres.

Template:
- `movies/templates/movies/recommendations_dashboard.html`

### B) Other recommendation pages
- `/recommendations/content/` → MongoDB search
- `/recommendations/collaborative/` → SQL-based collaborative
- `/recommendations/graph/` → Neo4j graph traversal

## 5) Setup & Run

### Python dependencies
See `requirements.txt`.

### Environment variables
MySQL:
- `MYSQL_DATABASE` (default `film_db`)
- `MYSQL_USER` (default `root`)
- `MYSQL_PASSWORD` (default empty)
- `MYSQL_HOST` (default `127.0.0.1`)
- `MYSQL_PORT` (default `3306`)

MongoDB:
- `MONGODB_URI` (default `mongodb://localhost:27017`)
- `MONGODB_DB` (default `film_mongo`)

Neo4j:
- `NEO4J_URI` (default `bolt://localhost:7687`)
- `NEO4J_USER` (default `neo4j`)
- `NEO4J_PASSWORD` (default empty)

### Commands
- Migrations:
  - `python manage.py migrate`
- Run:
  - `python manage.py runserver`

On runserver startup, the app may run an initial bootstrap sync thread (see `movies/apps.py`).

## 6) Notes / Recommended next improvements
- Add a production-safe `SECRET_KEY` via env var.
- Add proper logging instead of `print()`/tracebacks.
- Add tests for sync + rec logic.
- Decide between `mysqlclient` vs `PyMySQL` and remove the other from requirements.
