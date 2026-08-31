"""Resume entity produced by resume_service.parse_resume()."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResumeProfile:
    """Everything the platform could reliably extract from a resume."""

    filename: str = ""
    text: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""
    skills: list[str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    education_level: str | None = None
    experience_years: float | None = None
    projects: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    sections_found: list[str] = field(default_factory=list)
    word_count: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def contact_complete(self) -> bool:
        return bool(self.email and self.phone)

    @property
    def is_fresh_profile(self) -> bool:
        """True when the resume shows no professional experience duration."""
        return self.experience_years is None or self.experience_years < 1

    def summary(self) -> dict:
        """Serialisable summary for session state and debugging."""
        return {
            "filename": self.filename,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "skills": self.skills,
            "education": self.education,
            "education_level": self.education_level,
            "experience_years": self.experience_years,
            "projects": self.projects,
            "certifications": self.certifications,
            "sections_found": self.sections_found,
            "word_count": self.word_count,
            "warnings": self.warnings,
        }
