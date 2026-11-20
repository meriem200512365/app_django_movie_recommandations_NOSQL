**README — Projet "film" (Django + MySQL + MongoDB + Neo4j)**

**Résumé**
- **Description:** Application Django (v4.2) nommée `film` fournissant un catalogue de films avec CRUD, notation, avis, watchlist et recommandations hybrides (SQL, MongoDB, Neo4j).
- **App principale:** `movies`.

**Architecture**
- **Backend:** Django ORM (MySQL par défaut) pour stockage principal.
- **NoSQL (optionnel):** MongoDB pour documents films et recherche full-text; Neo4j pour graphe utilisateur-film (recommandations graph).
- **Synchronisation:** commande de gestion `sync_to_mongo_neo4j` réplique les films, utilisateurs, ratings et watchlist vers MongoDB/Neo4j.

**Dépendances**
- Voir [requirements.txt](requirements.txt) — `Django`, `Pillow`, `mysqlclient` (ou `PyMySQL`), `pymongo`, `neo4j`.

**Fichiers clés**
- **Configuration projet:** [film/film/settings.py](film/film/settings.py)
- **Entrypoint:** [manage.py](manage.py)
- **App principale:** [movies/](/movies)
  - Modèles: [movies/models.py](movies/models.py)
  - Vues: [movies/views.py](movies/views.py)
  - URLs: [movies/urls.py](movies/urls.py)
  - Backends NoSQL: [movies/db_backends.py](movies/db_backends.py)
  - Commandes de gestion: [movies/management/commands/](movies/management/commands/)
- **Templates:** [movies/templates/movies/](movies/templates/movies/)
- **Static / Media:** `static/`, `media/` (posters sous `media/posters/`).

**Variables d'environnement importantes**
- MySQL: `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`.
- MongoDB: `MONGODB_URI` (ex: `mongodb://localhost:27017`), `MONGODB_DB` (par défaut `film_mongo`).
- Neo4j: `NEO4J_URI` (ex: `bolt://localhost:7687`), `NEO4J_USER`, `NEO4J_PASSWORD`.
- Sécurité: ne jamais laisser de mots de passe en dur en production — utiliser des variables d'environnement ou un vault.

**Installation & Exécution locale**
1. Créer et activer un environnement virtuel, installer dépendances:
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
```
2. Configurer les variables d'environnement (exemples Windows PowerShell):
```powershell
$env:MYSQL_DATABASE='film_db'
$env:MYSQL_USER='root'
$env:MYSQL_PASSWORD='changeme'
$env:MYSQL_HOST='127.0.0.1'
$env:MONGODB_URI='mongodb://localhost:27017'
$env:NEO4J_URI='bolt://localhost:7687'
$env:NEO4J_USER='neo4j'
$env:NEO4J_PASSWORD='password'
```
3. Appliquer les migrations et créer un superuser:
```bash
python manage.py migrate
python manage.py createsuperuser
```
4. (Optionnel) Remplir la base avec des films d'exemple:
```bash
python manage.py seed_movies
```
5. (Optionnel) Synchroniser vers MongoDB/Neo4j:
```bash
python manage.py sync_to_mongo_neo4j
```
6. Lancer le serveur:
```bash
python manage.py runserver
```

**Commandes de gestion utiles**
- `python manage.py seed_movies` — crée des films d'exemple et posters (ne crée pas les genres par défaut).
- `python manage.py sync_to_mongo_neo4j` — synchronise SQL → MongoDB/Neo4j (crée index texte dans Mongo, nœuds/relations dans Neo4j).

**Comportement des recommandations "More Like This"**
- La section "More Like This" dans `movie_detail` utilise les **genres partagés**:
  - Si un film n'a pas de `Genre` associé, la requête renverra rien.
  - Si l'utilisateur a déjà noté/regardé beaucoup de films, la vue exclut ces films (pour éviter répétition), ce qui peut laisser la liste vide si l'ensemble est réduit.
- Vérifiez que les films ont des `genres` et `tags` — le script `seed_movies` fourni n'associe pas automatiquement de genres.

**Vérifications & Debug rapide**
- Vérifier genres d'un film:
```bash
python manage.py shell -c "from movies.models import Movie; m=Movie.objects.first(); print(m.id, m.title, list(m.genres.values_list('name',flat=True)))"
```
- Tester la requête de recommandations localement (remplacez `MOVIE_ID`):
```bash
python manage.py shell -c "from movies.models import Movie; from django.db.models import Count; m=Movie.objects.get(pk=MOVIE_ID); genre_ids=list(m.genres.values_list('id',flat=True)); print('genre_ids',genre_ids); qs=Movie.objects.filter(genres__in=genre_ids).exclude(pk__in={m.pk}).annotate(shared=Count('genres')).order_by('-shared','-ratings__score').distinct()[:10]; print([ (x.pk,x.title) for x in qs ])"
```
- Ajouter genres via shell (ex):
```bash
python manage.py shell -c "from movies.models import Genre,Movie; g,_=Genre.objects.get_or_create(name='Action'); movies=Movie.objects.all()[:3]; [m.genres.add(g) for m in movies]; print('done')"
```

**Problèmes connus & recommandations**
- `seed_movies` ne crée pas de `Genre`/`Tag` — ajouter cette logique si vous voulez des recommandations automatiques.
- Vérifier les identifiants/permissions Neo4j si `graph_recommendations` renvoie des erreurs (les vues gèrent les exceptions et proposent des fallbacks SQL/Mongo).
- En production: `DEBUG=False`, configurer `ALLOWED_HOSTS`, sécuriser cookies (`SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`) et stocker `SECRET_KEY` en secret.

**Structure réservée au rapport (liste succincte)**
- Entrées: [manage.py](manage.py)
- Réglages: [film/film/settings.py](film/film/settings.py)
- Dépendances: [requirements.txt](requirements.txt)
- App: [movies/](/movies) (models, views, urls, templates)
- Commandes: [movies/management/commands/](movies/management/commands/)

**Proposition d'améliorations**
- Étendre `seed_movies` pour créer/associer `Genre`/`Tag` et quelques `Rating` automatiques.
- Rendre les badges `Genres`/`Tags` cliquables (filtre par genre/tag dans `movie_list`).
- Ajouter tests unitaires couvrant la logique de recommandations (SQL/Mongo/Neo4j fallback).

---
Fichier généré automatiquement pour le rapport — modifiez/complétez si nécessaire.
