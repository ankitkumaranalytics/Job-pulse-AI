"""Job entity — a safe, typed view over one row of the jobs dataset."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Job:
    """Normalized view of a job posting row (never raises on missing data)."""

    job_id: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    role: str = ""
    experience_category: str = ""
    salary_average: float | None = None
    skills: list[str] = field(default_factory=list)
    description: str = ""

    @classmethod
    def from_row(cls, row) -> "Job":
        """Build a Job from a pandas Series, tolerating any missing column."""

        def get(key, default=None):
            try:
                value = row.get(key, default)
            except (AttributeError, KeyError):
                return default
            if value is None or value != value:  # NaN guard
                return default
            return value

        skills = get("extracted_skills", [])
        if isinstance(skills, (list, tuple, set)):
            skill_list = [str(s) for s in skills]
        elif skills and str(skills).strip():
            skill_list = [s.strip() for s in str(skills).split(",") if s.strip()]
        else:
            skill_list = []

        salary = get("salary_average")
        return cls(
            job_id=str(get("job_id", "")),
            title=str(get("job_title", "")),
            company=str(get("company", "")),
            location=str(get("city", "")),
            role=str(get("standardized_job_title", get("job_title", ""))),
            experience_category=str(get("experience_category", "")),
            salary_average=float(salary) if salary is not None else None,
            skills=skill_list,
            description=str(get("job_description", ""))[:600],
        )

    @property
    def skills_text(self) -> str:
        return " ".join(self.skills)
