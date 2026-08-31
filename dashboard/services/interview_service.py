"""AI Mock Interview Coach service (FEATURE 9).

Generates role/type/level-relevant interview questions from a curated
template bank (seeded for reproducibility) and evaluates answers with
deterministic heuristics: technical-term coverage, communication
signals, STAR structure and completeness.

IMPORTANT: feedback is AI-generated *guidance* for practice purposes —
explicitly not a professional assessment. The UI must keep that label.
"""
from __future__ import annotations

import random
import re

from dashboard.utils.scoring import clamp100, weighted_score

# Per-skill technical question banks: skill -> [(question, expected keywords)]
_TECHNICAL_BANK: dict[str, list[tuple[str, list[str]]]] = {
    "SQL": [
        ("Explain the difference between INNER JOIN, LEFT JOIN and FULL JOIN. When would you use each?", ["join", "left", "inner", "match", "null"]),
        ("Write a query to find the second-highest salary per department. Which window function would you use?", ["window", "rank", "dense_rank", "partition", "order"]),
        ("What is the difference between WHERE and HAVING? Give a real example.", ["filter", "group by", "aggregate", "having", "where"]),
        ("How would you optimise a slow query running on a 10M-row table?", ["index", "explain", "partition", "scan", "optimis", "optimiz"]),
    ],
    "Python": [
        ("How do you handle missing values in a pandas DataFrame? Describe two strategies.", ["pandas", "dataframe", "fillna", "dropna", "missing", "impute"]),
        ("Explain list comprehensions vs loops for data transformation. When is each better?", ["comprehension", "loop", "vectoris", "vectoriz", "performance"]),
        ("Describe how you would profile and fix memory issues in a large DataFrame.", ["dtype", "category", "chunk", "memory", "copy"]),
    ],
    "Power BI": [
        ("Walk me through how you would design a sales dashboard from raw CSV data.", ["model", "relationship", "measure", "dax", "dashboard"]),
        ("Explain the difference between calculated columns and measures in DAX.", ["dax", "measure", "column", "context", "row"]),
    ],
    "Tableau": [
        ("How do LOD expressions differ from table calculations? Give a use case.", ["lod", "level of detail", "include", "exclude", "fixed", "table calc"]),
    ],
    "Statistics": [
        ("Explain p-value and confidence interval to a non-technical stakeholder.", ["p-value", "significan", "confidence", "interval", "hypothesis"]),
        ("How would you detect whether two groups differ meaningfully in an A/B test?", ["a/b", "test", "t-test", "sample", "significan"]),
    ],
    "Excel": [
        ("Which Excel features do you use for a 100k-row monthly reconciliation?", ["vlookup", "xlookup", "pivot", "index", "match", "power query"]),
    ],
    "Machine Learning": [
        ("How do you choose between classification and regression metrics for a project?", ["accuracy", "precision", "recall", "rmse", "metric", "f1"]),
        ("Explain overfitting and three concrete ways to prevent it.", ["overfit", "regulari", "cross-validation", "pruning", "dropout"]),
    ],
}
_GENERIC_TECHNICAL = [
    ("Describe an end-to-end data project you built: data source, pipeline, and outcome.", ["data", "pipeline", "clean", "dashboard", "model", "outcome"]),
    ("How do you validate that your analysis is correct before sharing it?", ["validat", "verify", "test", "reconcil", "sanity"]),
]
_HR_BANK = [
    ("Tell me about yourself and what draws you to this role.", ["experience", "skill", "role", "excited", "background"]),
    ("What are your greatest strengths relevant to this position?", ["strength", "skill", "deliver", "result"]),
    ("Where do you see yourself in three years?", ["grow", "learn", "goal", "career"]),
    ("Why should we hire you over other candidates?", ["value", "skill", "fit", "contribute"]),
]
_BEHAVIORAL_BANK = [
    ("Describe a time you missed a deadline. What happened and what did you change?", ["situation", "task", "action", "result", "deadline", "learn"]),
    ("Tell me about a conflict with a teammate and how you resolved it.", ["situation", "listen", "communicat", "resolved", "outcome"]),
    ("Describe a project where you had to learn a new tool quickly.", ["learn", "situation", "action", "delivered", "result"]),
    ("Give an example of feedback you received that was hard to hear.", ["feedback", "improved", "action", "result"]),
]
_STAR_WORDS = ["situation", "task", "action", "result", "project", "team", "outcome",
               "challenge", "goal", "impact", "learned", "delivered"]
_FILLERS = ["i guess", "maybe", "i think probably", "sort of", "kind of", "um", "like yeah"]

_EVAL_WEIGHTS = {
    "technical_accuracy": 0.35,
    "communication": 0.25,
    "answer_structure": 0.20,
    "completeness": 0.20,
}


