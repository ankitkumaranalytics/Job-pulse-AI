"""User career profile used across matching, recommendations and coaching."""
from __future__ import annotations

from dataclasses import dataclass, field

from dashboard.utils.text_processing import dedupe_keep_order


@dataclass
class UserProfile:
    """The job seeker's profile as used by the AI engines."""

    skills: list[str] = field(default_factory=list)
    target_role: str = ""
    preferred_location: str = ""
    experience_level: str = "Entry Level"  # Fresher/Entry/Mid/Senior
    experience_years: float | None = None
    education_level: str | None = None
    career_goal: str = ""
    resume_text: str = ""

    def to_text(self) -> str:
        """Flatten the profile into a document for TF-IDF similarity."""
        parts = [self.target_role, self.preferred_location, self.career_goal]
        parts.extend(self.skills)
        if self.resume_text:
            parts.append(self.resume_text[:600])
        return " ".join(p for p in parts if p)

    @property
    def completeness(self) -> float:
        """0-100 profile completeness (drives alerts and the estimator)."""
        checks = [
            bool(self.skills),
            bool(self.target_role),
            bool(self.preferred_location),
            bool(self.experience_level),
            self.experience_years is not None,
            self.education_level is not None,
            bool(self.resume_text),
        ]
        return round(100.0 * sum(bool(c) for c in checks) / len(checks), 1)

    def merge_skills(self, extra: list[str]) -> list[str]:
        """Merge resume-extracted skills into the profile skills."""
        self.skills = dedupe_keep_order(list(self.skills) + list(extra))
        return self.skills
