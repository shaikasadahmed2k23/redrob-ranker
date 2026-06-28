"""
Feature extraction for a single candidate record.

Every function here takes a parsed candidate dict (as loaded from
candidates.jsonl) and returns plain Python scalars. No I/O, no model
loading -- this module is pure and easy to unit test.
"""

from datetime import date, datetime

from reference_data import (
    company_info,
    CONSULTING_COMPANIES,
    title_tier,
    PURE_RESEARCH_TITLES,
    skill_weight,
    FRAMEWORK_SURFACE_SKILLS,
    location_score,
)

TODAY = date(2026, 6, 27)  # dataset "as of" date; kept as a constant for reproducibility


def _parse_date(s):
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


# ---------------------------------------------------------------------------
# Honeypot / impossible-profile detection
# ---------------------------------------------------------------------------

def is_honeypot(candidate: dict) -> tuple[bool, str]:
    """
    Detects subtly-impossible profiles per the two clean, low-false-positive
    signals found during data exploration:
      1. "Expert" proficiency in a skill with 0 months of use (impossible).
      2. Sum of career_history durations substantially exceeds stated
         years_of_experience (impossible without overlapping full-time jobs,
         which the schema doesn't otherwise support).

    Returns (is_honeypot, reason).
    """
    for s in candidate.get("skills", []):
        if s.get("proficiency") == "expert" and s.get("duration_months", -1) == 0:
            return True, f"expert proficiency in '{s['name']}' with 0 months of use"

    yoe = candidate["profile"]["years_of_experience"]
    total_months = sum(ch.get("duration_months", 0) for ch in candidate.get("career_history", []))
    # generous buffer (18 months) to avoid penalizing legitimate overlap/rounding
    if total_months > (yoe * 12 + 18):
        return True, f"career history totals {total_months} months but stated experience is only {yoe} years"

    return False, ""


# ---------------------------------------------------------------------------
# Hard disqualifier checks (soft-penalty multipliers, not necessarily zero)
# ---------------------------------------------------------------------------

def disqualifier_multiplier(candidate: dict) -> tuple[float, list[str]]:
    """
    Returns a multiplier in [0, 1] reflecting the JD's explicit disqualifiers,
    plus a list of human-readable reasons for any penalty applied. We use soft
    multipliers rather than hard zeros (except for honeypots, handled
    separately) because the JD itself says these are heuristics ("we will
    probably not move forward") with explicit exceptions, not absolute rules.
    """
    reasons = []
    multiplier = 1.0

    titles_held = [ch["title"] for ch in candidate.get("career_history", [])]
    titles_held.append(candidate["profile"]["current_title"])
    companies_held = [ch["company"] for ch in candidate.get("career_history", [])]
    companies_held.append(candidate["profile"]["current_company"])

    # Disqualifier: pure research-only career, no production deployment signal.
    if titles_held and all(t in PURE_RESEARCH_TITLES for t in titles_held):
        multiplier *= 0.25
        reasons.append("entire career in pure-research titles with no production-deployment role")

    # Disqualifier: 100% consulting-only career (TCS/Infosys/Wipro/etc.)
    if companies_held and all(c in CONSULTING_COMPANIES for c in companies_held):
        multiplier *= 0.35
        reasons.append("entire career at IT-services/consulting firms with no product company exposure")

    # Disqualifier: senior person who hasn't written production code in 18+ months
    # (proxied by: current title is non-technical leadership-sounding AND
    # years_of_experience is high). We don't have a literal "last wrote code"
    # field, so we proxy conservatively using title only, and only for the
    # clearest cases (Project Manager / Operations Manager with high seniority).
    current_title = candidate["profile"]["current_title"]
    yoe = candidate["profile"]["years_of_experience"]
    if current_title in {"Project Manager", "Operations Manager"} and yoe >= 8:
        multiplier *= 0.6
        reasons.append("senior profile in a non-coding management title")

    # Disqualifier: CV/speech/robotics-only specialist without NLP/IR exposure.
    skill_names = {s["name"] for s in candidate.get("skills", [])}
    cv_speech_skills = {"Computer Vision", "Image Classification", "Object Detection",
                         "YOLO", "Speech Recognition", "ASR", "TTS", "GANs", "CNN"}
    nlp_ir_skills = {"NLP", "Natural Language Processing", "Information Retrieval",
                      "Information Retrieval Systems", "Embeddings", "Vector Search",
                      "Semantic Search", "Search Infrastructure", "Ranking Systems",
                      "Learning to Rank", "LLMs", "RAG"}
    has_cv_speech = bool(skill_names & cv_speech_skills)
    has_nlp_ir = bool(skill_names & nlp_ir_skills)
    if has_cv_speech and not has_nlp_ir and len(skill_names & cv_speech_skills) >= 2:
        multiplier *= 0.5
        reasons.append("CV/speech-focused skill set without NLP/IR exposure")

    # Disqualifier: title-chaser pattern. The JD's actual concern is jumping
    # companies every ~1.5 years purely to inflate a title, NOT moving fast
    # early in a fast-moving field. We only flag this when *every* stint is
    # short (<=18mo, so there's no anchor of depth anywhere in the history)
    # AND there are at least 4 such jobs (a sustained pattern, not 2-3 normal
    # early-career moves).
    history = candidate.get("career_history", [])
    short_stints = [ch for ch in history if ch.get("duration_months", 999) <= 18]
    if len(history) >= 4 and len(short_stints) == len(history):
        multiplier *= 0.7
        reasons.append("every role lasted <=18 months with no anchor of depth -- possible title-hopping")

    # Disqualifier: recent (<12mo) LangChain/RAG-only AI exposure with no
    # deeper pre-LLM-era IR/ranking signal and no senior production history.
    ai_relevant_skills = {n for n in skill_names if n in {
        "NLP", "Natural Language Processing", "Embeddings", "Vector Search",
        "Semantic Search", "Information Retrieval", "Information Retrieval Systems",
        "Ranking Systems", "Learning to Rank", "Recommendation Systems",
        "Search Infrastructure", "FAISS", "Pinecone", "Weaviate", "Qdrant", "Milvus",
        "Elasticsearch", "OpenSearch", "BM25",
    }}
    framework_only = bool(skill_names & FRAMEWORK_SURFACE_SKILLS) and not ai_relevant_skills
    if framework_only:
        multiplier *= 0.55
        reasons.append("AI exposure limited to framework/prompting skills (LangChain/RAG/Prompt Engineering) without retrieval or ranking depth")

    return multiplier, reasons


