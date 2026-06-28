# Dashboard

A standalone, single-file dashboard for browsing the top-100 ranked
candidates — built so the ranking output is something a recruiter can
actually click through, not just a CSV to stare at.

![Desktop overview](screenshots/desktop_overview.png)

## Running it

There's nothing to install and nothing to build. Just open the file:

```bash
open ui/dashboard.html        # macOS
xdg-open ui/dashboard.html    # Linux
# or just double-click it in a file browser
```

The candidate data (the same top-100 produced by `src/rank.py`) is embedded
directly inside `dashboard.html` as a JSON literal, so the page works fully
offline — no server, no `fetch()`, no CORS issues from opening a local file.

Click any row to expand it and see the full score breakdown: the
`core fit × disqualifier × behavioral` formula computed on that exact
candidate, the seven core-fit components as bars, and any concerns the
ranker noted (low responsiveness, location/visa mismatch, etc.).

![Score breakdown detail view](screenshots/desktop_detail.png)

It's responsive down to mobile — the table collapses into cards below
800px width.

![Mobile view](screenshots/mobile_overview.png)

## Regenerating the data

If you re-run the ranker and want the dashboard to reflect a new result,
regenerate `top100_data.json` and re-embed it:

```bash
cd src
python3 -c "
import sys, json
sys.path.insert(0, '.')
from rank import load_candidates, score_candidates, build_reasoning

candidates = load_candidates('/path/to/candidates.jsonl')
results = score_candidates(candidates)
results.sort(key=lambda r: (-r['score'], r['candidate_id']))
top = results[:100]

out = []
for rank, r in enumerate(top, start=1):
    c = r['candidate']; p = c['profile']
    out.append({
        'rank': rank, 'candidate_id': r['candidate_id'], 'score': round(r['score'], 6),
        'core_fit': round(r['core_fit'], 4), 'dq_mult': round(r['dq_mult'], 4),
        'beh_mult': round(r['beh_mult'], 4),
        'components': {k: round(v, 4) for k, v in r['components'].items()},
        'title': p['current_title'], 'company': p['current_company'], 'yoe': p['years_of_experience'],
        'location': p['location'], 'country': p['country'], 'headline': p['headline'],
        'reasoning': build_reasoning(r), 'dq_reasons': r['dq_reasons'], 'beh_notes': r['beh_notes'],
    })

with open('../ui/top100_data.json', 'w') as f:
    json.dump(out, f)
"
```

Then re-embed it into `dashboard.html` by replacing the JSON literal after
`const CANDIDATES = ` with the contents of the regenerated
`top100_data.json`.

## Testing

The dashboard is plain HTML/CSS/vanilla JS with no framework and no build
step, but it's covered by a Playwright test suite that loads the actual
file in a real browser and exercises every interactive path: search,
location/concern filters, column sorting, row expand/collapse by mouse and
by keyboard, the empty-results state, and responsive layout at desktop,
tablet, and mobile widths.

```bash
npm install        # installs playwright, the only dependency (dev-only, for tests)
npm test           # runs all 6 test files, asserts on row counts / DOM state / zero console errors
```

All six suites currently pass with zero console or page errors. Worth
knowing: an early version had a real bug here — expanding a row by keyboard
(Enter/Space) rebuilds the table body via `innerHTML`, which silently drops
focus back to `<body>`, so a second Enter press did nothing instead of
collapsing the row. Fixed by re-focusing the toggled row after re-render,
but *only* when the render was triggered by that toggle — naively restoring
focus on every render would otherwise steal focus away from the search box
mid-keystroke. Covered by `tests/test_keyboard.js` and
`tests/test_search_after_expand.js` so it can't silently regress.

## Files

```
dashboard.html       the actual deliverable -- open this
dashboard.js          all interactivity (search, filter, sort, expand/collapse)
top100_data.json      the data embedded into dashboard.html (kept separately for re-generation)
tests/                 Playwright QA suite, run with `npm test`
screenshots/           clean screenshots used in this README
```
