-- ============================================================
-- JobPulse AI — PostgreSQL Schema
-- Database: jobpulse_db
-- ============================================================

-- Drop tables in dependency order (for clean re-runs)
DROP TABLE IF EXISTS job_skills CASCADE;
DROP TABLE IF EXISTS skills CASCADE;
DROP TABLE IF EXISTS jobs CASCADE;

-- ------------------------------------------------------------
-- Table: jobs
-- Stores processed job postings
-- ------------------------------------------------------------
CREATE TABLE jobs (
    job_id                 VARCHAR(50) PRIMARY KEY,
    job_title              TEXT,
    standardized_job_title VARCHAR(100),
    company                VARCHAR(200),
    location               VARCHAR(100),
    city                   VARCHAR(100),
    state                  VARCHAR(100),
    country                VARCHAR(50),
    industry               VARCHAR(100),
    salary_min             NUMERIC(15,2),
    salary_max             NUMERIC(15,2),
    salary_average         NUMERIC(15,2),
    currency               VARCHAR(10) DEFAULT 'INR',
    experience_min         NUMERIC(5,2),
    experience_max         NUMERIC(5,2),
    experience_category    VARCHAR(50),
    employment_type        VARCHAR(50),
    posting_date           TIMESTAMP,
    job_description        TEXT,
    created_at             TIMESTAMP DEFAULT NOW()
);

-- Indexes for frequently queried columns
CREATE INDEX idx_jobs_title    ON jobs (standardized_job_title);
CREATE INDEX idx_jobs_company  ON jobs (company);
CREATE INDEX idx_jobs_location ON jobs (location);
CREATE INDEX idx_jobs_city     ON jobs (city);
CREATE INDEX idx_jobs_salary   ON jobs (salary_average);
CREATE INDEX idx_jobs_date     ON jobs (posting_date);
CREATE INDEX idx_jobs_industry ON jobs (industry);

-- ------------------------------------------------------------
-- Table: skills
-- Stores the skill dictionary (canonical skill names)
-- ------------------------------------------------------------
CREATE TABLE skills (
    skill_id       VARCHAR(100) PRIMARY KEY,
    skill_name     VARCHAR(200) UNIQUE NOT NULL,
    skill_category VARCHAR(100)
);

-- ------------------------------------------------------------
-- Table: job_skills
-- Many-to-many mapping between jobs and skills
-- ------------------------------------------------------------
CREATE TABLE job_skills (
    job_id   VARCHAR(50)  NOT NULL REFERENCES jobs (job_id) ON DELETE CASCADE,
    skill_id VARCHAR(100) NOT NULL REFERENCES skills (skill_id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, skill_id)
);

CREATE INDEX idx_job_skills_skill ON job_skills (skill_id);
CREATE INDEX idx_job_skills_job   ON job_skills (job_id);