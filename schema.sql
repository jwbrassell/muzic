CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    artist TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS playlist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL,
    media_id INTEGER NOT NULL,
    order_position INTEGER NOT NULL,
    FOREIGN KEY (playlist_id) REFERENCES playlists (id),
    FOREIGN KEY (media_id) REFERENCES media (id)
);

CREATE TABLE IF NOT EXISTS subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_text TEXT,
    active BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL,
    weight INTEGER DEFAULT 1,
    active BOOLEAN DEFAULT 1,
    FOREIGN KEY (media_id) REFERENCES media (id)
);

CREATE TABLE IF NOT EXISTS playlist_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL,
    current_position INTEGER NOT NULL DEFAULT 0,
    last_ad_position INTEGER NOT NULL DEFAULT 0,
    is_repeat BOOLEAN NOT NULL DEFAULT 1,
    is_shuffle BOOLEAN NOT NULL DEFAULT 0,
    shuffle_queue TEXT,
    FOREIGN KEY (playlist_id) REFERENCES playlists (id)
);
