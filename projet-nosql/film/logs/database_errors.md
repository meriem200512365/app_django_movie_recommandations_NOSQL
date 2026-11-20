# Journal des Erreurs - Application de Gestion de Films

Ce document répertorie les erreurs courantes rencontrées lors du développement de l'application, leurs solutions et les références utiles.

## Table des Matières
1. [Erreurs MySQL](#mysql-errors)
2. [Erreurs MongoDB](#mongodb-errors)
3. [Erreurs Neo4j](#neo4j-errors)
4. [Erreurs de Synchronisation](#sync-errors)
5. [Erreurs Django](#django-errors)

## MySQL Errors

### 1. Erreur de connexion à la base de données
```
django.db.utils.OperationalError: (2003, "Can't connect to MySQL server on 'localhost'")
```
**Cause** : Le serveur MySQL n'est pas démarré ou les identifiants sont incorrects.
**Solution** :
- Vérifier que le service MySQL est en cours d'exécution
- Vérifier les paramètres de connexion dans `settings.py`
- S'assurer que l'utilisateur a les droits nécessaires

**Documentation** : [Django Database Settings](https://docs.djangoproject.com/en/4.2/ref/settings/#databases)

### 2. Erreur de clé étrangère
```
django.db.utils.IntegrityError: (1452, 'Cannot add or update a child row: a foreign key constraint fails')
```
**Cause** : Tentative d'insertion d'une référence à une clé étrangère qui n'existe pas.
**Solution** :
- Vérifier que les données référencées existent avant l'insertion
- Utiliser `on_delete` correctement dans les modèles

## MongoDB Errors

### 1. Erreur de connexion
```
pymongo.errors.ServerSelectionTimeoutError: localhost:27017: [Errno 111] Connection refused
```
**Cause** : Le service MongoDB n'est pas démarré ou n'écoute pas sur le port par défaut.
**Solution** :
- Démarrer le service MongoDB : `sudo systemctl start mongod`
- Vérifier le port dans `settings.py`

**Documentation** : [PyMongo Documentation](https://pymongo.readthedocs.io/)

### 2. Erreur d'authentification
```
pymongo.errors.OperationFailure: Authentication failed
```
**Cause** : Identifiants incorrects ou utilisateur sans privilèges.
**Solution** :
- Vérifier les variables d'environnement MONGODB_URI et MONGODB_DB
- S'assurer que l'utilisateur a les droits nécessaires

## Neo4j Errors

### 1. Erreur de connexion Bolt
```
neo4j.exceptions.ServiceUnavailable: Failed to establish connection to [localhost:7687]
```
**Cause** : Le service Neo4j n'est pas démarré ou le protocole Bolt n'est pas activé.
**Solution** :
- Démarrer le service Neo4j
- Activer le protocole Bolt dans la configuration Neo4j
- Vérifier les paramètres de connexion dans `settings.py`

**Documentation** : [Neo4j Python Driver](https://neo4j.com/docs/api/python-driver/current/)

### 2. Erreur de timeout
```
neo4j.exceptions.TransientError: Database is currently unavailable
```
**Cause** : La base de données met trop de temps à répondre.
**Solution** :
- Augmenter le timeout dans la configuration
- Vérifier la charge du serveur Neo4j

## Synchronisation Errors

### 1. Erreur de synchronisation partielle
```
Error during sync: Some records failed to sync
```
**Cause** : Certains enregistrements n'ont pas pu être synchronisés.
**Solution** :
- Vérifier les logs pour les détails
- Implémenter une logique de réessai
- Vérifier la cohérence des données entre les bases

### 2. Conflit de versions
```
VersionConflict: Document update conflict
```
**Cause** : Tentative de mise à jour simultanée du même document.
**Solution** :
- Implémenter un verrouillage optimiste
- Utiliser des transactions atomiques

## Django Errors

### 1. Erreur de migration
```
django.db.migrations.exceptions.InconsistentMigrationHistory
```
**Cause** : Incohérence dans l'historique des migrations.
**Solution** :
- Supprimer les migrations problématiques
- Faire un `python manage.py migrate --fake`

### 2. Erreur de modèle non chargé
```
django.core.exceptions.AppRegistryNotReady: Apps aren't loaded yet
```
**Cause** : Tentative d'accès aux modèles avant le chargement complet de Django.
**Solution** :
- S'assurer que le code s'exécute après le chargement de Django
- Utiliser `django.apps.apps.ready` si nécessaire

## Bonnes Pratiques

1. **Journalisation**
   - Toujours logger les erreurs avec suffisamment de contexte
   - Utiliser différents niveaux de log (DEBUG, INFO, ERROR)

2. **Gestion des erreurs**
   - Toujours utiliser des blocs try/except spécifiques
   - Fournir des messages d'erreur clairs

3. **Sécurité**
   - Ne jamais exposer d'informations sensibles dans les logs
   - Utiliser des variables d'environnement pour les informations sensibles

## Références
- [Documentation Django](https://docs.djangoproject.com/)
- [Documentation MongoDB](https://docs.mongodb.com/)
- [Documentation Neo4j](https://neo4j.com/docs/)
- [Documentation MySQL](https://dev.mysql.com/doc/)

---
Dernière mise à jour : 15/01/2026
