-- Existing core tables
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    duration INTEGER,  -- Duration in seconds
    checksum TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'inactive',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS playlist_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL,
    type TEXT NOT NULL,  -- 'once', 'daily', 'weekly'
    datetime DATETIME,   -- For 'once' type
    time TIME,          -- For 'daily' and 'weekly' types
    days TEXT,          -- For 'weekly' type, comma-separated days (0-6)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (playlist_id) REFERENCES playlists (id)
);

CREATE TABLE IF NOT EXISTS playlist_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL,
    played_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (playlist_id) REFERENCES playlists (id)
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

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS media_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    FOREIGN KEY (media_id) REFERENCES media (id),
    FOREIGN KEY (tag_id) REFERENCES tags (id),
    UNIQUE(media_id, tag_id)
);

-- New ad management system tables
CREATE TABLE IF NOT EXISTS ad_campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_date DATETIME,
    end_date DATETIME,
    target_percentage FLOAT,
    status TEXT DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ad_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER,
    media_id INTEGER NOT NULL,
    type TEXT NOT NULL,  -- 'audio', 'image', 'video'
    duration INTEGER,
    weight INTEGER DEFAULT 1,
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES ad_campaigns(id),
    FOREIGN KEY (media_id) REFERENCES media(id)
);

CREATE TABLE IF NOT EXISTS ad_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER,
    playlist_id INTEGER,
    frequency INTEGER,  -- How often the ad should play (e.g., every N songs)
    priority INTEGER,   -- Higher priority ads get played first
    start_time TIME,    -- Optional time-of-day restrictions
    end_time TIME,
    days_of_week TEXT,  -- Comma-separated days (e.g., "1,2,3,4,5" for weekdays)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES ad_campaigns(id),
    FOREIGN KEY (playlist_id) REFERENCES playlists(id)
);

CREATE TABLE IF NOT EXISTS ad_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER,
    asset_id INTEGER,
    playlist_id INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    duration INTEGER,    -- How long the ad played
    completed BOOLEAN,   -- Whether the ad played to completion
    FOREIGN KEY (campaign_id) REFERENCES ad_campaigns(id),
    FOREIGN KEY (asset_id) REFERENCES ad_assets(id),
    FOREIGN KEY (playlist_id) REFERENCES playlists(id)
);

-- Legacy ads table (will be dropped after migration)
CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL,
    weight INTEGER DEFAULT 1,
    active BOOLEAN DEFAULT 1,
    FOREIGN KEY (media_id) REFERENCES media (id)
);

-- Create default campaign for legacy ads
INSERT OR IGNORE INTO ad_campaigns (name, status)
VALUES ('Legacy Campaign', 'active');

-- Migrate any existing ads to ad_assets
INSERT OR IGNORE INTO ad_assets (media_id, weight, active, campaign_id)
SELECT 
    media_id,
    weight,
    active,
    (SELECT id FROM ad_campaigns WHERE name = 'Legacy Campaign')
FROM ads
WHERE media_id NOT IN (SELECT media_id FROM ad_assets);

-- Drop the legacy table
DROP TABLE IF EXISTS ads;
