-- PostgreSQL schema for Foursquare slice
-- Database: foursquaredb

CREATE TABLE IF NOT EXISTS users (
    userid BIGINT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS pois (
    poi_id TEXT PRIMARY KEY,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    category TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checkins (
    checkin_id BIGSERIAL PRIMARY KEY,
    userid BIGINT NOT NULL REFERENCES users(userid),
    poi_id TEXT NOT NULL REFERENCES pois(poi_id),
    checkin_time_text TEXT NOT NULL,
    tz_offset_minutes SMALLINT NOT NULL
);

CREATE TABLE IF NOT EXISTS friendship_before (
    userid BIGINT NOT NULL REFERENCES users(userid),
    friendid BIGINT NOT NULL REFERENCES users(userid),
    PRIMARY KEY (userid, friendid)
);

CREATE TABLE IF NOT EXISTS friendship_after (
    userid BIGINT NOT NULL REFERENCES users(userid),
    friendid BIGINT NOT NULL REFERENCES users(userid),
    PRIMARY KEY (userid, friendid)
);

-- Critical indexes for analytics
CREATE INDEX IF NOT EXISTS idx_checkins_userid ON checkins(userid);
CREATE INDEX IF NOT EXISTS idx_checkins_poi_id ON checkins(poi_id);
CREATE INDEX IF NOT EXISTS idx_checkins_userid_poi_id ON checkins(userid, poi_id);
CREATE INDEX IF NOT EXISTS idx_pois_country ON pois(country);
CREATE INDEX IF NOT EXISTS idx_friendship_before_friendid ON friendship_before(friendid);
CREATE INDEX IF NOT EXISTS idx_friendship_after_friendid ON friendship_after(friendid);

-- Full-text index for Q4 custom category mapping
CREATE INDEX IF NOT EXISTS idx_pois_category_tsv
ON pois
USING GIN (to_tsvector('english', category));
