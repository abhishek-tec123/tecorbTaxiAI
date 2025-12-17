# schema.py

DRIVERS_TABLE = """
CREATE TABLE IF NOT EXISTS drivers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    driver_id VARCHAR(64) UNIQUE,
    external_id VARCHAR(64) UNIQUE,
    name VARCHAR(255),
    phone VARCHAR(64),
    vehicle_id VARCHAR(64),
    status VARCHAR(32),
    current_h3 VARCHAR(32),
    lat DOUBLE,
    lon DOUBLE,
    rating DOUBLE,
    activity_at DATETIME,
    last_update_at DATETIME,
    created_at DATETIME,
    meta JSON
) ENGINE=InnoDB;
"""

RIDERS_TABLE = """
CREATE TABLE IF NOT EXISTS riders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rider_id VARCHAR(64) UNIQUE,
    external_id VARCHAR(64) UNIQUE,
    name VARCHAR(255),
    phone VARCHAR(64),
    lat DOUBLE,
    lon DOUBLE,
    activity_at DATETIME,
    created_at DATETIME,
    meta JSON
) ENGINE=InnoDB;
"""

TRIPS_TABLE = """
CREATE TABLE IF NOT EXISTS trips (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trip_id VARCHAR(64) UNIQUE,
    request_id VARCHAR(64) UNIQUE,
    rider_id VARCHAR(64),
    driver_id VARCHAR(64),
    status VARCHAR(32),
    requested_at DATETIME,
    matched_at DATETIME,
    start_at DATETIME,
    end_at DATETIME,
    pickup_lat DOUBLE,
    pickup_lon DOUBLE,
    drop_lat DOUBLE,
    drop_lon DOUBLE,
    pickup_distance_km DOUBLE,
    ride_distance_km DOUBLE,
    ride_duration_min DOUBLE,
    wait_time_min DOUBLE,
    fare DOUBLE,
    cancellation_reason VARCHAR(255),
    match_quality DOUBLE,
    created_at DATETIME,
    meta JSON
) ENGINE=InnoDB;
"""

TRIP_MATCH_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS trip_match_logs (
    match_id INT AUTO_INCREMENT PRIMARY KEY,
    trip_id VARCHAR(64),
    ts DATETIME NOT NULL,
    driver_id VARCHAR(64),
    rider_id VARCHAR(64),
    distance_km DOUBLE,
    match_status VARCHAR(64),
    matcher_version VARCHAR(64),
    reward_estimate DOUBLE,
    response_time_ms INT,
    INDEX idx_trip_id (trip_id),
    CONSTRAINT fk_trip_match_trip FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
) ENGINE=InnoDB;
"""

H3_HEXES_TABLE = """
CREATE TABLE IF NOT EXISTS h3_hexes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hex_id VARCHAR(32) UNIQUE,
    resolution INT,
    center_lat DOUBLE,
    center_lon DOUBLE,
    area_km2 DOUBLE,
    area_m2 DOUBLE,
    edge_length_km DOUBLE,
    inside_polygon TINYINT,
    point_hex TINYINT,
    driver_count INT DEFAULT 0,
    rider_count INT DEFAULT 0,
    created_at DATETIME
) ENGINE=InnoDB;
"""

# List of tables in creation order (important for foreign keys)
ALL_TABLES = [
    DRIVERS_TABLE,
    RIDERS_TABLE,
    TRIPS_TABLE,
    TRIP_MATCH_LOGS_TABLE,
    H3_HEXES_TABLE
]


HEX_LIST = [
    "872a1001cffffff", "872a1008cffffff", "872a100a4ffffff", "872a100d2ffffff", "872a1000affffff",
    "872a100a9ffffff", "872a1018bffffff", "872a100d3ffffff", "872a100d4ffffff", "872a100f2ffffff",
    "872a10011ffffff", "872a100aaffffff", "872a100f6ffffff", "872a10014ffffff", "872a10012ffffff",
    "872a10002ffffff", "872a1008dffffff", "872a100adffffff", "872a10003ffffff", "872a100a0ffffff",
    "872a1072dffffff", "872a10088ffffff", "872a10018ffffff", "872a1001effffff", "872a100acffffff",
    "872a100abffffff", "872a1001dffffff", "872a100d0ffffff", "872a100a8ffffff", "872a10015ffffff",
    "872a100a1ffffff", "872a100d6ffffff", "872a100a5ffffff", "872a10016ffffff", "872a10725ffffff",
    "872a10033ffffff", "872a10019ffffff", "872a10013ffffff", "872a10089ffffff", "872a100aeffffff",
    "872a1072cffffff", "872a1001bffffff", "872a100a3ffffff", "872a10728ffffff", "872a100f4ffffff",
    "872a10189ffffff", "872a10721ffffff", "872a10010ffffff", "872a1008bffffff", "872a1001affffff",
]
