-- Properties are global (shared across all users/searches)
CREATE TABLE IF NOT EXISTS properties (
    id                      BIGSERIAL PRIMARY KEY,
    rightmove_id            BIGINT NOT NULL UNIQUE,
    link                    TEXT NOT NULL UNIQUE,
    sqm                     DOUBLE PRECISION,
    price                   INTEGER,
    price_per_sqm           DOUBLE PRECISION,
    address                 TEXT,
    property_listing_type   TEXT,
    preview_data            JSONB,
    preview_fetched_at      TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS searches (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    query_url       TEXT NOT NULL,
    search_type     TEXT NOT NULL DEFAULT 'Sale',
    label           TEXT,
    sqm_min         DOUBLE PRECISION NOT NULL DEFAULT 0,
    sqm_max         DOUBLE PRECISION NOT NULL DEFAULT 999,
    max_pages       INTEGER NOT NULL DEFAULT 10,
    status          TEXT NOT NULL DEFAULT 'pending',
    progress        INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT,
    total_found     INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS searches_user_id_idx ON searches(user_id);

CREATE TABLE IF NOT EXISTS search_properties (
    search_id       BIGINT NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
    property_id     BIGINT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    PRIMARY KEY (search_id, property_id)
);

CREATE INDEX IF NOT EXISTS search_properties_property_id_idx ON search_properties(property_id);

CREATE TABLE IF NOT EXISTS property_statuses (
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    property_id     BIGINT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'unreviewed',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, property_id)
);

-- Row-level security (defense in depth; backend already filters by user_id)
ALTER TABLE searches ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS searches_policy ON searches;
CREATE POLICY searches_policy ON searches
    USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

ALTER TABLE property_statuses ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS statuses_policy ON property_statuses;
CREATE POLICY statuses_policy ON property_statuses
    USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
