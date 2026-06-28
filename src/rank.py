#!/usr/bin/env python3
"""
rank.py -- Redrob Hackathon: Intelligent Candidate Discovery & Ranking

Produces the top-100 ranked CSV submission from the full candidate pool.

Usage:
    python rank.py --candidates ./candidates.jsonl --out ./submission.csv

Design summary (see docs/approach.md and the submission deck for full detail):

  score = disqualifier_multiplier
        * behavioral_multiplier
        * core_fit_score

  core_fit_score is a weighted blend of:
    - title relevance tier               (0.22)
    - career-history semantic similarity  (0.20)  [TF-IDF + LSA vs JD text]
    - trust-weighted skill match           (0.20)
    - years-of-experience band fit         (0.13)
    - company quality / AI-relevance       (0.15)
    - location fit                          (0.07)
    - education tier                        (0.03)

Honeypots (subtly-impossible profiles) are detected and removed entirely
before scoring, rather than just down-weighted, per the hackathon's explicit
instruction to keep the honeypot rate in the top 100 below 10%.

Runtime target: well under 5 minutes on a 16GB CPU-only machine for the full
100K-candidate pool. No network calls, no GPU, no hosted LLM calls anywhere
in this script.
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from features import (
    is_honeypot,
    disqualifier_multiplier,
    title_score,
    experience_score,
    company_quality_score,
    skill_match_score,
    career_history_relevance_text,
    education_score,
    location_fit_score,
    behavioral_multiplier,
)
from semantic import build_semantic_index, semantic_similarity

# Core fit component weights (must sum to 1.0)
WEIGHTS = {
    "title": 0.22,
    "semantic": 0.20,
    "skill": 0.20,
    "experience": 0.13,
    "company": 0.15,
    "location": 0.07,
    "education": 0.03,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

JD_TEXT = """
Senior AI Engineer, Founding Team, Redrob AI. Own the intelligence layer:
ranking, retrieval, and matching systems for candidate-JD search. Production
experience with embeddings-based retrieval systems (sentence-transformers,
OpenAI embeddings, BGE, E5), deployed to real users -- handling embedding
drift, index refresh, retrieval-quality regression in production. Production
experience with vector databases or hybrid search infrastructure: Pinecone,
Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, FAISS. Strong Python,
code quality matters. Hands-on experience designing evaluation frameworks for
ranking systems: NDCG, MRR, MAP, offline-to-online correlation, A/B test
interpretation. Shipped at least one end-to-end ranking, search, or
recommendation system to real users at meaningful scale. Hybrid retrieval,
LLM-based re-ranking, learning-to-rank. Prefers candidates who understood
retrieval and ranking before it was fashionable, with genuine production
deployment experience rather than only recent LangChain-and-OpenAI projects.
Wants a builder who ships, not only a researcher; prefers candidates with
applied ML or AI roles at product companies rather than purely services
companies. 5-9 years experience, Pune or Noida, India preferred.
""".strip()


def load_candidates(path: str):
    candidates = []
    opener = open
    if str(path).endswith(".gz"):
        import gzip
        opener = gzip.open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                candidates.append(json.loads(line))
    return candidates


def score_candidates(candidates: list[dict]) -> list[dict]:
    """Returns a list of result dicts, one per non-honeypot candidate, with all components."""
    texts = [career_history_relevance_text(c) for c in candidates]
    jd_vec, cand_matrix, _, _ = build_semantic_index(JD_TEXT, texts)
    sem_scores = semantic_similarity(jd_vec, cand_matrix)

    results = []
    honeypot_count = 0

    for i, c in enumerate(candidates):
        hp, hp_reason = is_honeypot(c)
        if hp:
            honeypot_count += 1
            continue  # excluded entirely, per hackathon instructions

        comp = {
            "title": title_score(c),
            "semantic": float(sem_scores[i]),
            "skill": skill_match_score(c),
            "experience": experience_score(c),
            "company": company_quality_score(c),
            "location": location_fit_score(c),
            "education": education_score(c),
        }
        core_fit = sum(WEIGHTS[k] * comp[k] for k in WEIGHTS)

        dq_mult, dq_reasons = disqualifier_multiplier(c)
        beh_mult, beh_notes = behavioral_multiplier(c)

        final_score = core_fit * dq_mult * beh_mult

        results.append({
            "candidate_id": c["candidate_id"],
            "score": final_score,
            "core_fit": core_fit,
            "components": comp,
            "dq_mult": dq_mult,
            "dq_reasons": dq_reasons,
            "beh_mult": beh_mult,
            "beh_notes": beh_notes,
            "candidate": c,
        })

    print(f"[rank.py] Excluded {honeypot_count} honeypot candidates before scoring.", file=sys.stderr)
    return results


def _most_relevant_career_snippet(c: dict, exclude_current: bool = True) -> str:
    """
    Finds the single career_history entry whose title is most relevant to the
    JD (highest title tier), and names the specific JD-relevant keywords its
    description mentions -- giving the reasoning a real, candidate-specific
    anchor instead of generic praise.

    Deliberately paraphrases rather than quoting verbatim: exploration of the
    dataset showed only ~168 unique description sentence templates reused
    across all 100K candidates (some sentences appear 1000s of times), so a
    verbatim quote is not a reliable per-candidate signal and risks reading as
    templated reasoning at Stage 4 review even though it's genuinely
    per-candidate. Naming the *combination* of role + company + the specific
    keywords found is more distinctive than the sentence itself.
    """
    from reference_data import title_tier, CORE_SKILLS

    history = c.get("career_history", [])
    if exclude_current:
        history = [ch for ch in history if not ch.get("is_current")]
    if not history:
        return ""

    best = max(history, key=lambda ch: title_tier(ch["title"]))
    desc = best.get("description", "").lower()

    keywords = sorted(CORE_SKILLS, key=lambda k: -CORE_SKILLS[k])
    found = [kw for kw in keywords if CORE_SKILLS[kw] >= 0.7 and kw.lower() in desc]
    found = found[:3]

    if found:
        kw_text = ", ".join(found)
        return f"as {best['title']} at {best['company']} ({best['duration_months']}mo) their role description specifically covers {kw_text}"

    return f"previously {best['title']} at {best['company']} ({best['duration_months']}mo)"


def _top_trusted_skills(c: dict, k: int = 3) -> list[str]:
    """Top-k skills ranked by JD-relevance * evidence (endorsements + duration), not just keyword presence."""
    from reference_data import skill_weight

    scored = []
    for s in c.get("skills", []):
        w = skill_weight(s["name"])
        if w < 0.3:
            continue
        evidence = s.get("endorsements", 0) * 0.5 + s.get("duration_months", 0) * 0.5
        scored.append((w * (1 + evidence / 100.0), s))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:k]]


def build_reasoning(r: dict) -> str:
    """
    Produces a 1-2 sentence, candidate-specific reasoning string. Deliberately
    avoids templated boilerplate (e.g. "title closely matches the role" on
    every row) since Stage 4 manual review explicitly samples 10 rows and
    checks whether reasonings are substantively different from each other.
    Instead, each reasoning anchors on: (a) a concrete detail pulled from the
    candidate's most relevant past role, (b) their best-evidenced skills
    (trust-weighted, not just listed), and (c) an honest flag of whatever is
    actually holding the candidate back, even at high ranks.
    """
    c = r["candidate"]
    p = c["profile"]
    sig = c["redrob_signals"]
    comp = r["components"]

    title = p["current_title"]
    company = p["current_company"]
    yoe = p["years_of_experience"]

    snippet = _most_relevant_career_snippet(c)
    trusted_skills = _top_trusted_skills(c)
    skill_phrase = ""
    if trusted_skills:
        names = ", ".join(s["name"] for s in trusted_skills)
        total_endorse = sum(s.get("endorsements", 0) for s in trusted_skills)
        if total_endorse >= 15:
            skill_phrase = f"strong, endorsement-backed depth in {names}"
        else:
            skill_phrase = f"relevant but lightly-endorsed skills in {names}"

    lead = f"{title} at {company}, {yoe:.1f} yrs experience"
    if snippet:
        lead += f"; {snippet}"
    if skill_phrase:
        lead += f"; {skill_phrase}"

    # Collect honest concerns -- always surface at least one if any exist,
    # even for top-ranked candidates, per the spec's "honest concerns" check.
    concerns = list(r["dq_reasons"]) + list(r["beh_notes"])

    # Add a concern about experience-band mismatch if relevant and not already covered
    if comp["experience"] < 0.6:
        if yoe < 5:
            concerns.append(f"only {yoe:.1f} yrs experience, below the JD's 5-9 yr band")
        else:
            concerns.append(f"{yoe:.1f} yrs experience is above the JD's core 5-9 yr band")

    if comp["location"] < 0.5:
        concerns.append(f"based in {p['location']}, {p['country']} -- outside the JD's India preference, no visa sponsorship")

    if not sig.get("verified_email") or not sig.get("verified_phone"):
        concerns.append("unverified contact info")

    notice = sig.get("notice_period_days")
    if notice and notice > 90 and "long notice period" not in " ".join(concerns):
        concerns.append(f"{notice}-day notice period")

    if concerns:
        # Surface at most the two most material concerns, to keep it concise and honest
        concern_text = "; but " + "; ".join(concerns[:2])
    else:
        concern_text = ""

    reasoning = lead + concern_text + "."

    # If still too long, trim the concern clause first (least essential),
    # then the lead, always cutting at a clause boundary (";") rather than
    # mid-word, so the output never ends on a dangling truncation.
    if len(reasoning) > 340:
        reasoning = (lead + ".")
        if len(reasoning) > 340:
            clauses = lead.split("; ")
            trimmed = clauses[0]
            for clause in clauses[1:]:
                if len(trimmed) + 2 + len(clause) > 336:
                    break
                trimmed += "; " + clause
            reasoning = trimmed + "."
    return reasoning


def write_submission(results: list[dict], out_path: str, top_n: int = 100):
    results.sort(key=lambda r: (-r["score"], r["candidate_id"]))
    top = results[:top_n]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank, r in enumerate(top, start=1):
            writer.writerow([
                r["candidate_id"],
                rank,
                f"{r['score']:.6f}",
                build_reasoning(r),
            ])
    print(f"[rank.py] Wrote {len(top)} rows to {out_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl (or .jsonl.gz)")
    parser.add_argument("--out", required=True, help="Path to write the output submission CSV")
    parser.add_argument("--top-n", type=int, default=100)
    args = parser.parse_args()

    t0 = time.time()
    candidates = load_candidates(args.candidates)
    print(f"[rank.py] Loaded {len(candidates)} candidates in {time.time()-t0:.1f}s", file=sys.stderr)

    t1 = time.time()
    results = score_candidates(candidates)
    print(f"[rank.py] Scored {len(results)} candidates in {time.time()-t1:.1f}s", file=sys.stderr)

    write_submission(results, args.out, top_n=args.top_n)
    print(f"[rank.py] Total runtime: {time.time()-t0:.1f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
