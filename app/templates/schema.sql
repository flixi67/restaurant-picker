-- ========================
-- Core Tables
-- ========================

-- Meetings (Parent table)
CREATE TABLE meetings (
    id VARCHAR(12) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    datetime TEXT NOT NULL,
    group_size INTEGER CHECK (group_size > 0),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Restaurants (Standalone master data)
CREATE TABLE restaurants (
    id VARCHAR(100) PRIMARY KEY,
    meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    rating DECIMAL(3, 2) CHECK (rating BETWEEN 0 AND 5),
    googleMapsUri VARCHAR(200) NOT NULL,
    websiteUri VARCHAR(200),
    formattedAddress VARCHAR(200),
    internationalPhoneNumber VARCHAR(20),
    primaryType VARCHAR(50),
    userRatingCount INTEGER CHECK (userRatingCount > 0),
    servesVegetarianFood INTEGER DEFAULT 0,
    paymentOptions_acceptsCashOnly INTEGER DEFAULT 0,
    priceRange_startPrice_units DECIMAL,
    priceRange_endPrice_units DECIMAL,
    priceLevel VARCHAR(50)
);

-- ========================
-- Transactional Tables
-- ========================

-- Members (Joins meetings → users)
CREATE TABLE members (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)), 2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) || substr(hex(randomblob(2)), 2) || '-' || hex(randomblob(6)))),
    meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    budget INTEGER CHECK (budget BETWEEN 1 AND 4),
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
    score REAL,             -- Add your scoring metric here
    ranking INTEGER,           -- Add rank (e.g., 1st, 2nd, 3rd)
    UNIQUE (meeting_id, restaurant_id) -- Prevent duplicates
);
