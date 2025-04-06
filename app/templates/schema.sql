-- ========================
-- Core Tables
-- ========================

-- Meetings (Parent table)
CREATE TABLE meetings (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)), 2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) || substr(hex(randomblob(2)), 2) || '-' || hex(randomblob(6)))),
    name VARCHAR(100) NOT NULL,
    datetime TEXT NOT NULL,
    group_size INTEGER CHECK (group_size > 0),
    budget INTEGER NOT NULL CHECK (budget BETWEEN 1 AND 3), -- 1=$, 2=$$, 3=$$$
    uses_cash INTEGER DEFAULT FALSE,
    uses_card INTEGER DEFAULT FALSE,
    is_vegetarian INTEGER DEFAULT FALSE,
    lat REAL NOT NULL,
    lng REAL NOT NULL, -- PostGIS for spatial queries
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Restaurants (Standalone master data)
CREATE TABLE restaurants (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)), 2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) || substr(hex(randomblob(2)), 2) || '-' || hex(randomblob(6)))),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    lat DECIMAL(10, 8) NOT NULL,
    lng DECIMAL(11, 8) NOT NULL,
    price_range INTEGER CHECK (price_range BETWEEN 1 AND 3),
    accepts_cash INTEGER DEFAULT FALSE,
    accepts_card INTEGER DEFAULT FALSE,
    vegetarian_friendly INTEGER DEFAULT FALSE,
    rating DECIMAL(3, 2) CHECK (rating BETWEEN 0 AND 5),
    UNIQUE (lat, lng) -- Prevent duplicate locations
);

-- ========================
-- Transactional Tables
-- ========================

-- Members (Joins meetings → users)
CREATE TABLE members (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)), 2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) || substr(hex(randomblob(2)), 2) || '-' || hex(randomblob(6)))),
    meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    budget INTEGER CHECK (budget BETWEEN 1 AND 3),
    uses_cash INTEGER DEFAULT FALSE,
    uses_card INTEGER DEFAULT FALSE,
    is_vegetarian INTEGER DEFAULT FALSE,
    location_preference VARCHAR(100),
    CONSTRAINT valid_payment_method CHECK (uses_cash OR uses_card)
);

-- Top Restaurants (Temporal relationship table)
CREATE TABLE top_restaurants (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)), 2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) || substr(hex(randomblob(2)), 2) || '-' || hex(randomblob(6)))),
    meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    restaurant_id TEXT NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT TRUE,
    UNIQUE (meeting_id, restaurant_id) -- Prevent duplicates
);

-- ========================
-- Performance Optimizations
-- ========================

-- Indexes for frequent filters
CREATE INDEX idx_meetings_datetime ON meetings(datetime);
CREATE INDEX idx_restaurants_veg ON restaurants(vegetarian_friendly) WHERE vegetarian_friendly = TRUE;
CREATE INDEX idx_top_restaurants_active ON top_restaurants(meeting_id) WHERE is_active = TRUE;
