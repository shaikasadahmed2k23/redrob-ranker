# Redrob Hackathon -- sandbox image
#
# Satisfies the submission_spec.md Section 10.5 sandbox requirement: a
# reproducible environment that runs the ranker end-to-end on a small
# candidate sample (<=100 candidates) within the compute budget (<=5 min,
# CPU-only, no network at inference).
#
# Build:
#   docker build -t redrob-ranker-sandbox .
#
# Run (ranks the bundled 50-candidate sample, mirrors what a hosted
# HuggingFace Space / Streamlit Cloud / Replit instance would do):
#   docker run --rm redrob-ranker-sandbox

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY sandbox/sample_candidates.jsonl sample_candidates.jsonl
COPY validate_submission.py .

# No network access is needed or used at runtime -- everything required is
# already baked into the image at build time.
ENV PYTHONUNBUFFERED=1

CMD ["python", "src/rank.py", "--candidates", "sample_candidates.jsonl", "--out", "sandbox_submission.csv", "--top-n", "20"]
# top-n=20 because the bundled sample has only 50 candidates (the full hackathon
# run against the real candidates.jsonl uses the default top-n=100).
