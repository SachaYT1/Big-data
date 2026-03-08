-- ScyllaDB schema for Foursquare slice (query-driven design)

CREATE KEYSPACE IF NOT EXISTS foursquaredb
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 3};

USE foursquaredb;

-- Core entities
CREATE TABLE IF NOT EXISTS users_by_id (
    userid bigint PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS pois_by_id (
    poi_id text PRIMARY KEY,
    latitude double,
    longitude double,
    category text,
    country text,
    custom_category text
);

CREATE TABLE IF NOT EXISTS checkins_by_user (
    userid bigint,
    checkin_time text,
    poi_id text,
    tz_offset_minutes smallint,
    PRIMARY KEY ((userid), checkin_time, poi_id)
);

CREATE TABLE IF NOT EXISTS checkins_by_poi (
    poi_id text,
    checkin_time text,
    userid bigint,
    tz_offset_minutes smallint,
    PRIMARY KEY ((poi_id), checkin_time, userid)
);

CREATE TABLE IF NOT EXISTS friendship_before_by_user (
    userid bigint,
    friendid bigint,
    PRIMARY KEY ((userid), friendid)
);

CREATE TABLE IF NOT EXISTS friendship_after_by_user (
    userid bigint,
    friendid bigint,
    PRIMARY KEY ((userid), friendid)
);

CREATE TABLE IF NOT EXISTS stable_friendship_by_user (
    userid bigint,
    friendid bigint,
    PRIMARY KEY ((userid), friendid)
);

-- Query-serving tables
CREATE TABLE IF NOT EXISTS q1_top_countries (
    bucket int,
    total_checkins bigint,
    country text,
    PRIMARY KEY ((bucket), total_checkins, country)
) WITH CLUSTERING ORDER BY (total_checkins DESC, country ASC);

CREATE TABLE IF NOT EXISTS q2_recommendations_global (
    bucket int,
    score bigint,
    userid bigint,
    poi_id text,
    category text,
    country text,
    PRIMARY KEY ((bucket), score, userid, poi_id)
) WITH CLUSTERING ORDER BY (score DESC, userid ASC, poi_id ASC);

CREATE TABLE IF NOT EXISTS q3_attractive_venues_global (
    bucket int,
    total_shares bigint,
    poi_id text,
    category text,
    country text,
    latitude double,
    longitude double,
    PRIMARY KEY ((bucket), total_shares, poi_id)
) WITH CLUSTERING ORDER BY (total_shares DESC, poi_id ASC);

CREATE TABLE IF NOT EXISTS q4_custom_category_counts (
    custom_category text PRIMARY KEY,
    venue_count bigint
);