# ---------------------------------------------------------------------------
# Core fit components (each returns a 0-1 score)
# ---------------------------------------------------------------------------

def title_score(candidate: dict) -> float:
    return title_tier(candidate["profile"]["current_title"]) / 5.0


def experience_score(candidate: dict) -> float:
    """Soft band around 5-9 years, per the JD ('a range, not a requirement')."""
    yoe = candidate["profile"]["years_of_experience"]
    if 5 <= yoe <= 9:
        return 1.0
    if yoe < 5:
        # linear falloff below 5, floor at 0 by ~1.5 years
        return max(0.0, (yoe - 1.5) / 3.5)
    # above 9: gentle falloff, JD says "seriously consider candidates outside the band"
    return max(0.3, 1.0 - (yoe - 9) * 0.07)


def company_quality_score(candidate: dict) -> float:
    """Weighted blend of current company quality and career-history company quality."""
    from reference_data import COMPANY_TYPE_SCORE

    current = company_info(candidate["profile"]["current_company"])
    current_score = COMPANY_TYPE_SCORE[current["type"]]
    if current["ai_relevant"]:
        current_score = min(1.0, current_score + 0.1)

    history = candidate.get("career_history", [])
    if not history:
        return current_score

    hist_scores = []
    for ch in history:
        info = company_info(ch["company"])
        s = COMPANY_TYPE_SCORE[info["type"]]
        if info["ai_relevant"]:
            s = min(1.0, s + 0.1)
        hist_scores.append(s)

    avg_hist = sum(hist_scores) / len(hist_scores)
    # current role weighted more heavily than history average
    return 0.6 * current_score + 0.4 * avg_hist


def skill_match_score(candidate: dict) -> float:
    """
    Trust-weighted skill score: weight each skill's JD-relevance by both
    proficiency and a trust factor derived from endorsements + duration_months.
    This is the direct counter to keyword-stuffing -- a skill claimed with
    zero endorsements and minimal duration counts far less than the same
    skill backed by real endorsements and tenure.
    """
    skills = candidate.get("skills", [])
    if not skills:
        return 0.0

    proficiency_mult = {"beginner": 0.4, "intermediate": 0.65, "advanced": 0.85, "expert": 1.0}

    weighted_scores = []
    for s in skills:
        base_weight = skill_weight(s["name"])
        if base_weight < 0.1:
            continue  # irrelevant skill, don't let it dilute the average
        prof_mult = proficiency_mult.get(s.get("proficiency"), 0.5)
        # trust factor: endorsements and duration both matter, each capped
        endorsement_trust = min(1.0, s.get("endorsements", 0) / 20.0)
        duration_trust = min(1.0, s.get("duration_months", 0) / 24.0)
        trust = 0.3 + 0.35 * endorsement_trust + 0.35 * duration_trust  # floor 0.3, max 1.0
        weighted_scores.append(base_weight * prof_mult * trust)

    if not weighted_scores:
        return 0.0

    # Take a blend of the top-5 relevant skills (depth) and overall average
    # (breadth) so a candidate needs more than one or two strong skills.
    weighted_scores.sort(reverse=True)
    top5 = weighted_scores[:5]
    top5_avg = sum(top5) / len(top5)
    overall_avg = sum(weighted_scores) / len(weighted_scores)
    return 0.7 * top5_avg + 0.3 * overall_avg


def career_history_relevance_text(candidate: dict) -> str:
    """Concatenated free text used for the TF-IDF semantic similarity component."""
    parts = [candidate["profile"].get("headline", ""), candidate["profile"].get("summary", "")]
    for ch in candidate.get("career_history", []):
        parts.append(ch.get("title", ""))
        parts.append(ch.get("description", ""))
    return " ".join(parts)


