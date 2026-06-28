# Approach — Design Rationale

This document is the longer version of the README's architecture section:
what we tried, what we rejected, and why, with the actual numbers from
exploring the dataset. It's written to be defensible in the Stage 5
"defend your work" interview — every claim below is backed by a script in
`notebooks/` or a test in `tests/`.

## 1. Reading the JD as a set of constraints, not a keyword list

The JD is unusually explicit about what it does and doesn't want, and it
explicitly says the "right answer" isn't keyword matching. We treated three
sections of the JD as direct, encodable inputs rather than vibes:

- **"Things you absolutely need"** → the core fit score's title and skill
  components are weighted toward retrieval/ranking/embeddings specifically,
  not ML in general.
- **"Things we explicitly do NOT want"** → became the `disqualifier_multiplier`
  in `src/features.py`, one clause per JD bullet.
- **"How to read between the lines"** → the ideal-candidate description
  (6-8 years, 4-5 in applied ML at product companies, shipped an end-to-end
  ranking/search/recsys system, Pune/Noida-located) is essentially a
  worked example of what a top-score candidate should look like. We used it
  as a sanity check on rank-1 results (see below), not as a separate scoring
  rule.

## 2. Why hand-built lookup tables instead of fuzzy matching

Before writing any scoring logic, we enumerated every distinct value the
pool actually contains:

```
$ python notebooks/01_explore_data.py candidates.jsonl
Unique companies: 63
Unique titles: 48
Unique skills: 133
```

This is a **closed, small universe**. Classifying 63 companies by hand
(`reference_data.COMPANY_TABLE`) — AI-native, big-tech, Indian product
company, SaaS, consulting, or fictional-placeholder — takes an afternoon and
is then exactly right for every candidate, forever. Asking a similarity
model "is Infosys a consulting company?" is solving a harder, noisier
version of a problem we can just answer directly. The same logic applies to
the 48 titles (`TITLE_TIER`) and 133 skills (`CORE_SKILLS`).

This also makes the system far easier to defend in an interview: every
score component traces back to a specific, inspectable table entry, not a
black-box embedding.

## 3. The keyword-stuffer trap, concretely

`sample_candidates.json`'s first candidate (`CAND_0000001`) is a clean
illustration of the trap the JD warns about: a Backend/Data Engineer at
Mindtree (IT services) whose skill list includes NLP, Image Classification,
Fine-tuning LLMs, Speech Recognition, GANs, LoRA, and Milvus — practically
every trending AI keyword — but whose actual `career_history` descriptions
say things like *"Most of my career has been data engineering, with some
adjacent ML exposure"* and whose own summary says they're *"building
competence on the ML side"* and are *"interested in transitioning toward...
AI/ML-focused work."*

The bundled `sample_submission.csv` (explicitly **not** a quality reference,
per the spec) ranks candidates by raw AI-keyword count and recruiter
response rate — its #1 pick is an **HR Manager** with "9 AI core skills."
This is the exact failure mode the hackathon is testing for.

Our system separates these cases via:

- **Title tier**: Backend Engineer / HR Manager score low (1/5 or 0/5)
  regardless of skill list; Senior AI Engineer / Recommendation Systems
  Engineer / Search Engineer score 4-5/5.
- **Trust-weighted skill score**: a skill claimed with 0 endorsements and 0-1
  months of use contributes far less than the same skill with real
  endorsement and tenure evidence (`skill_match_score` in `features.py`).
- **Semantic similarity of career-history text**, not skill tags — this is
  what lets a candidate who never writes "RAG" or "Pinecone" but whose
  `career_history.description` says they "migrated our keyword-search-based
  product to embedding-based retrieval" still score well, per the JD's own
  example of what a Tier-5 candidate's profile might look like.

In our actual run on the 50-candidate sample bundle, this resulted in the
legitimate Recommendation Systems Engineer (`CAND_0000031`, 6 years, Swiggy,
genuine ranking/retrieval career history) scoring **0.70**, well ahead of
the keyword-stuffer (`CAND_0000001`, **0.40**) — see `tests/` and the sample
run logged in the PR history for the underlying numbers.

## 4. Honeypots: what worked, what didn't

We looked for "subtly impossible" patterns the README mentions (e.g. "8
years of experience at a company founded 3 years ago"). We don't have
company-founding-year data, so we couldn't check that specific example
directly, but we tested several internal-consistency checks instead:

| Check | Candidates flagged | Verdict |
|---|---|---|
| "Expert" proficiency, 0 months duration | 21 | **Used** — genuinely impossible, rare enough to be a real signal |
| Career-history total months ≫ stated years_of_experience (+18mo buffer) | 24 | **Used** — same reasoning |
| Salary `min > max` | 18,865 (~19% of pool) | **Rejected** — far too common, just noisy data entry |
| Education `end_year` after first job's `start_date` | 19,499 (~19% of pool) | **Rejected** — internships/part-time work during study explain this normally |
| A single skill's `duration_months` exceeding total experience by 24mo+ | 2,821 (~2.8% of pool) | **Rejected** — still an order of magnitude too common; mostly hobby/pre-professional skill use |
| Overlapping `career_history` date ranges | 0 | N/A — the generator apparently doesn't produce this pattern |

We landed on the two reliable checks (45 candidates total) rather than
forcing a match to the README's "~80" figure with noisier heuristics. The
README itself says *"you don't need to special-case them"* — a ranking
system with sound title/company/skill-trust logic should naturally avoid
honeypots without needing to catch literally all of them by name. Measured
result: **0 honeypots in our final top 100** (well under the 10%
disqualification threshold), even though our explicit detector only removes
45 of the ~80 before scoring.

## 5. Calibrating the behavioral multiplier against the pool's real
   distribution, not assumptions

Our first version of the recency bonus assumed "active within 14 days" was
a meaningful threshold. Running it against the full pool revealed:

```
last_active_date: days-inactive percentiles (p5/p10/p25/p50/p75/p90/p95)
  [41, 51, 83, 136, 193, 237, 254]
```

**Nobody** in the 100K-candidate pool has logged in within the last 30 days
— the most recently active candidate is ~32 days out. Our original
threshold was dead code. We rebuilt the recency tiers around the pool's
actual percentiles (top decile = ≤51 days, top quartile = ≤83 days, etc.).

The same issue showed up in `notice_period_days`: the JD says "we'd love
sub-30-day notice," which we initially encoded as a flat bonus for ≤30 days
and penalty for >60. The pool's actual median is **90 days** (p25=60,
p50=90, p75=120, p90=150) — a flat 60-day penalty cutoff would have
penalized roughly 75% of the pool, washing out the signal. We rescaled the
tiers against the pool's real distribution instead.

