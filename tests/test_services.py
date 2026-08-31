"""
Service-layer tests for the career-intelligence platform.

Covers: skill extraction, resume parsing + fallback, ATS scoring, job
matching, recommendation ranking, semantic search, skill gap analysis,
roadmap building, interview generation/evaluation, tracker persistence,
alerts and invalid-input handling. Every score must satisfy
0 <= score <= 100.
"""
from __future__ import annotations

import pandas as pd
import pytest

from dashboard.models.user_profile import UserProfile
from dashboard.utils.constants import ATS_WEIGHTS, MATCH_WEIGHTS, RECOMMENDATION_WEIGHTS
from dashboard.utils.scoring import clamp100, weighted_score


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def sample_resume_text() -> str:
    return (
        "Ankit Kumar\nankit@example.com | +91 9876543210\n"
        "SUMMARY\nData analyst with 2 years of experience in analytics.\n"
        "SKILLS\nPython, SQL, Power BI, Excel, Pandas\n"
        "EXPERIENCE\nAnalyst at ABC Corp, improved reporting by 40% over 2 years\n"
        "EDUCATION\nB.Tech Computer Science, 2022\n"
        "PROJECTS\n1. Sales Analytics Dashboard built with Power BI and SQL\n"
        "CERTIFICATIONS\nAWS Certified Cloud Practitioner\n"
    )


@pytest.fixture(scope="module")
def sample_profile(sample_resume_text):
    from dashboard.services.resume_service import parse_resume

    return parse_resume(sample_resume_text, "resume.txt")


@pytest.fixture(scope="module")
def jobs_df() -> pd.DataFrame:
    return pd.DataFrame({
        "job_id": ["J1", "J2", "J3"],
        "job_title": ["Data Analyst", "Senior Data Analyst", "Barista"],
        "standardized_job_title": ["Data Analyst", "Data Analyst", "Other"],
        "company": ["InfoEdge", "TCS", "CafeX"],
        "city": ["Chennai", "Bangalore", "Delhi"],
        "salary_average": [600000, 1200000, 30000],
        "posting_date": ["2026-01-05", "2026-01-06", "2026-01-07"],
        "experience_category": ["Entry Level", "Senior Level", "Entry Level"],
        "experience_min": [1, 5, 0],
        "extracted_skills": [
            ["Python", "SQL", "Power BI", "Excel"],
            ["Python", "SQL", "Spark", "AWS"],
            ["Coffee", "POS"],
        ],
        "job_description": [
            "data analyst python sql dashboards",
            "senior analytics spark aws",
            "coffee making",
        ],
    })


def assert_score_bounds(value: float) -> None:
    assert 0 <= value <= 100, f"score out of bounds: {value}"


# ---------------------------------------------------------------- weights
def test_weight_sums_are_one() -> None:
    assert abs(sum(ATS_WEIGHTS.values()) - 1.0) < 1e-6
    assert abs(sum(MATCH_WEIGHTS.values()) - 1.0) < 1e-6
    assert abs(sum(RECOMMENDATION_WEIGHTS.values()) - 1.0) < 1e-6


def test_clamp_never_exceeds_bounds() -> None:
    assert clamp100(150) == 100 and clamp100(-10) == 0 and clamp100(float("nan")) == 0


# ------------------------------------------------------- resume parsing
def test_resume_parse_extracts_contact_skills(sample_profile) -> None:
    assert sample_profile.email == "ankit@example.com"
    assert "Python" in sample_profile.skills
    assert sample_profile.experience_years == 2.0
    assert sample_profile.education_level == "Bachelors"
    assert sample_profile.projects


def test_resume_parse_fallback_plain_text() -> None:
    """A resume without standard headings must still parse core fields."""
    from dashboard.services.resume_service import parse_resume

    text = ("Priya Sharma priya@dev.io +91 90000 11111 "
            "skills: Python and SQL. 3 years experience.")
    profile = parse_resume(text, "plain.txt")
    assert profile.email == "priya@dev.io"
    assert "Python" in profile.skills
    assert profile.experience_years == 3.0


