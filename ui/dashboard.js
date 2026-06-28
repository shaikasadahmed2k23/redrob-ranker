// Falcon -- Redrob Hackathon candidate ranking dashboard
// Pure vanilla JS, no build step, no dependencies. Data is embedded inline
// in dashboard.html as the CANDIDATES constant so this works fully offline,
// double-clicked from a filesystem with no server.

(function () {
  "use strict";

  let sortKey = "score";
  let sortDir = "desc";
  let expandedId = null;

  const tableBody = document.getElementById("tableBody");
  const searchInput = document.getElementById("searchInput");
  const countryFilter = document.getElementById("countryFilter");
  const flagFilter = document.getElementById("flagFilter");
  const resultCount = document.getElementById("resultCount");
  const emptyState = document.getElementById("emptyState");

  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderStats() {
    const n = CANDIDATES.length;
    const india = CANDIDATES.filter((c) => c.country === "India").length;
    const meanYoe = (CANDIDATES.reduce((s, c) => s + c.yoe, 0) / n).toFixed(1);
    const flagged = CANDIDATES.filter(
      (c) => (c.dq_reasons && c.dq_reasons.length) || (c.beh_notes && c.beh_notes.length)
    ).length;

    const stats = [
      [n, "candidates ranked"],
      [india + " / " + n, "India-based"],
      [meanYoe + " yrs", "mean experience"],
      [flagged, "with a noted concern"],
    ];

    document.getElementById("statRow").innerHTML = stats
      .map(
        (s) =>
          '<div class="stat-card"><div class="stat-value">' +
          escapeHtml(s[0]) +
          '</div><div class="stat-label">' +
          escapeHtml(s[1]) +
          "</div></div>"
      )
      .join("");
  }

  function populateFilters() {
    const countries = Array.from(new Set(CANDIDATES.map((c) => c.country))).sort();
    countryFilter.innerHTML =
      '<option value="">All locations</option>' +
      countries.map((c) => '<option value="' + escapeHtml(c) + '">' + escapeHtml(c) + "</option>").join("");
  }

  function matchesFilters(c, query, country, flag) {
    if (country && c.country !== country) return false;
    const hasFlag = (c.dq_reasons && c.dq_reasons.length) || (c.beh_notes && c.beh_notes.length);
    if (flag === "flagged" && !hasFlag) return false;
    if (flag === "clean" && hasFlag) return false;
    if (query) {
      const haystack = (c.title + " " + c.company + " " + c.candidate_id + " " + c.location).toLowerCase();
      if (!haystack.includes(query.toLowerCase())) return false;
    }
    return true;
  }

  function sortCandidates(list) {
    const dir = sortDir === "asc" ? 1 : -1;
    return list.slice().sort((a, b) => {
      let av = a[sortKey];
      let bv = b[sortKey];
      if (typeof av === "string") av = av.toLowerCase();
      if (typeof bv === "string") bv = bv.toLowerCase();
      if (av < bv) return -1 * dir;
      if (av > bv) return 1 * dir;
      return a.rank - b.rank;
    });
  }

  function componentLabel(key) {
    const labels = {
      title: "Title relevance",
      semantic: "Semantic similarity",
      skill: "Trust-weighted skill",
      experience: "Experience-band fit",
      company: "Company quality",
      location: "Location fit",
      education: "Education tier",
    };
    return labels[key] || key;
  }

  function renderDetailRow(c) {
    const compRows = Object.keys(c.components)
      .map((key) => {
        const val = c.components[key];
        const pct = Math.max(0, Math.min(100, val * 100));
        return (
          '<div class="comp-row"><div class="comp-label">' +
          escapeHtml(componentLabel(key)) +
          '</div><div class="comp-track"><div class="comp-fill" style="width:' +
          pct.toFixed(0) +
          '%;"></div></div><div class="comp-val">' +
          val.toFixed(2) +
          "</div></div>"
        );
      })
      .join("");

    const notes = (c.dq_reasons || []).concat(c.beh_notes || []);
    const notesHtml = notes.length
      ? '<div class="notes-list">' +
        notes.map((n) => '<div class="note-item">' + escapeHtml(n) + "</div>").join("") +
        "</div>"
      : '<div class="notes-list"><div class="note-item" style="background:var(--teal-light); color:#0E6B5F;">No concerns noted for this candidate.</div></div>';

    return (
      '<tr class="detail-row"><td colspan="7"><div class="detail-panel">' +
      '<div><div class="detail-section-title">Why this rank</div>' +
      '<div class="reasoning-text">' +
      escapeHtml(c.reasoning) +
      "</div>" +
      '<div class="headline-text">"' +
      escapeHtml(c.headline) +
      '"</div>' +
      '<div class="formula-row">' +
      '<div class="formula-chip"><div class="fc-val">' + c.core_fit.toFixed(2) + '</div><div class="fc-label">core fit</div></div>' +
      '<div class="formula-op">&times;</div>' +
      '<div class="formula-chip"><div class="fc-val">' + c.dq_mult.toFixed(2) + '</div><div class="fc-label">disqualifier</div></div>' +
      '<div class="formula-op">&times;</div>' +
      '<div class="formula-chip"><div class="fc-val">' + c.beh_mult.toFixed(2) + '</div><div class="fc-label">behavioral</div></div>' +
      '<div class="formula-op">=</div>' +
      '<div class="formula-chip result"><div class="fc-val">' + c.score.toFixed(3) + '</div><div class="fc-label">final score</div></div>' +
      "</div>" +
      (notes.length ? notesHtml : "") +
      "</div>" +
      '<div><div class="detail-section-title">Core fit components</div>' +
      '<div class="component-bars">' +
      compRows +
      "</div>" +
      (notes.length ? "" : notesHtml) +
      "</div>" +
      "</div></td></tr>"
    );
  }

  function render(options) {
    options = options || {};
    const query = searchInput.value.trim();
    const country = countryFilter.value;
    const flag = flagFilter.value;

    let filtered = CANDIDATES.filter((c) => matchesFilters(c, query, country, flag));
    filtered = sortCandidates(filtered);

    resultCount.textContent = filtered.length + " of " + CANDIDATES.length + " shown";
    emptyState.style.display = filtered.length === 0 ? "block" : "none";

    const rows = [];
    filtered.forEach((c) => {
      const isExpanded = c.candidate_id === expandedId;
      const hasFlag = (c.dq_reasons && c.dq_reasons.length) || (c.beh_notes && c.beh_notes.length);
      const rankClass = c.rank <= 10 ? "rank-pill top10" : "rank-pill";

      rows.push(
        '<tr class="row' + (isExpanded ? " expanded" : "") + '" data-id="' + escapeHtml(c.candidate_id) + '">' +
          '<td><span class="' + rankClass + '">' + c.rank + "</span></td>" +
          '<td><div class="cand-id">' + escapeHtml(c.candidate_id) + "</div></td>" +
          '<td><div class="cand-title">' + escapeHtml(c.title) + '</div><div class="cand-company">' + escapeHtml(c.company) + '</div><div class="cand-meta-mobile">' + escapeHtml(c.candidate_id) + " · " + c.yoe.toFixed(1) + " yrs · " + escapeHtml(c.location.split(",")[0]) + "</div></td>" +
          "<td>" + c.yoe.toFixed(1) + " yrs</td>" +
          "<td>" + escapeHtml(c.location.split(",")[0]) + "</td>" +
          '<td class="score-cell">' + c.score.toFixed(3) + "</td>" +
          '<td><svg class="expand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg></td>' +
        "</tr>"
      );
      if (isExpanded) {
        rows.push(renderDetailRow(c));
      }
    });

    tableBody.innerHTML = rows.join("");

    Array.from(tableBody.querySelectorAll("tr.row")).forEach((tr) => {
      tr.setAttribute("tabindex", "0");
      tr.setAttribute("role", "button");
      const toggle = () => {
        const id = tr.getAttribute("data-id");
        expandedId = expandedId === id ? null : id;
        render({ restoreFocusTo: id });
      };
      tr.addEventListener("click", toggle);
      tr.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggle();
        }
      });
    });

    // Re-render rebuilds the whole tbody via innerHTML, which destroys and
    // recreates every row element -- this silently drops keyboard focus back
    // to <body>. When the row toggle itself triggered this render (not a
    // search/filter/sort change), restore focus to that same row so repeated
    // Enter/Space presses keep working and a keyboard user doesn't lose
    // their place in the list. We deliberately do NOT do this on every
    // render -- search/filter/sort changes call render() too, and stealing
    // focus away from the search input mid-keystroke would break typing.
    if (options.restoreFocusTo) {
      const toRefocus = tableBody.querySelector('tr.row[data-id="' + options.restoreFocusTo + '"]');
      if (toRefocus) toRefocus.focus();
    }
  }

  function attachSortHandlers() {
    Array.from(document.querySelectorAll("th.sortable")).forEach((th) => {
      th.setAttribute("tabindex", "0");
      th.setAttribute("role", "button");
      const activate = () => {
        const key = th.getAttribute("data-key");
        if (sortKey === key) {
          sortDir = sortDir === "asc" ? "desc" : "asc";
        } else {
          sortKey = key;
          sortDir = key === "candidate_id" || key === "title" || key === "location" ? "asc" : "desc";
        }
        Array.from(document.querySelectorAll("th.sortable")).forEach((h) => {
          h.classList.remove("active");
          const arrow = h.querySelector(".arrow");
          if (arrow) arrow.remove();
        });
        th.classList.add("active");
        const span = document.createElement("span");
        span.className = "arrow";
        span.textContent = sortDir === "asc" ? "▲" : "▼";
        th.appendChild(span);
        render();
      };
      th.addEventListener("click", activate);
      th.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          activate();
        }
      });
    });
  }

  searchInput.addEventListener("input", render);
  countryFilter.addEventListener("change", render);
  flagFilter.addEventListener("change", render);

  renderStats();
  populateFilters();
  attachSortHandlers();
  render();
})();
