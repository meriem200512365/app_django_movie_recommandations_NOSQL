PRAGMA foreign_keys = ON;

CREATE TABLE auth_user (
    id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    password varchar(128) NOT NULL,
    last_login datetime NULL,
    is_superuser bool NOT NULL,
    username varchar(150) NOT NULL UNIQUE,
    first_name varchar(150) NOT NULL,
    last_name varchar(150) NOT NULL,
    email varchar(254) NOT NULL,
    is_staff bool NOT NULL,
    is_active bool NOT NULL,
    date_joined datetime NOT NULL
);

CREATE TABLE movies_movie (
    id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    title varchar(255) NOT NULL,
    year integer NULL,
    duration integer NULL
);

CREATE TABLE movies_rating (
    id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    user_id integer NOT NULL,
    movie_id integer NOT NULL,
    score integer NOT NULL,
    created_at datetime NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT unique_user_movie UNIQUE (user_id, movie_id),
    FOREIGN KEY(user_id) REFERENCES auth_user(id) ON DELETE CASCADE,
    FOREIGN KEY(movie_id) REFERENCES movies_movie(id) ON DELETE CASCADE
);

CREATE TABLE movies_review (
    id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    user_id integer NOT NULL,
    movie_id integer NOT NULL,
    content text NOT NULL,
    created_at datetime NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES auth_user(id) ON DELETE CASCADE,
    FOREIGN KEY(movie_id) REFERENCES movies_movie(id) ON DELETE CASCADE
);

CREATE TABLE movies_watchlist (
    id integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    user_id integer NOT NULL,
    movie_id integer NOT NULL,
    added_at datetime NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT unique_watchlist_entry UNIQUE (user_id, movie_id),
    FOREIGN KEY(user_id) REFERENCES auth_user(id) ON DELETE CASCADE,
    FOREIGN KEY(movie_id) REFERENCES movies_movie(id) ON DELETE CASCADE
);