def test_resume_invalid_inputs_raise() -> None:
    from dashboard.services.resume_service import extract_text, parse_resume
    from dashboard.utils.validation import ResumeParseError

    with pytest.raises(ResumeParseError):
        extract_text("virus.exe", b"MZ...")
    with pytest.raises(ResumeParseError):
        extract_text("empty.txt", b"")
    with pytest.raises(ResumeParseError):
        parse_resume("short")

# ------------------------------------------------------------ ATS scoring
def test_ats_scores_have_bounds_and_factors(sample_profile) -> None:
    from dashboard.services.ats_service import score_resume

    report = score_resume(sample_profile)
    assert_score_bounds(report["overall"])
    for comp in report["components"].values():
        assert_score_bounds(comp["score"])
        assert comp["factors"], "each component must explain itself"
    assert report["recommendations"]


def test_ats_role_requirements_drive_missing_keywords(sample_profile, jobs_df) -> None:
    from dashboard.services.ats_service import score_resume
    from models.skill_gap import SkillGapAnalyzer

    requirements = SkillGapAnalyzer(jobs_df).get_required_skills("Data Analyst", top_n=10)
    report = score_resume(sample_profile, requirements)
    assert report["missing_keywords"]
    assert_score_bounds(report["overall"])


# --------------------------------------------------------- match engine
def test_match_components_and_bounds(sample_profile, sample_resume_text) -> None:
    from dashboard.services.match_service import compute_match

    jd = ("We need a Data Analyst skilled in Python, SQL, Tableau and Statistics. "
          "2+ years experience. Bachelors degree required.")
    match = compute_match(
        sample_resume_text, sample_profile.skills, jd,
        experience_years=2.0, education_level="Bachelors",
        projects_text="Sales dashboard built with Power BI",
    )
    assert_score_bounds(match["overall"])
    for score in match["components"].values():
        assert_score_bounds(score)
    assert "Tableau" in match["missing_skills"]
    assert "SQL" in match["matched_skills"]


def test_match_semantic_identical_beats_disjoint() -> None:
    from dashboard.services.match_service import compute_match

    text = "python sql power bi dashboards data cleaning"
    aligned = compute_match(text, ["Python"], text)
    disjoint = compute_match(text, ["Python"], "bakery pastry croissant espresso menu")
    assert aligned["components"]["semantic_match"] > disjoint["components"]["semantic_match"]


def test_match_empty_jd_raises() -> None:
    from dashboard.services.match_service import compute_match
    from dashboard.utils.validation import ServiceError

    with pytest.raises(ServiceError):
        compute_match("resume text", ["Python"], "   ")


# ------------------------------------------------- estimator (FEATURE 10)
def test_application_strength_bounds_and_wording(sample_profile, sample_resume_text) -> None:
    from dashboard.services.match_service import (
        compute_match,
        estimate_application_strength,
    )

    match = compute_match(sample_resume_text, sample_profile.skills,
                          "Data Analyst with Python and SQL")
    strength = estimate_application_strength(match, profile_completeness=85, ats_overall=70)
    assert_score_bounds(strength["strength"])
    assert "NOT a prediction" in strength["disclaimer"]

# -------------------------------------------------- recommendations (F3)
def test_hybrid_recommender_ranks_and_explains(jobs_df) -> None:
    from dashboard.services.recommendation_service import HybridRecommender

    profile = UserProfile(
        skills=["Python", "SQL"], target_role="Data Analyst",
        preferred_location="Chennai", experience_level="Entry Level",
    )
    results = HybridRecommender(jobs_df).recommend(profile, top_n=3)
    assert len(results) >= 1
    assert results.iloc[0]["job_title"] == "Data Analyst"  # best fit first
    for score in results["match_score"]:
        assert 0 <= score <= 1
    assert results.iloc[0]["why_recommended"].startswith("Recommended because")


