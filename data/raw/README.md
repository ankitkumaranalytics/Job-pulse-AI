# Raw Data Directory

Place the raw job-postings CSV file (named `jobs.csv` by default) in this folder.

The CSV should contain columns such as:

| column            | description                                   |
|-------------------|-----------------------------------------------|
| job_id            | Unique identifier for each job posting      |
| job_title         | Title of the job                              |
| company           | Company offering the job                      |
| location          | General location (city/region)                |
| city              | City name                                     |
| state             | State or province                             |
| country           | Country (e.g. India)                          |
| industry          | Industry sector                               |
| salary            | Raw salary text                               |
| salary_min        | Minimum salary (numeric)                      |
| salary_max        | Maximum salary (numeric)                      |
| currency          | Currency code (e.g. INR)                      |
| experience        | Experience requirement text                   |
| experience_min    | Minimum experience in years (numeric)         |
| experience_max    | Maximum experience in years (numeric)          |
| employment_type   | Full-time, Part-time, Contract, etc.          |
| posting_date      | Date the job was posted                       |
| job_description   | Full job description text                     |
| skills            | Comma-separated list of skills                |

---

**Note:** If no real dataset is available, run `python scripts/generate_sample_data.py`
to generate a realistic synthetic dataset (clearly labelled as sample data).
