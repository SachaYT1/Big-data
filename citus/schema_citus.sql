-- Citus schema for Foursquare slice
-- Database: foursquaredb

CREATE EXTENSION IF NOT EXISTS citus;

DROP TABLE IF EXISTS checkins CASCADE;
DROP TABLE IF EXISTS friendship_before CASCADE;
DROP TABLE IF EXISTS friendship_after CASCADE;
DROP TABLE IF EXISTS pois CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    userid BIGINT PRIMARY KEY
);

CREATE TABLE pois (
    poi_id TEXT PRIMARY KEY,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    category TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE checkins (
    checkin_id BIGSERIAL,
    userid BIGINT NOT NULL,
    poi_id TEXT NOT NULL,
    checkin_time_text TEXT NOT NULL,
    tz_offset_minutes SMALLINT NOT NULL
);

CREATE TABLE friendship_before (
    userid BIGINT NOT NULL,
    friendid BIGINT NOT NULL,
    PRIMARY KEY (userid, friendid)
);

CREATE TABLE friendship_after (
    userid BIGINT NOT NULL,
    friendid BIGINT NOT NULL,
    PRIMARY KEY (userid, friendid)
);

-- Citus distribution strategy:
-- - checkins / friendship_before / friendship_after / users distributed by userid
-- - pois as reference table to make poi joins local on workers
SELECT create_distributed_table('users', 'userid');
SELECT create_distributed_table('checkins', 'userid');
SELECT create_distributed_table('friendship_before', 'userid');
SELECT create_distributed_table('friendship_after', 'userid');
SELECT create_reference_table('pois');

-- Important indexes for analytics
CREATE INDEX idx_citus_checkins_userid ON checkins(userid);
CREATE INDEX idx_citus_checkins_poi_id ON checkins(poi_id);
CREATE INDEX idx_citus_checkins_userid_poi_id ON checkins(userid, poi_id);
CREATE INDEX idx_citus_pois_country ON pois(country);
CREATE INDEX idx_citus_friendship_before_friendid ON friendship_before(friendid);
CREATE INDEX idx_citus_friendship_after_friendid ON friendship_after(friendid);
CREATE INDEX idx_citus_pois_category_tsv
ON pois
USING GIN (to_tsvector('english', category));