def test_hybrid_recommender_empty_frame(jobs_df) -> None:
    from dashboard.services.recommendation_service import HybridRecommender

    out = HybridRecommender(jobs_df.head(0)).recommend(UserProfile(skills=["Python"]))
    assert isinstance(out, pd.DataFrame) and len(out) == 0


# ---------------------------------------------------- search (FEATURE 4)
def test_query_parsing_extracts_intent(jobs_df) -> None:
    from dashboard.services.search_service import parse_query

    intent = parse_query(
        "fresher Data Analyst internship in Chennai with Python and SQL", jobs_df
    )
    assert intent["role"] == "Data Analyst"
    assert intent["location"] == "Chennai"
    assert intent["experience_level"] == "Fresher"
    assert intent["job_type"] == "Internship"
    assert {"Python", "SQL"} <= set(intent["skills"])


def test_rank_jobs_returns_scored_results(jobs_df) -> None:
    from dashboard.services.search_service import rank_jobs

    results = rank_jobs(jobs_df, "data analyst in chennai with python")
    assert len(results) >= 1
    assert results.iloc[0]["job_title"] == "Data Analyst"
    assert_score_bounds(float(results.iloc[0]["_search_score"]))


def test_rank_jobs_empty_query_raises(jobs_df) -> None:
    from dashboard.services.search_service import rank_jobs
    from dashboard.utils.validation import ServiceError

    with pytest.raises(ServiceError):
        rank_jobs(jobs_df, "x")


# ---------------------------------------------- skill gap (FEATURE 5)
def test_skill_gap_priorities_and_bounds(jobs_df) -> None:
    from dashboard.services.skill_gap_service import analyze_skill_gap

    gaps = analyze_skill_gap(jobs_df, ["Python"], "Data Analyst")
    assert_score_bounds(gaps["gap_score"])
    assert gaps["gap_score"] > 0  # SQL/Power BI/Excel missing
    priorities = gaps["priorities"]
    assert priorities and priorities == sorted(priorities, key=lambda p: -p["priority"])
    assert all(p["bucket"] in {"High", "Medium", "Low"} for p in priorities)


def test_skill_gap_zero_when_all_skills_present(jobs_df) -> None:
    from dashboard.services.skill_gap_service import analyze_skill_gap
    from models.skill_gap import SkillGapAnalyzer

    requirements = SkillGapAnalyzer(jobs_df).get_required_skills("Data Analyst", top_n=10)
    gaps = analyze_skill_gap(
        jobs_df, [s for s, _, _ in requirements], "Data Analyst", top_n=10
    )
    assert gaps["gap_score"] == 0
    assert gaps["missing_count"] == 0


def test_skill_gap_invalid_role_raises(jobs_df) -> None:
    from dashboard.services.skill_gap_service import analyze_skill_gap
    from dashboard.utils.validation import ServiceError

    with pytest.raises(ServiceError):
        analyze_skill_gap(jobs_df, ["Python"], "Astronaut")

# ------------------------------------------------- roadmap (FEATURE 6)
def test_roadmap_builds_ordered_phases_with_progress(jobs_df) -> None:
    from dashboard.services.roadmap_service import build_roadmap
    from dashboard.services.skill_gap_service import analyze_skill_gap

    gaps = analyze_skill_gap(jobs_df, ["Python"], "Data Analyst")
    roadmap = build_roadmap(
        [p["skill"] for p in gaps["priorities"]],
        target_role="Data Analyst",
        completed_skills={"SQL"},
    )
    assert roadmap["phases"], "roadmap must contain at least one phase"
    # 1 of the 5 missing skills (SQL) already learned -> 20% progress
    assert roadmap["completed_skills"] == 1
    assert 0 < roadmap["completion_pct"] < 100
    for phase in roadmap["phases"]:
        assert phase["duration_weeks"] >= 2
        assert phase["skills"]


