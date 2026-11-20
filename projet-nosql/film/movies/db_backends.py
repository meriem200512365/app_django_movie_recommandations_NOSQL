import os
from django.conf import settings


def get_mongo_db():
    try:
        from pymongo import MongoClient
    except Exception:
        raise RuntimeError('pymongo is required for MongoDB integration. pip install pymongo')
    uri = getattr(settings, 'MONGODB_URI', 'mongodb://localhost:27017')
    client = MongoClient(uri, serverSelectionTimeoutMS=2000)
    dbname = getattr(settings, 'MONGODB_DB', 'film_mongo')
    return client[dbname]


def get_neo4j_driver():
    try:
        from neo4j import GraphDatabase
    except Exception:
        raise RuntimeError('neo4j-driver is required for Neo4j integration. pip install neo4j')
    uri = getattr(settings, 'NEO4J_URI', 'bolt://localhost:7687')
    user = getattr(settings, 'NEO4J_USER', 'neo4j')
    password = getattr(settings, 'NEO4J_PASSWORD', '')
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password), connection_timeout=2)
        # Test the connection immediately
        with driver.session() as session:
            session.run("RETURN 1")
        return driver
    except Exception as e:
        print(f"[Neo4j Error] Failed to connect to {uri}: {str(e)}")
        return None
