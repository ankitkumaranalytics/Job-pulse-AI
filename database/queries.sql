-- ============================================================
-- JobPulse AI — Analytical SQL Queries
-- Run these against the jobpulse_db database after loading data.
-- ============================================================

-- ------------------------------------------------------------
-- Query 1: Top 20 most demanded skills
-- Counts how many job postings request each skill (via job_skills).
-- ------------------------------------------------------------
SELECT s.skill_name,
       COUNT(DISTINCT js.job_id) AS demand_count
FROM skills s
JOIN job_skills js ON s.skill_id = js.skill_id
GROUP BY s.skill_name
ORDER BY demand_count DESC
LIMIT 20;

-- ------------------------------------------------------------
-- Query 2: Top hiring companies
-- Companies with the most job postings.
-- ------------------------------------------------------------
SELECT company,
       COUNT(*) AS job_count
FROM jobs
GROUP BY company
ORDER BY job_count DESC
LIMIT 15;

-- ------------------------------------------------------------
-- Query 3: Cities with the highest number of job postings
-- ------------------------------------------------------------
SELECT city AS location,
       COUNT(*) AS job_count
FROM jobs
WHERE city IS NOT NULL
  AND city <> 'Unknown'
GROUP BY city
ORDER BY job_count DESC
LIMIT 15;

-- ------------------------------------------------------------
-- Query 4: Most demanded job roles
-- Uses standardized_job_title.
-- ------------------------------------------------------------
SELECT standardized_job_title AS job_role,
       COUNT(*) AS job_count
FROM jobs
GROUP BY standardized_job_title
ORDER BY job_count DESC;

-- ------------------------------------------------------------
-- Query 5: Average salary by job role
-- ------------------------------------------------------------
SELECT standardized_job_title AS job_role,
       ROUND(AVG(salary_average), 2) AS avg_salary,
       ROUND(MIN(salary_average), 2)    AS min_salary,
       ROUND(MAX(salary_average), 2)    AS max_salary,
       COUNT(*) AS n_jobs
FROM jobs
WHERE salary_average IS NOT NULL
GROUP BY standardized_job_title
ORDER BY avg_salary DESC;

-- ------------------------------------------------------------
-- Query 6: Average salary by experience category
-- ------------------------------------------------------------
SELECT experience_category,
       ROUND(AVG(salary_average), 2) AS avg_salary,
       ROUND(MIN(salary_average), 2)    AS min_salary,
       ROUND(MAX(salary_average), 2)    AS max_salary,
       COUNT(*) AS n_jobs
FROM jobs
WHERE salary_average IS NOT NULL
GROUP BY experience_category
ORDER BY avg_salary DESC;

-- ------------------------------------------------------------
-- Query 7: Highest paying locations
-- Only locations with enough salary records to be meaningful.
-- ------------------------------------------------------------
SELECT city AS location,
       ROUND(AVG(salary_average), 2) AS avg_salary,
       COUNT(*) AS n_jobs
FROM jobs
WHERE salary_average IS NOT NULL
  AND city IS NOT NULL
  AND city <> 'Unknown'
GROUP BY city
HAVING COUNT(*) >= 3
ORDER BY avg_salary DESC
LIMIT 15;

-- ------------------------------------------------------------
-- Query 8: Most demanded skills for Data Analysts
-- ------------------------------------------------------------
SELECT s.skill_name,
       COUNT(DISTINCT js.job_id) AS demand_count
FROM skills s
JOIN job_skills js ON s.skill_id = js.skill_id
JOIN jobs j        ON j.job_id = js.job_id
WHERE j.standardized_job_title = 'Data Analyst'
GROUP BY s.skill_name
ORDER BY demand_count DESC
LIMIT 20;
-- ------------------------------------------------------------
-- Query 9: Most demanded skills for Data Scientists
-- ------------------------------------------------------------
SELECT s.skill_name,
       COUNT(DISTINCT js.job_id) AS demand_count
FROM skills s
JOIN job_skills js ON s.skill_id = js.skill_id
JOIN jobs j        ON j.job_id = js.job_id
WHERE j.standardized_job_title = 'Data Scientist'
GROUP BY s.skill_name
ORDER BY demand_count DESC
LIMIT 20;

-- ------------------------------------------------------------
-- Query 10: Most demanded skill combinations
-- Pairs of skills requested together in the same posting.
-- ------------------------------------------------------------
SELECT a.skill_name AS skill_1,
       b.skill_name AS skill_2,
       COUNT(*) AS combo_count
FROM job_skills ja
JOIN job_skills jb ON ja.job_id = jb.job_id AND ja.skill_id < jb.skill_id
JOIN skills a ON a.skill_id = ja.skill_id
JOIN skills b ON b.skill_id = jb.skill_id
GROUP BY a.skill_name, b.skill_name
ORDER BY combo_count DESC
LIMIT 15;

-- ------------------------------------------------------------
-- Query 11: Monthly job posting trends
-- ------------------------------------------------------------
SELECT TO_CHAR(DATE_TRUNC('month', posting_date), 'YYYY-MM') AS month,
       COUNT(*) AS job_count
FROM jobs
WHERE posting_date IS NOT NULL
GROUP BY DATE_TRUNC('month', posting_date)
ORDER BY month ASC;

-- ------------------------------------------------------------
-- Query 12: Companies requiring the widest range of technical skills
-- ------------------------------------------------------------
SELECT j.company,
       ROUND(AVG(sk.per_job), 2) AS avg_skills_per_job,
       COUNT(*) AS n_jobs
FROM jobs j
JOIN (
    SELECT job_id, COUNT(*) AS per_job
    FROM job_skills
    GROUP BY job_id
) sk ON sk.job_id = j.job_id
GROUP BY j.company
HAVING COUNT(*) >= 3
ORDER BY avg_skills_per_job DESC
LIMIT 15;

-- ------------------------------------------------------------
-- Query 13: Jobs suitable for freshers
-- ------------------------------------------------------------
SELECT job_id,
       job_title,
       company,
       city,
       salary_average,
       experience_category
FROM jobs
WHERE experience_category = 'Fresher'
   OR (experience_min IS NOT NULL AND experience_min <= 1)
ORDER BY posting_date DESC
LIMIT 50;

-- ------------------------------------------------------------
-- Query 14: Skills associated with higher salary
-- Average salary of postings that require each skill.
-- ------------------------------------------------------------
SELECT s.skill_name,
       ROUND(AVG(j.salary_average), 2) AS avg_salary,
       COUNT(DISTINCT js.job_id) AS n_jobs
FROM skills s
JOIN job_skills js    ON s.skill_id = js.skill_id
JOIN jobs j           ON j.job_id = js.job_id
WHERE j.salary_average IS NOT NULL
GROUP BY s.skill_name
HAVING COUNT(DISTINCT js.job_id) >= 10
ORDER BY avg_salary DESC
LIMIT 20;

-- ------------------------------------------------------------
-- Query 15: Job demand by industry
-- ------------------------------------------------------------
SELECT industry,
       COUNT(*) AS job_count,
       ROUND(AVG(salary_average), 2) AS avg_salary
FROM jobs
WHERE industry IS NOT NULL
  AND industry <> 'Other'
GROUP BY industry
ORDER BY job_count DESC;