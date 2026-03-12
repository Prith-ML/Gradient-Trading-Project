-- ============================================================================
-- USPTO Patent Data Schema (PatentsView)
-- Normalized schema for granted patents, inventors, assignees, applications
-- ============================================================================

-- ============================================================================
-- 1. PATENTS TABLE
-- Core patent metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS patents (
    patent_id VARCHAR(20) PRIMARY KEY,
    patent_type VARCHAR(100),
    patent_date DATE,
    patent_title TEXT,
    wipo_kind VARCHAR(10),
    num_claims INTEGER,
    withdrawn INTEGER DEFAULT 0,
    filename VARCHAR(120),
    inserted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_patents_date ON patents(patent_date);
CREATE INDEX IF NOT EXISTS idx_patents_type ON patents(patent_type);


-- ============================================================================
-- 2. APPLICATIONS TABLE
-- Patent application information
-- ============================================================================
CREATE TABLE IF NOT EXISTS applications (
    application_id VARCHAR(36) PRIMARY KEY,
    patent_id VARCHAR(20) NOT NULL REFERENCES patents(patent_id) ON DELETE CASCADE,
    patent_application_type VARCHAR(20),
    filing_date DATE,
    series_code VARCHAR(20),
    rule_47_flag BIGINT,
    inserted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_applications_patent_id ON applications(patent_id);
CREATE INDEX IF NOT EXISTS idx_applications_filing_date ON applications(filing_date);


-- ============================================================================
-- 3. INVENTORS TABLE (disambiguated)
-- ============================================================================
CREATE TABLE IF NOT EXISTS inventors (
    inventor_id VARCHAR(128) PRIMARY KEY,
    disambig_inventor_name_first TEXT,
    disambig_inventor_name_last TEXT,
    gender_code VARCHAR(1),
    location_id VARCHAR(128),
    inserted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inventors_location ON inventors(location_id);


-- ============================================================================
-- 4. PATENT_INVENTORS (many-to-many)
-- ============================================================================
CREATE TABLE IF NOT EXISTS patent_inventors (
    patent_id VARCHAR(20) NOT NULL REFERENCES patents(patent_id) ON DELETE CASCADE,
    inventor_id VARCHAR(128) NOT NULL REFERENCES inventors(inventor_id) ON DELETE CASCADE,
    inventor_sequence INTEGER NOT NULL,
    PRIMARY KEY (patent_id, inventor_id)
);

CREATE INDEX IF NOT EXISTS idx_patent_inventors_inventor ON patent_inventors(inventor_id);


-- ============================================================================
-- 5. ASSIGNEES TABLE (disambiguated)
-- ============================================================================
CREATE TABLE IF NOT EXISTS assignees (
    assignee_id VARCHAR(36) PRIMARY KEY,
    disambig_assignee_individual_name_first VARCHAR(96),
    disambig_assignee_individual_name_last VARCHAR(96),
    disambig_assignee_organization VARCHAR(256),
    assignee_type INTEGER,
    location_id VARCHAR(128),
    inserted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assignees_organization ON assignees(disambig_assignee_organization);
CREATE INDEX IF NOT EXISTS idx_assignees_type ON assignees(assignee_type);


-- ============================================================================
-- 6. PATENT_ASSIGNEES (many-to-many)
-- ============================================================================
CREATE TABLE IF NOT EXISTS patent_assignees (
    patent_id VARCHAR(20) NOT NULL REFERENCES patents(patent_id) ON DELETE CASCADE,
    assignee_id VARCHAR(36) NOT NULL REFERENCES assignees(assignee_id) ON DELETE CASCADE,
    assignee_sequence INTEGER NOT NULL,
    PRIMARY KEY (patent_id, assignee_id)
);

CREATE INDEX IF NOT EXISTS idx_patent_assignees_assignee ON patent_assignees(assignee_id);


-- ============================================================================
-- 7. LOCATIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS locations (
    location_id VARCHAR(128) PRIMARY KEY,
    disambig_city VARCHAR(128),
    disambig_state VARCHAR(20),
    disambig_country VARCHAR(16),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    county VARCHAR(60),
    state_fips VARCHAR(2),
    county_fips VARCHAR(6),
    inserted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


-- ============================================================================
-- 8. CPC CLASSIFICATIONS (at issue)
-- ============================================================================
CREATE TABLE IF NOT EXISTS patent_cpc (
    patent_id VARCHAR(20) NOT NULL REFERENCES patents(patent_id) ON DELETE CASCADE,
    cpc_sequence INTEGER NOT NULL,
    cpc_section VARCHAR(10),
    cpc_class VARCHAR(20),
    cpc_subclass VARCHAR(20),
    cpc_group VARCHAR(32),
    cpc_type VARCHAR(36),
    PRIMARY KEY (patent_id, cpc_sequence)
);

CREATE INDEX IF NOT EXISTS idx_patent_cpc_class ON patent_cpc(cpc_class);


-- ============================================================================
-- 9. INGESTION_RUNS (pipeline tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS uspto_ingestion_runs (
    run_id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    source_url TEXT,
    table_name VARCHAR(100),
    rows_loaded INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    CONSTRAINT uspto_status_valid CHECK (status IN ('success', 'partial', 'running', 'error'))
);

CREATE INDEX IF NOT EXISTS idx_uspto_ingestion_started ON uspto_ingestion_runs(started_at);