# ----------------------------------------------- interview (FEATURE 9)
def test_interview_generation_is_deterministic(jobs_df) -> None:
    from dashboard.services.interview_service import generate_interview

    skills = [("SQL", 10, "Critical"), ("Python", 8, "Important"), ("Power BI", 5, "Optional")]
    first = generate_interview(skills, "Technical", "Entry Level", n_questions=4, seed=7)
    second = generate_interview(skills, "Technical", "Entry Level", n_questions=4, seed=7)
    assert first == second
    assert len(first) == 4
    assert all(q["question"] and q["expected_keywords"] for q in first)


def test_interview_evaluation_bounds_and_star_bonus(jobs_df) -> None:
    from dashboard.services.interview_service import evaluate_answer, generate_interview

    question = generate_interview([("SQL", 5, "Critical")], "Technical",
                                  n_questions=1, seed=3)[0]
    strong = evaluate_answer(question, (
        "Situation: our monthly report was slow. Task: cut processing time. "
        "Action: I rewrote the SQL using window functions and rank over partition, "
        "added an index, and validated results. Result: 40% faster reports, "
        "adopted by 3 teams."
    ))
    weak = evaluate_answer(question, "i guess maybe i would use sql i think")
    assert_score_bounds(strong["overall"])
    assert strong["overall"] > weak["overall"]
    assert strong["components"]["answer_structure"] > weak["components"]["answer_structure"]


# ------------------------------------------------- tracker (FEATURE 8)
def test_tracker_crud_and_analytics(tmp_path) -> None:
    from dashboard.services import tracker_service

    db = tmp_path / "tracker.db"
    app_id = tracker_service.add_application(
        "Acme", "Data Analyst", "Chennai", "Applied",
        match_score=82.0, db_path=db,
    )
    tracker_service.update_status(app_id, "Interview", db_path=db)
    tracker_service.update_notes(app_id, "Recruiter call Tuesday", db_path=db)
    apps = tracker_service.list_applications(db)
    assert len(apps) == 1
    assert apps[0]["status"] == "Interview"
    assert apps[0]["notes"] == "Recruiter call Tuesday"

    analytics = tracker_service.tracker_analytics(apps)
    assert analytics["total"] == 1
    assert analytics["by_status"]["Interview"] == 1
    assert analytics["interview_rate"] == 100.0

    tracker_service.delete_application(app_id, db_path=db)
    assert tracker_service.list_applications(db) == []


def test_tracker_invalid_status_raises(tmp_path) -> None:
    from dashboard.services import tracker_service
    from dashboard.utils.validation import ServiceError

    db = tmp_path / "t2.db"
    app_id = tracker_service.add_application("Globex", "Analyst", db_path=db)
    with pytest.raises(ServiceError):
        tracker_service.update_status(app_id, "Hired?", db_path=db)
    with pytest.raises(ServiceError):
        tracker_service.add_application("   ", "Analyst", db_path=db)


# --------------------------------------------------- alerts (FEATURE 11)
def test_alerts_generation(jobs_df, tmp_path) -> None:
    from dashboard.services import tracker_service
    from dashboard.services.alerts_service import generate_alerts

    profile = UserProfile(skills=["Python"], target_role="Data Analyst")
    alerts = generate_alerts(jobs_df, profile, applications=[])
    assert all({"icon", "title", "detail", "cta_page"} <= set(a) for a in alerts)
    assert all(a["cta_page"] in {
        "Job Search", "⭐ AI Career Advisor", "Application Tracker",
        "Resume Intelligence",
    } for a in alerts)


# ------------------------------------------- navigation consistency
def test_navigation_registry_is_consistent() -> None:
    from dashboard.components.premium import NAV_LABELS, PAGE_KEYS

    assert set(NAV_LABELS) == set(PAGE_KEYS.keys()), "every label needs a page key"
    assert len(NAV_LABELS) == len(set(NAV_LABELS)), "labels must be unique"
    assert "requested_navigation" not in PAGE_KEYS  # reserved key stays internal


