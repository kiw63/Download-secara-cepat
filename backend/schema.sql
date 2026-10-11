PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id TEXT PRIMARY KEY,
 display_name TEXT NOT NULL,
 created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS videos (
 id TEXT PRIMARY KEY,
 owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 title TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 storage_key TEXT,
 storage_status TEXT NOT NULL DEFAULT 'local'
   CHECK(storage_status IN ('local','uploading','online','failed')),
 visibility TEXT NOT NULL DEFAULT 'private'
   CHECK(visibility IN ('private','public')),
 created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_videos_owner_created ON videos(owner_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_videos_public_feed ON videos(visibility,storage_status,created_at DESC);
