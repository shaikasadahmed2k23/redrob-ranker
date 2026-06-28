"""
Unit tests for the ranking system's core logic.

Run with: python -m pytest tests/ -v
(or: python -m unittest discover tests/  if pytest isn't installed)
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from features import (
    is_honeypot,
    disqualifier_multiplier,
    title_score,
    experience_score,
    skill_match_score,
    behavioral_multiplier,
)
from reference_data import title_tier, skill_weight, company_info


def make_candidate(**overrides):
    """Builds a minimal valid candidate dict, with overrides for specific fields."""
    base = {
        "candidate_id": "CAND_0000000",
        "profile": {
            "anonymized_name": "Test Candidate",
            "headline": "Test Headline",
            "summary": "Test summary.",
            "location": "Pune, Maharashtra",
            "country": "India",
            "years_of_experience": 7.0,
            "current_title": "Senior AI Engineer",
            "current_company": "Krutrim",
            "current_company_size": "201-500",
            "current_industry": "AI/ML",
        },
        "career_history": [
            {
                "company": "Krutrim", "title": "Senior AI Engineer",
                "start_date": "2023-01-01", "end_date": None,
                "duration_months": 42, "is_current": True,
                "industry": "AI/ML", "company_size": "201-500",
                "description": "Built embeddings-based retrieval system using FAISS.",
            },
        ],
        "education": [{"institution": "X", "degree": "B.Tech", "field_of_study": "CS",
                        "start_year": 2014, "end_year": 2018, "tier": "tier_2"}],
        "skills": [
            {"name": "FAISS", "proficiency": "advanced", "endorsements": 20, "duration_months": 30},
        ],
        "redrob_signals": {
            "profile_completeness_score": 90, "signup_date": "2025-01-01",
            "last_active_date": "2026-06-01", "open_to_work_flag": True,
            "profile_views_received_30d": 10, "applications_submitted_30d": 1,
            "recruiter_response_rate": 0.6, "avg_response_time_hours": 24,
            "skill_assessment_scores": {}, "connection_count": 100,
            "endorsements_received": 20, "notice_period_days": 30,
            "expected_salary_range_inr_lpa": {"min": 30, "max": 45},
            "preferred_work_mode": "hybrid", "willing_to_relocate": True,
            "github_activity_score": 50, "search_appearance_30d": 50,
            "saved_by_recruiters_30d": 2, "interview_completion_rate": 0.8,
            "offer_acceptance_rate": 0.6, "verified_email": True,
            "verified_phone": True, "linkedin_connected": True,
        },
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and key in base:
            base[key] = {**base[key], **value}
        else:
            base[key] = value
    return base


class TestHoneypotDetection(unittest.TestCase):
    def test_clean_candidate_not_flagged(self):
        c = make_candidate()
        hp, _ = is_honeypot(c)
        self.assertFalse(hp)

    def test_expert_zero_months_is_honeypot(self):
        c = make_candidate(skills=[
            {"name": "MLflow", "proficiency": "expert", "endorsements": 5, "duration_months": 0}
        ])
        hp, reason = is_honeypot(c)
        self.assertTrue(hp)
        self.assertIn("expert", reason)

    def test_career_overflow_is_honeypot(self):
        c = make_candidate(
            profile={"years_of_experience": 2.0},
            career_history=[
                {"company": "A", "title": "X", "start_date": "2010-01-01", "end_date": "2020-01-01",
                 "duration_months": 120, "is_current": False, "industry": "Software",
                 "company_size": "1-10", "description": "x"},
            ],
        )
        hp, reason = is_honeypot(c)
        self.assertTrue(hp)
        self.assertIn("career history", reason)

    def test_advanced_zero_months_not_flagged(self):
        # only "expert" + 0 months is impossible; "advanced" + 0 is just unusual, not flagged
        c = make_candidate(skills=[
            {"name": "MLflow", "proficiency": "advanced", "endorsements": 5, "duration_months": 0}
        ])
        hp, _ = is_honeypot(c)
        self.assertFalse(hp)


class TestDisqualifiers(unittest.TestCase):
    def test_consulting_only_career_penalized(self):
        c = make_candidate(
            profile={"current_company": "TCS", "current_title": "Software Engineer"},
            career_history=[
                {"company": "TCS", "title": "Software Engineer", "start_date": "2018-01-01",
                 "end_date": None, "duration_months": 60, "is_current": True,
                 "industry": "IT Services", "company_size": "10001+", "description": "x"},
                {"company": "Infosys", "title": "Software Engineer", "start_date": "2014-01-01",
                 "end_date": "2018-01-01", "duration_months": 48, "is_current": False,
                 "industry": "IT Services", "company_size": "10001+", "description": "x"},
            ],
        )
        mult, reasons = disqualifier_multiplier(c)
        self.assertLess(mult, 1.0)
        self.assertTrue(any("consulting" in r for r in reasons))

    def test_mixed_consulting_and_product_not_penalized_for_consulting(self):
        c = make_candidate(
            career_history=[
                {"company": "TCS", "title": "Software Engineer", "start_date": "2014-01-01",
                 "end_date": "2017-01-01", "duration_months": 36, "is_current": False,
                 "industry": "IT Services", "company_size": "10001+", "description": "x"},
                {"company": "Krutrim", "title": "Senior AI Engineer", "start_date": "2017-01-01",
                 "end_date": None, "duration_months": 60, "is_current": True,
                 "industry": "AI/ML", "company_size": "201-500", "description": "x"},
            ],
        )
        mult, reasons = disqualifier_multiplier(c)
        self.assertFalse(any("consulting" in r for r in reasons))

    def test_pure_research_career_penalized(self):
        c = make_candidate(
            profile={"current_title": "AI Research Engineer"},
            career_history=[
                {"company": "X", "title": "AI Research Engineer", "start_date": "2018-01-01",
                 "end_date": None, "duration_months": 60, "is_current": True,
                 "industry": "AI/ML", "company_size": "51-200", "description": "x"},
            ],
        )
        mult, reasons = disqualifier_multiplier(c)
        self.assertLess(mult, 1.0)
        self.assertTrue(any("pure-research" in r for r in reasons))

    def test_framework_only_ai_exposure_penalized(self):
        c = make_candidate(skills=[
            {"name": "LangChain", "proficiency": "advanced", "endorsements": 5, "duration_months": 10},
            {"name": "Prompt Engineering", "proficiency": "advanced", "endorsements": 3, "duration_months": 8},
        ])
        mult, reasons = disqualifier_multiplier(c)
        self.assertLess(mult, 1.0)
        self.assertTrue(any("framework" in r for r in reasons))


class TestScoringComponents(unittest.TestCase):
    def test_title_score_ordering(self):
        self.assertGreater(title_tier("Senior AI Engineer"), title_tier("HR Manager"))
        self.assertGreater(title_tier("ML Engineer"), title_tier("Software Engineer"))

    def test_experience_score_peaks_in_band(self):
        c7 = make_candidate(profile={"years_of_experience": 7.0})
        c1 = make_candidate(profile={"years_of_experience": 1.0})
        c20 = make_candidate(profile={"years_of_experience": 20.0})
        self.assertGreater(experience_score(c7), experience_score(c1))
        self.assertGreater(experience_score(c7), experience_score(c20))

    def test_skill_trust_weighting(self):
        # same skill, same proficiency, but one has real endorsement+duration evidence
        trusted = make_candidate(skills=[
            {"name": "RAG", "proficiency": "expert", "endorsements": 40, "duration_months": 36}
        ])
        unbacked = make_candidate(skills=[
            {"name": "RAG", "proficiency": "expert", "endorsements": 0, "duration_months": 1}
        ])
        self.assertGreater(skill_match_score(trusted), skill_match_score(unbacked))

    def test_company_classification_known_vs_unknown(self):
        self.assertEqual(company_info("Krutrim")["type"], "ai_native")
        self.assertEqual(company_info("TCS")["type"], "consulting")
        # unknown company should not crash, falls back to a sane default
        self.assertIn("type", company_info("Some Company Not In Table"))


class TestBehavioralMultiplier(unittest.TestCase):
    def test_inactive_candidate_penalized(self):
        active = make_candidate(redrob_signals={"last_active_date": "2026-06-20"})
        inactive = make_candidate(redrob_signals={"last_active_date": "2025-01-01"})
        mult_active, _ = behavioral_multiplier(active)
        mult_inactive, _ = behavioral_multiplier(inactive)
        self.assertGreater(mult_active, mult_inactive)

    def test_low_response_rate_penalized(self):
        responsive = make_candidate(redrob_signals={"recruiter_response_rate": 0.7})
        unresponsive = make_candidate(redrob_signals={"recruiter_response_rate": 0.05})
        mult_r, _ = behavioral_multiplier(responsive)
        mult_u, _ = behavioral_multiplier(unresponsive)
        self.assertGreater(mult_r, mult_u)

    def test_multiplier_stays_bounded(self):
        c = make_candidate(redrob_signals={
            "last_active_date": "2020-01-01", "recruiter_response_rate": 0.0,
            "interview_completion_rate": 0.0, "offer_acceptance_rate": 0.0,
            "open_to_work_flag": False, "notice_period_days": 180,
            "verified_email": False, "verified_phone": False,
        })
        mult, _ = behavioral_multiplier(c)
        self.assertGreaterEqual(mult, 0.4)
        self.assertLessEqual(mult, 1.25)


if __name__ == "__main__":
    unittest.main()