def generate_interview(
    role_skills: list | list[tuple[str, int, str]],
    interview_type: str = "Technical",
    experience_level: str = "Entry Level",
    n_questions: int = 5,
    seed: int = 42,
) -> list[dict]:
    """
    Build a reproducible mock interview (same seed -> same questions).

    ``role_skills``: (skill, count, importance) tuples from SkillGapAnalyzer
    or a plain skill list — top skills drive Technical question selection.
    """
    rng = random.Random(seed)
    questions: list[dict] = []

    if interview_type == "Technical":
        skills: list[str] = []
        for item in role_skills or []:
            name = item[0] if isinstance(item, (tuple, list)) else str(item)
            if name not in skills:
                skills.append(str(name))
        bank: list[tuple[str, list[str]]] = []
        for skill in skills:
            bank.extend(_TECHNICAL_BANK.get(skill, []))
        bank.extend(_GENERIC_TECHNICAL)
        rng.shuffle(bank)
        for question, expected in bank[:n_questions]:
            questions.append({"type": "Technical", "question": question,
                              "expected_keywords": expected})
    elif interview_type == "Behavioral":
        pool = _BEHAVIORAL_BANK[:]
        rng.shuffle(pool)
        for question, expected in pool[:n_questions]:
            questions.append({"type": "Behavioral", "question": question,
                              "expected_keywords": expected})
    else:  # HR
        pool = _HR_BANK[:]
        rng.shuffle(pool)
        for question, expected in pool[:n_questions]:
            questions.append({"type": "HR", "question": question,
                              "expected_keywords": expected})

    for i, q in enumerate(questions, start=1):
        q["id"] = f"q{i}"
        q["experience_level"] = experience_level
    return questions

def evaluate_answer(question: dict, answer: str) -> dict:
    """Score one answer across four explainable components (0-100 each)."""
    text = (answer or "").strip()
    lowered = text.lower()
    words = re.findall(r"[A-Za-z']+", lowered)

    expected = [k.lower() for k in question.get("expected_keywords", [])]
    keyword_hits = sum(1 for k in expected if k in lowered)
    coverage = keyword_hits / len(expected) if expected else 0.5

    # --- Technical accuracy: expected-concept coverage + quantification ---
    quantified = bool(re.search(r"\d+\s*%|\b\d{2,}\+?\b", lowered))
    technical = clamp100(100.0 * (0.75 * coverage + 0.25 * (1.0 if quantified else 0.0)))

    # --- Communication: answer-length bands + filler/hedging penalty ---
    length = len(words)
    if length == 0:
        communication = 0.0
    elif length < 20:
        communication = 35.0
    elif length <= 220:
        communication = 90.0
    elif length <= 350:
        communication = 75.0
    else:
        communication = 55.0  # rambling
    fillers = sum(lowered.count(f) for f in _FILLERS)
    communication = clamp100(communication - 6.0 * fillers)

    # --- Structure: STAR signals / paragraph or bullet organisation ---
    star_hits = sum(1 for w in _STAR_WORDS if w in lowered)
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    structure = clamp100(
        min(100.0, 14.0 * star_hits
            + 15.0 * (1 if len(paragraphs) >= 2 else 0)
            + 15.0 * (1 if ("\n-" in text or "\n•" in text or "\n1" in text) else 0))
    )

    # --- Completeness: minimum depth + concept coverage ---
    depth_ok = length >= 45
    completeness = clamp100(100.0 * (0.6 * coverage + 0.4 * (1.0 if depth_ok else 0.0)))

    overall = weighted_score(
        {"technical_accuracy": technical, "communication": communication,
         "answer_structure": structure, "completeness": completeness},
        _EVAL_WEIGHTS,
    )

    strengths: list[str] = []
    if technical >= 70:
        strengths.append("Covers the key technical concepts")
    if structure >= 60:
        strengths.append("Structured, easy-to-follow answer (STAR-style signals)")
    if quantified:
        strengths.append("Uses concrete numbers/impact")
    if communication >= 75 and length >= 20:
        strengths.append("Appropriate answer length and delivery")

    weak: list[str] = []
    missing_concepts = [k for k in expected if k not in lowered]
    if technical < 60:
        weak.append("Key concepts not addressed: "
                    + (", ".join(missing_concepts[:3]) or "core ideas"))
    if structure < 50:
        weak.append("Unstructured — use STAR (Situation, Task, Action, Result)")
    if length < 25:
        weak.append("Answer is too short — expand with a concrete example")
    if length > 350:
        weak.append("Answer is very long — tighten to the strongest 2-3 points")
    if not quantified:
        weak.append("Add measurable outcomes (%, volume, time saved)")
    if fillers:
        weak.append("Reduce hedging/filler language to sound more confident")

    practice = []
    if question["type"] == "Technical":
        practice.append("Practice one JOIN + window-function scenario out loud")
    if structure < 50:
        practice.append("Prepare two project stories using STAR")
    if not quantified:
        practice.append("Rewrite one achievement with a measurable result")
    if not practice:
        practice.append("Keep practising under a 2-minute timer per answer")

    return {
        "overall": overall,
        "components": {"technical_accuracy": technical, "communication": communication,
                       "answer_structure": structure, "completeness": completeness},
        "strengths": strengths,
        "weak_areas": weak,
        "recommended_practice": practice[:3],
        "missing_concepts": missing_concepts[:5],
        "scoring_basis": (
            "Deterministic heuristics: expected-concept coverage, answer-length "
            "bands, filler detection and STAR structure signals. AI-generated "
            "guidance for practice — NOT a professional or objective assessment."
        ),
    }


def session_summary(evaluations: list[dict]) -> dict:
    """Aggregate per-question evaluations into a session scorecard."""
    if not evaluations:
        return {"overall": 0.0, "components": {}, "weak_areas": [], "practice": []}
    keys = ["technical_accuracy", "communication", "answer_structure", "completeness"]
    components = {
        k: clamp100(sum(e["components"].get(k, 0.0) for e in evaluations) / len(evaluations))
        for k in keys
    }
    return {
        "overall": clamp100(sum(e["overall"] for e in evaluations) / len(evaluations)),
        "components": components,
        "weak_areas": [w for e in evaluations for w in e.get("weak_areas", [])][:6],
        "practice": [p for e in evaluations for p in e.get("recommended_practice", [])][:5],
    }
