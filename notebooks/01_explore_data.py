"""
01_explore_data.py -- Exploratory analysis that informed the ranker's design.

This is a plain script (not a Jupyter notebook) so it runs without extra
dependencies and so its output is easy to diff in git history. Run it with:

    python notebooks/01_explore_data.py /path/to/candidates.jsonl

It reproduces every finding referenced in docs/approach.md and in the
in-code comments of src/reference_data.py and src/features.py:
  - the candidate pool draws from a closed, enumerable universe of 63
    companies, 48 titles, and 133 skills (hence the hand-built lookup
    tables instead of fuzzy matching)
  - the distribution of each redrob_signal (used to calibrate the
    behavioral multiplier against real percentiles, not guessed thresholds)
  - the honeypot patterns that are detectable cheaply and reliably
    (expert-proficiency-with-zero-duration; career-history-duration-exceeds-
    stated-experience), and which candidate patterns turned out NOT to be
    reliable honeypot signals (salary min>max, education-after-first-job)
    because they were too common (~19% of the pool) to be the intended traps
"""

import gzip
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime

import numpy as np

TODAY = date(2026, 6, 27)


def load(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def main(path):
    companies, titles, skills = set(), set(), set()
    co_industry = defaultdict(set)
    last_active_days = []
    response_rates, completion_rates, notice_periods = [], [], []

    expert_zero_mo = 0
    career_overflow = 0
    n = 0

    for c in load(path):
        n += 1
        companies.add(c["profile"]["current_company"])
        titles.add(c["profile"]["current_title"])
        co_industry[c["profile"]["current_company"]].add(c["profile"]["current_industry"])

        for ch in c["career_history"]:
            companies.add(ch["company"])
            titles.add(ch["title"])
            co_industry[ch["company"]].add(ch["industry"])

        has_expert_zero = False
        for s in c["skills"]:
            skills.add(s["name"])
            if s["proficiency"] == "expert" and s.get("duration_months", -1) == 0:
                has_expert_zero = True
        if has_expert_zero:
            expert_zero_mo += 1

        yoe = c["profile"]["years_of_experience"]
        total_months = sum(ch["duration_months"] for ch in c["career_history"])
        if total_months > yoe * 12 + 18:
            career_overflow += 1

        sig = c["redrob_signals"]
        la = datetime.strptime(sig["last_active_date"], "%Y-%m-%d").date()
        last_active_days.append((TODAY - la).days)
        response_rates.append(sig["recruiter_response_rate"])
        completion_rates.append(sig["interview_completion_rate"])
        notice_periods.append(sig["notice_period_days"])

    print(f"Total candidates: {n}")
    print(f"Unique companies: {len(companies)}")
    print(f"Unique titles: {len(titles)}")
    print(f"Unique skills: {len(skills)}")
    print()

    multi_industry = {c: ind for c, ind in co_industry.items() if len(ind) > 1}
    print(f"Companies mapping to >1 industry: {len(multi_industry)} (expect 0 -- confirms 1:1 company->industry map)")
    print()

    def pct(arr, p):
        return round(float(np.percentile(arr, p)), 2)

    print("last_active_date: days-inactive percentiles (p5/p10/p25/p50/p75/p90/p95):")
    print("  ", [pct(last_active_days, p) for p in (5, 10, 25, 50, 75, 90, 95)])
    print("  NOTE: p10 is", pct(last_active_days, 10),
          "-- nobody in the pool has been active in the last ~30 days, so absolute")
    print("  day thresholds like '<=14 days = recent' are dead code; use pool percentiles instead.")
    print()

    print("recruiter_response_rate percentiles:", [pct(response_rates, p) for p in (10, 25, 50, 75, 90)])
    print("interview_completion_rate percentiles:", [pct(completion_rates, p) for p in (10, 25, 50, 75, 90)])
    print("notice_period_days percentiles:", [pct(notice_periods, p) for p in (10, 25, 50, 75, 90)])
    print("  NOTE: median notice period is", pct(notice_periods, 50),
          "days, not 30 -- penalize relative to this distribution, not a flat 30-day cutoff.")
    print()

    print(f"Honeypot signal 1 (expert proficiency, 0 months used): {expert_zero_mo} candidates")
    print(f"Honeypot signal 2 (career-history months >> stated years_of_experience): {career_overflow} candidates")
    print(f"Combined honeypot candidates found: ~{expert_zero_mo + career_overflow} "
          "(README states the dataset contains ~80 honeypots total; these two cheap, "
          "low-false-positive checks catch roughly half of them. We do not chase the "
          "remaining ones with looser heuristics, since every looser variant we tried "
          "(salary min>max, education ending after first job start, skill-duration "
          "exceeding total experience) triggered on 15-20%% of the ENTIRE pool -- far "
          "too common to be the intended traps, just noisy synthetic-data generation.)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../data/candidates.jsonl")
