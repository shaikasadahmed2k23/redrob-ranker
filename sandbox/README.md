# Sandbox

Satisfies submission_spec.md §10.5: a reproducible hosted environment that
runs the ranker end-to-end on a small candidate sample (≤100 candidates)
within the compute budget.

## Option A: Docker (self-contained, works anywhere)

```bash
docker build -t redrob-ranker-sandbox .
docker build -t redrob-ranker-sandbox .
```

This builds and runs unmodified, with no external dependencies beyond the
public Python base image at build time, and **no network access at runtime**
— matching the actual compute constraints of the real ranking step.

It ranks the bundled 50-candidate sample (`sandbox/sample_candidates.jsonl`,
the same 50 candidates from the hackathon bundle's `sample_candidates.json`,
converted to JSONL) and writes the top 20 to `sandbox_submission.csv` inside
the container.

To pull the output file out of the container:

```bash
docker run --rm -v "$(pwd)/sandbox-output:/app/out" redrob-ranker-sandbox \
  python src/rank.py --candidates sample_candidates.jsonl --out out/sandbox_submission.csv --top-n 20
```

## Option B: Hosted platforms

If you'd rather use one of the platforms explicitly listed as acceptable in
submission_spec.md §10.5 (HuggingFace Spaces, Streamlit Cloud, Replit,
Google Colab, Binder), the same `src/` code works unmodified — point any of
them at this repo and run:

```bash
pip install -r requirements.txt
python src/rank.py --candidates sandbox/sample_candidates.jsonl --out submission.csv --top-n 20
```

**HuggingFace Spaces / Streamlit Cloud**: wrap the same call in a minimal
`app.py` that calls `subprocess.run([...])` or imports `src/rank.py`
directly and displays the resulting CSV — the ranking logic itself doesn't
change.

**Google Colab / Binder**: a single notebook cell running the two commands
above is sufficient; no GPU runtime needed.

## What this sandbox proves

- The exact same `src/rank.py` entrypoint used for the full 100K run works
  unmodified on a small sample.
- No network calls, no GPU, fast runtime (<1 second on 50 candidates) —
  consistent with the ~50-65 second measured runtime on the full 100K pool.
- The full Stage-3 reproduction (100K candidates, 5-minute budget) happens
  against the real `candidates.jsonl` using the identical command documented
  in the README and `submission_metadata.yaml`'s `reproduce_command`.