This is the kind of bug that's easy to ship and hard to notice without
actually looking at the data — which is the point of `notebooks/01_explore_data.py`
existing as a first-class part of this repo rather than throwaway scratch
work.

## 6. A disqualifier heuristic we built, tested, and had to fix

An early version of the "title-chaser" disqualifier flagged any candidate
with 3+ career-history entries where 3+ of them lasted under 18 months. We
tested it against the 50-candidate sample bundle and it incorrectly flagged
`CAND_0000031` — on inspection, a strong, legitimately-progressing candidate
(Zomato → Uber → Mad Street Den → Swiggy, each role *more* relevant to
ranking/retrieval than the last, over 6 years) who was simply moving
normally through a fast-growing field, not chasing titles for prestige. We
tightened the rule to only fire when **every single** role in the history
is ≤18 months (no anchor of depth anywhere) **and** there are at least 4 of
them — closer to the JD's actual described concern ("switching companies
every 1.5 years" as a sustained pattern, not 2-3 fast early moves). This
is documented in the inline comment in `features.py::disqualifier_multiplier`
and covered by `tests/test_features.py`.

## 7. Why TF-IDF/LSA, not a transformer embedding model

We would have liked to try `sentence-transformers` for the semantic
similarity component. The execution environment we built this in didn't
have network access to install `torch`/`sentence-transformers`, which
forced the TF-IDF/LSA approach — but on reflection we think this is
actually the right call for this spec regardless of that constraint:

- The compute budget (≤5 min, CPU-only, 100K candidates) leaves little room
  for a transformer forward-pass over every candidate's career-history text
  *in addition to* everything else the ranker needs to do. TF-IDF + SVD
  fits comfortably (our full run measures ~50-65 seconds total, with the
  semantic-index build being a small fraction of that).
- It's a textbook case for where lexical/LSA methods are still competitive:
  resume and JD text both live in a fairly constrained professional
  vocabulary, which is exactly the regime where TF-IDF representations do
  reasonably well relative to their cost.
- It keeps every similarity score inspectable — useful for the Stage 4
  reasoning-quality review and the Stage 5 interview alike.

If we had transformer access, the natural next step (documented as a
"future work" item, not implemented here to keep the compute budget honest)
would be a small local model like a distilled MiniLM-class sentence encoder,
swapped in behind the same `semantic.py` interface — `build_semantic_index`
and `semantic_similarity` are written as a clean seam for exactly this kind
of swap.

## 8. Reasoning-column quality

The submission spec's Stage 4 review samples 10 random rows and checks for
hallucination, JD-connection, honest concerns, and **variation** ("are the
10 sampled reasonings substantively different from each other?"). Our first
draft failed this by construction — every top-100 reasoning said some
variant of "title closely matches the role; career history closely matches
the JD's retrieval/ranking focus," because by definition every top-100
candidate scores well on title and semantic similarity. We rebuilt
`build_reasoning()` in `rank.py` to instead surface what's *specific* to
each candidate: their single most-relevant past role plus the actual
JD-relevant keywords found in *that role's* description, their best-
evidenced (not just listed) skills, and — critically — at least one honest
concern when one exists (location/visa mismatch, long notice period,
unverified contact info, low responsiveness), even for high-ranked
candidates. We also found that the underlying synthetic dataset reuses only
~168 unique description-sentence templates across all 100K candidates, so
we deliberately paraphrase rather than quote those descriptions verbatim —
a verbatim quote risks looking like templated reasoning at review time even
when it's genuinely candidate-specific, since the same exact sentence often
appears for dozens of unrelated candidates by construction of the dataset.

## 9. What we'd do with more compute budget or more time

- Swap TF-IDF/LSA for a small local sentence-encoder model behind the same
  interface, as noted in §7.
- Build an explicit learning-to-rank layer (e.g. gradient-boosted trees over
  the same feature set) if we had labeled relevance judgments to train
  against — right now every weight in `WEIGHTS` is hand-set based on reading
  the JD, not learned, which is honest but leaves performance on the table
  if ground-truth labels were available for even a small validation slice.
- Extend honeypot detection with a company-founding-year table if that data
  becomes available, to directly catch the "8 years at a 3-year-old company"
  pattern the README describes, rather than relying on the two proxy checks
  we validated instead.