def education_score(candidate: dict) -> float:
    """Light-weight signal; JD doesn't emphasize pedigree."""
    edu = candidate.get("education", [])
    if not edu:
        return 0.4  # neutral-low, not punitive -- JD doesn't require a degree explicitly
    tier_score = {"tier_1": 1.0, "tier_2": 0.8, "tier_3": 0.6, "tier_4": 0.4, "unknown": 0.5}
    scores = [tier_score.get(e.get("tier", "unknown"), 0.5) for e in edu]
    return max(scores)


def location_fit_score(candidate: dict) -> float:
    return location_score(candidate["profile"]["location"], candidate["profile"]["country"])


# ---------------------------------------------------------------------------
# Behavioral signal multiplier
# ---------------------------------------------------------------------------

def behavioral_multiplier(candidate: dict) -> tuple[float, list[str]]:
    """
    Returns a multiplier roughly in [0.5, 1.18] reflecting platform activity
    and engagement signals, plus human-readable notes for the reasoning column.
    Applied multiplicatively on top of the core fit score, per the JD's
    explicit instruction to down-weight on-paper-good-but-unavailable candidates.

    Thresholds below are calibrated against the *actual* distribution of each
    signal across the full 100K-candidate pool (see notebooks/01_explore_data.py),
    not against guessed absolute values. For example, last_active_date in this
    dataset never falls within the last 30 days for anyone (the most recent
    candidate is ~32 days inactive), so a naive "<=14 days = recent" rule would
    be dead code; instead we use the pool's own percentiles (p10/p50/p90) so the
    multiplier actually discriminates between candidates.
    """
    sig = candidate["redrob_signals"]
    notes = []
    mult = 1.0

    # Recency of activity. Pool percentiles (days inactive): p5=41, p10=51,
    # p25=83, p50=136, p75=193, p90=237, p95=254.
    last_active = _parse_date(sig["last_active_date"])
    days_inactive = (TODAY - last_active).days if last_active else 9999
    if days_inactive <= 51:        # top decile of recency
        mult *= 1.10
    elif days_inactive <= 83:       # top quartile
        mult *= 1.03
    elif days_inactive <= 193:      # middle half -- neutral
        mult *= 1.0
    elif days_inactive <= 254:      # bottom quartile
        mult *= 0.85
        notes.append(f"inactive for {days_inactive} days")
    else:                            # bottom 5%
        mult *= 0.65
        notes.append(f"inactive for {days_inactive} days -- likely not actually reachable")

    # Open to work
    if not sig.get("open_to_work_flag", False):
        mult *= 0.85
        notes.append("not flagged open to work")

    # Recruiter response rate. Pool percentiles: p10=0.14, p25=0.25, p50=0.44,
    # p75=0.62, p90=0.73.
    rr = sig.get("recruiter_response_rate", 0)
    if rr >= 0.62:
        mult *= 1.06
    elif rr < 0.14:
        mult *= 0.75
        notes.append(f"low recruiter response rate ({rr:.0%})")
    elif rr < 0.25:
        mult *= 0.9
        notes.append(f"below-average recruiter response rate ({rr:.0%})")

    # Interview completion rate. Pool percentiles: p10=0.38, p25=0.48, p50=0.62, p75=0.76.
    icr = sig.get("interview_completion_rate", 1.0)
    if icr < 0.38:
        mult *= 0.8
        notes.append(f"low interview completion rate ({icr:.0%})")
    elif icr >= 0.76:
        mult *= 1.03

    # Offer acceptance rate (-1 = no history, treat as neutral, ~60% of pool).
    # Among those WITH history, pool percentiles run roughly 0.4 (p75) to 0.7 (p95),
    # since p50 and below is -1 (no history).
    oar = sig.get("offer_acceptance_rate", -1)
    if oar != -1:
        if oar < 0.3:
            mult *= 0.85
            notes.append(f"history of declining offers ({oar:.0%} acceptance)")
        elif oar >= 0.6:
            mult *= 1.04

    # Notice period. Pool median is ~90 days, NOT 30 -- the JD's "sub-30-day
    # ideal" is relative to a pool that mostly reports 60-150 day notice
    # periods, so we score relative to the pool's own distribution
    # (p25=60, p50=90, p75=120, p90=150) rather than penalizing everyone above
    # a flat 30-day cutoff.
    notice = sig.get("notice_period_days", 90)
    if notice <= 30:
        mult *= 1.08
    elif notice <= 60:
        mult *= 1.02
    elif notice <= 120:
        mult *= 1.0
    else:
        mult *= 0.92
        notes.append(f"long notice period ({notice} days)")

    # Verification / trust signals
    if not sig.get("verified_email", True):
        mult *= 0.97
    if not sig.get("verified_phone", True):
        mult *= 0.97

    # Clamp to a sane range so this never dominates the core fit score
    mult = max(0.45, min(1.2, mult))
    return mult, notes
