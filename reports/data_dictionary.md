# JobPulse AI — Data Dictionary

This document describes every column used in the JobPulse AI pipeline
and dashboard. Columns marked **(engineered)** are created by the
feature-engineering / skill-extraction steps, not present in the raw input.

---

## Raw Data Columns

### job_id
- **Description:** Unique identifier for each job posting.
- **Data Type:** Text (String)
- **Example:** `JOB-000001`

### job_title
- **Description:** Title of the job as posted by the employer.
- **Data Type:** Text (String)
- **Example:** `Senior Data Analyst`

### company
- **Description:** Name of the hiring company.
- **Data Type:** Text (String)
- **Example:** `TechNova Solutions`

### location
- **Description:** General location / region of the job.
- **Data Type:** Text (String)
- **Example:** `Bangalore`

### city
- **Description:** City where the job is based.
- **Data Type:** Text (String)
- **Example:** `Hyderabad`

### state
- **Description:** State or province.
- **Data Type:** Text (String)
- **Example:** `Telangana`

### country
- **Description:** Country of the job posting.
- **Data Type:** Text (String)
- **Example:** `India`

### industry
- **Description:** Industry sector of the employer.
- **Data Type:** Text (String)
- **Example:** `Information Technology`

### salary
- **Description:** Raw salary text (as posted).
- **Data Type:** Text (String)
- **Example:** `12 LPA`

### salary_min
- **Description:** Minimum annual salary (numeric).
- **Data Type:** Number (Float)
- **Example:** `600000`

### salary_max
- **Description:** Maximum annual salary (numeric).
- **Data Type:** Number (Float)
- **Example:** `900000`

### currency
- **Description:** Currency code.
- **Data Type:** Text (String)
- **Example:** `INR`

### experience
- **Description:** Raw experience requirement text.
- **Data Type:** Text (String)
- **Example:** `3-5 years`

### experience_min
- **Description:** Minimum years of experience required.
- **Data Type:** Number (Float)
- **Example:** `3`

### experience_max
- **Description:** Maximum years of experience required.
- **Data Type:** Number (Float)
- **Example:** `5`

### employment_type
- **Description:** Full-time / Contract / Internship, etc.
- **Data Type:** Text (String)
- **Example:** `Full-time`

### posting_date
- **Description:** Date the job was posted.
- **Data Type:** Date (YYYY-MM-DD)
- **Example:** `2025-06-15`

### job_description
- **Description:** Full job description text (used for skill extraction).
- **Data Type:** Text (String, long)
- **Example:** `"We are hiring a Data Analyst at ..."`

### skills
- **Description:** Comma-separated list of skills as posted.
- **Data Type:** Text (String)
- **Example:** `Python, SQL, Power BI`

---

## Engineered Columns

### standardized_job_title
- **Description:** Job title mapped to a canonical role category.
- **Data Type:** Text (String, categorical)
- **Example:** `Data Analyst`
- **Categories:** `Data Analyst`, `Business Analyst`, `Data Scientist`,
  `Data Engineer`, `Machine Learning Engineer`, `BI Analyst`,
  `Analytics Engineer`, `Other`

### normalized_location
- **Description:** Location mapped to a canonical city name.
- **Data Type:** Text (String)
- **Example:** `Bangalore` (from `Bengaluru`)

### salary_average
- **Description:** Mean of `salary_min` and `salary_max`.
- **Data Type:** Number (Float)
- **Example:** `750000`

### experience_category
- **Description:** Experience requirement bucketed into levels.
- **Data Type:** Text (String, categorical)
- **Example:** `Mid Level`
- **Categories:** `Fresher`, `Entry Level`, `Mid Level`, `Senior Level`, `Not Specified`

### extracted_skills
- **Description:** Deduplicated list of canonical skill names extracted
  from `skills` and `job_description`.
- **Data Type:** List[String]
- **Example:** `["Python", "SQL", "Power BI"]`

### skills_count
- **Description:** Number of distinct extracted skills per job.
- **Data Type:** Number (Integer)
- **Example:** `5`

### posting_month
- **Description:** Month extracted from `posting_date`.
- **Data Type:** Number (Integer)
- **Example:** `6`

### posting_year
- **Description:** Year extracted from `posting_date`.
- **Data Type:** Number (Integer)
- **Example:** `2025`

### posting_weekday
- **Description:** Day-of-week of `posting_date`.
- **Data Type:** Text (String)
- **Example:** `Monday`

### job_age_days
- **Description:** Days between posting date and today.
- **Data Type:** Number (Integer)
- **Example:** `45`

---

## Database Tables

| Table        | Description                                           |
|--------------|-------------------------------------------------------|
| `jobs`       | One row per job posting (with engineered features)    |
| `skills`     | Canonical skill dictionary with categories            |
| `job_skills` | Many-to-many mapping between jobs and skills          |

---

## Power BI Exported Files

| File                  | Description                                |
|-----------------------|--------------------------------------------|
| `jobs_processed.csv`  | Main fact table (all jobs + features)      |
| `skills_summary.csv`  | Skill demand ranking                       |
| `company_summary.csv` | Company posting counts                     |
| `location_summary.csv`| Location posting counts                    |
| `salary_summary.csv`  | Salary stats by job role                   |