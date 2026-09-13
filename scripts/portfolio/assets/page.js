/* The page is a client over the snapshot: it holds no data of its own and derives no number.
 *
 * Two sources, one code path. An inlined snapshot is used when the renderer put one there, which
 * is what makes the local file work on a double-click; otherwise the neighbouring `metrics.json`
 * is fetched, which is what makes the published page show a new collection on reload without
 * having been rebuilt. Neither mode is the degraded one.
 *
 * No framework and no CDN: sorting, filtering and the detail rows are the hundred lines below, and
 * a dependency fetched at view time is a page that breaks when somebody else's CDN does.
 */
(function () {
  "use strict";

  var state = { snapshot: null, sort: { key: "score", dir: "desc" }, filter: "", open: {} };

  function esc(value) {
    return String(value === null || value === undefined ? "" : value).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  /* Absent is not zero and not empty: the three read differently and must look different. */
  function absent() {
    return '<span class="absent" title="not recorded">&mdash;</span>';
  }
  function na(why) {
    return '<span class="na" title="' + esc(why) + '">n/a</span>';
  }
  function num(value) {
    return value === null || value === undefined ? absent() : esc(value);
  }
  function day(value) {
    return value ? esc(String(value).slice(0, 10)) : absent();
  }

  function group(entry, name) {
    return entry[name] || null;
  }

  function isRPackage(entry) {
    var identity = group(entry, "identity");
    return !!(identity && identity.is_r_package);
  }

  var CONCLUSION_RANK = { failure: 0, timed_out: 0, startup_failure: 0, cancelled: 1, success: 3 };
  var CRAN_RANK = { ERROR: 0, FAIL: 0, WARN: 1, NOTE: 2, OK: 3 };

  function columns() {
    var list = [
      { key: "package", label: "Package", sort: function (e) { return e.slug; }, cell: packageCell },
      { key: "score", label: "Attention", num: true, sort: function (e) { return e.score ? e.score.value : null; }, cell: scoreCell },
      { key: "reasons", label: "Why", cell: reasonsCell },
      { key: "ci", label: "CI", sort: ciSort, cell: ciCell },
      { key: "unreleased", label: "Unreleased", num: true, sort: function (e) { return e.release ? e.release.commits_since : null; }, cell: unreleasedCell },
      { key: "cran", label: "CRAN", sort: cranSort, cell: cranCell },
      { key: "issues", label: "Issues", num: true, sort: function (e) { return e.tickets ? e.tickets.open_issues : null; }, cell: issuesCell },
      { key: "prs", label: "PRs", num: true, sort: function (e) { return e.tickets ? e.tickets.open_pull_requests : null; }, cell: prsCell },
      { key: "activity", label: "Last commit", sort: function (e) { return e.activity ? e.activity.last_commit_at : null; }, cell: activityCell }
    ];
    if (collected("template")) {
      list.push({
        key: "template",
        label: "Template",
        num: true,
        sort: function (e) { return e.template && e.template.collected ? e.template.outstanding : null; },
        cell: templateCell
      });
    }
    return list;
  }

  function collected(name) {
    var flags = state.snapshot.groups_collected || {};
    return flags[name] === true;
  }

  function packageCell(entry) {
    var identity = group(entry, "identity") || {};
    var html = '<div class="slug">' + esc(entry.slug) + (identity.archived ? ' <span class="warn">archived</span>' : "") + "</div>";
    if (identity.package) {
      html += '<div class="pkg">' + esc(identity.package) + (identity.version ? " " + esc(identity.version) : "") + "</div>";
    } else if (identity.is_r_package === false) {
      html += '<div class="pkg">not an R package</div>';
    }
    if (entry.stale) {
      html += '<div class="pkg">stale: last observed ' + (entry.observed_at ? day(entry.observed_at) : "never") + "</div>";
    }
    return html;
  }

  function scoreCell(entry) {
    if (!entry.score) return absent();
    return esc(entry.score.value) + (entry.score.stale ? '<div class="pkg">stale</div>' : "");
  }

  function reasonsCell(entry) {
    if (!entry.score || !entry.score.reasons || !entry.score.reasons.length) {
      return '<span class="absent">nothing outstanding</span>';
    }
    return (
      '<div class="reasons">' +
      entry.score.reasons
        .map(function (reason) {
          return '<span class="reason">' + esc(reason.label) + " <b>+" + esc(reason.contribution) + "</b></span>";
        })
        .join("") +
      "</div>"
    );
  }

  function ciSort(entry) {
    var ci = group(entry, "ci");
    if (!ci || !ci.latest_conclusion) return null;
    var rank = CONCLUSION_RANK[ci.latest_conclusion];
    return (rank === undefined ? 2 : rank) * 1000 - (ci.consecutive_failures || 0);
  }

  function ciCell(entry) {
    var ci = group(entry, "ci");
    if (!ci) return absent();
    if (!ci.latest_conclusion) return na("no workflow runs on the default branch");
    var failing = ci.consecutive_failures > 0;
    var html = '<span class="' + (failing ? "bad" : "ok") + '">' + esc(ci.latest_conclusion) + "</span>";
    if (failing) {
      html += '<div class="pkg">' + esc(ci.consecutive_failures) + " in a row since " + day(ci.red_since) + "</div>";
    } else if (ci.success_rate !== null && ci.success_rate !== undefined) {
      html += '<div class="pkg">' + Math.round(ci.success_rate * 100) + "% of " + ci.runs.length + " runs</div>";
    }
    return html;
  }

  function unreleasedCell(entry) {
    var release = group(entry, "release");
    if (!release) return absent();
    if (release.commits_since === null || release.commits_since === undefined) {
      return na("no release to count from");
    }
    var html = esc(release.commits_since) + (release.commits_since_truncated ? "+" : "");
    var types = release.commits_by_type || {};
    var facing = (types.feat || 0) + (types.fix || 0);
    if (facing) html += '<div class="pkg">' + facing + " user-facing</div>";
    return html;
  }

  function cranSort(entry) {
    var cran = group(entry, "cran");
    if (!cran || cran.state !== "available" || !cran.worst_status) return null;
    return CRAN_RANK[cran.worst_status] === undefined ? 4 : CRAN_RANK[cran.worst_status];
  }

  function cranCell(entry) {
    if (!isRPackage(entry)) return na("not an R package");
    var cran = group(entry, "cran");
    if (!cran) return absent();
    if (cran.state === "absent") return na("not on CRAN");
    if (cran.state !== "available") return '<span class="warn">unavailable</span>';
    var klass = cran.worst_status === "OK" ? "ok" : cran.worst_status === "NOTE" ? "warn" : "bad";
    var html = '<span class="' + klass + '">' + esc(cran.worst_status || "?") + "</span>";
    if (cran.version) html += '<div class="pkg">' + esc(cran.version) + "</div>";
    if (cran.deadline) html += '<div class="bad">deadline ' + esc(cran.deadline) + "</div>";
    return html;
  }

  function issuesCell(entry) {
    var tickets = group(entry, "tickets");
    if (!tickets) return absent();
    var html = num(tickets.open_issues);
    if (tickets.issues_no_maintainer_reply) html += '<div class="pkg">' + tickets.issues_no_maintainer_reply + " unanswered</div>";
    return html;
  }

  function prsCell(entry) {
    var tickets = group(entry, "tickets");
    if (!tickets) return absent();
    var html = num(tickets.open_pull_requests);
    if (tickets.pull_requests_awaiting_review) html += '<div class="pkg">' + tickets.pull_requests_awaiting_review + " awaiting review</div>";
    return html;
  }

  function activityCell(entry) {
    var activity = group(entry, "activity");
    if (!activity) return absent();
    var html = day(activity.last_commit_at);
    if (activity.dormant) html += '<div class="warn">dormant</div>';
    return html;
  }

  function templateCell(entry) {
    var template = group(entry, "template");
    if (!template) return absent();
    if (!template.collected) return na(template.reason || "not collected");
    var html = esc(template.outstanding);
    if (template.oldest_outstanding_at) html += '<div class="pkg">oldest ' + day(template.oldest_outstanding_at) + "</div>";
    return html;
  }

  function runStrip(ci) {
    if (!ci || !ci.runs || !ci.runs.length) return '<span class="absent">no runs retained</span>';
    return (
      '<span class="strip">' +
      ci.runs
        .map(function (run) {
          var klass = run.conclusion === "success" ? "pass" : run.conclusion === "failure" || run.conclusion === "timed_out" ? "fail" : "other";
          return '<span class="run ' + klass + '" title="' + esc((run.workflow || "run") + " " + (run.conclusion || "") + " " + day(run.created_at)) + '"></span>';
        })
        .join("") +
      "</span>"
    );
  }

  function detail(entry) {
    var identity = group(entry, "identity") || {};
    var links = identity.links || {};
    var ci = group(entry, "ci");
    var release = group(entry, "release") || {};
    var tickets = group(entry, "tickets") || {};
    var cran = group(entry, "cran");
    var template = group(entry, "template");
    var workspace = group(entry, "workspace");
    var rows = [];

    rows.push(["Description", identity.description ? esc(identity.description) : absent()]);
    rows.push([
      "Links",
      '<span class="links">' +
        (links.repository ? '<a href="' + esc(links.repository) + '">repository</a>' : "") +
        (links.actions ? '<a href="' + esc(links.actions) + '">actions</a>' : "") +
        (cran && cran.package_url && isRPackage(entry) ? '<a href="' + esc(cran.package_url) + '">CRAN</a>' : "") +
        (cran && cran.checks_url && isRPackage(entry) ? '<a href="' + esc(cran.checks_url) + '">CRAN checks</a>' : "") +
        (links.actions_sync ? '<a href="' + esc(links.actions_sync) + '">actions-sync</a>' : "") +
        "</span>"
    ]);
    if (ci) {
      rows.push(["CI history", runStrip(ci) + '<div class="pkg">window ' + day(ci.window_from) + " to " + day(ci.window_to) + "</div>"]);
      rows.push([
        "CI summary",
        (ci.success_rate === null || ci.success_rate === undefined ? absent() : Math.round(ci.success_rate * 100) + "% pass") +
          ", median " +
          (ci.median_duration_seconds === null || ci.median_duration_seconds === undefined ? absent() : Math.round(ci.median_duration_seconds / 60) + " min")
      ]);
    }
    rows.push([
      "Release",
      (release.latest_tag ? esc(release.latest_tag) + " on " + day(release.latest_published_at) : na("never released")) +
        (release.draft_release ? '<div class="pkg">draft: ' + esc(release.draft_release) + "</div>" : "")
    ]);
    if (release.commits_by_type) {
      rows.push([
        "Unreleased by type",
        Object.keys(release.commits_by_type)
          .map(function (type) { return esc(type) + " " + esc(release.commits_by_type[type]); })
          .join(", ") || absent()
      ]);
    }
    rows.push([
      "Versions",
      (identity.version ? "development " + esc(identity.version) : na("no DESCRIPTION")) +
        ", " +
        (release.cran_version ? "CRAN " + esc(release.cran_version) : na("not on CRAN")) +
        (release.ahead_of_cran ? ' <span class="warn">ahead</span>' : "")
    ]);
    if (cran && cran.state === "available" && cran.flavours && cran.flavours.length) {
      rows.push([
        "CRAN flavours",
        Object.keys(cran.status_counts || {})
          .map(function (status) { return esc(status) + " " + esc(cran.status_counts[status]); })
          .join(", ")
      ]);
    }
    rows.push([
      "Tickets",
      "issues " + num(tickets.open_issues) + " (" + num(tickets.issues_no_maintainer_reply) + " unanswered, " + num(tickets.issues_stale) + " stale), " +
        "pull requests " + num(tickets.open_pull_requests) + " (" + num(tickets.pull_requests_outside) + " outside, " + num(tickets.pull_requests_bot) + " bot, " +
        num(tickets.pull_requests_draft) + " draft, " + num(tickets.pull_requests_awaiting_review) + " awaiting review)"
    ]);
    if (template) {
      rows.push([
        "Template",
        template.collected
          ? esc(template.outstanding) + " outstanding" +
            (template.outstanding_commits && template.outstanding_commits.length
              ? '<div class="pkg">' + template.outstanding_commits.slice(0, 5).map(function (commit) { return esc(day(commit.authored_at) + " " + commit.subject); }).join("<br>") + "</div>"
              : "")
          : na(template.reason || "not collected")
      ]);
    }
    if (workspace) {
      rows.push([
        "Workspace (local only, never published)",
        workspace.collected === false
          ? na(workspace.reason || "not collected")
          : (workspace.dirty ? "dirty" : "clean") +
            ", " + num(workspace.unpushed) + " unpushed" +
            (workspace.operation_in_progress ? ", " + esc(workspace.operation_in_progress.join(", ")) + " in progress" : "")
      ]);
    }
    if (entry.error) rows.push(["Last failure", esc(entry.error)]);

    return (
      '<dl>' +
      rows.map(function (row) { return "<dt>" + row[0] + "</dt><dd>" + row[1] + "</dd>"; }).join("") +
      "</dl>"
    );
  }

  function compare(a, b, accessor, dir) {
    var left = accessor ? accessor(a) : null;
    var right = accessor ? accessor(b) : null;
    var leftMissing = left === null || left === undefined;
    var rightMissing = right === null || right === undefined;
    /* Absent values sort together and last, in either direction: a package with no CI is not the
     * best-behaved package in the portfolio, and a zero would say that it is. */
    if (leftMissing && rightMissing) return a.slug < b.slug ? -1 : 1;
    if (leftMissing) return 1;
    if (rightMissing) return -1;
    if (left === right) return a.slug < b.slug ? -1 : 1;
    var order = left < right ? -1 : 1;
    return dir === "desc" ? -order : order;
  }

  function visibleEntries() {
    var entries = Object.keys(state.snapshot.packages).map(function (slug) {
      var entry = state.snapshot.packages[slug];
      entry.slug = entry.slug || slug;
      return entry;
    });
    if (state.filter) {
      var needle = state.filter.toLowerCase();
      entries = entries.filter(function (entry) {
        var identity = entry.identity || {};
        return (
          entry.slug.toLowerCase().indexOf(needle) >= 0 ||
          (identity.package || "").toLowerCase().indexOf(needle) >= 0
        );
      });
    }
    var column = columns().filter(function (col) { return col.key === state.sort.key; })[0];
    if (column && column.sort) {
      entries.sort(function (a, b) { return compare(a, b, column.sort, state.sort.dir); });
    }
    return entries;
  }

  function renderTable() {
    var cols = columns();
    var entries = visibleEntries();
    var head =
      "<tr>" +
      cols
        .map(function (col) {
          var sorted = state.sort.key === col.key ? ' aria-sort="' + (state.sort.dir === "desc" ? "descending" : "ascending") + '"' : "";
          return '<th data-key="' + col.key + '"' + sorted + ">" + esc(col.label) + "</th>";
        })
        .join("") +
      "</tr>";
    var body = entries
      .map(function (entry) {
        var open = state.open[entry.slug];
        var row =
          '<tr class="row' + (entry.stale ? " stale" : "") + '" data-slug="' + esc(entry.slug) + '">' +
          cols
            .map(function (col) { return "<td" + (col.num ? ' class="num"' : "") + ">" + col.cell(entry) + "</td>"; })
            .join("") +
          "</tr>";
        var details =
          '<tr class="detail" data-detail="' + esc(entry.slug) + '"' + (open ? "" : ' hidden') + '>' +
          '<td colspan="' + cols.length + '">' + (open ? detail(entry) : "") + "</td></tr>";
        return row + details;
      })
      .join("");
    document.getElementById("table").innerHTML = "<thead>" + head + "</thead><tbody>" + body + "</tbody>";
    document.getElementById("shown").textContent = state.filter
      ? "Showing " + entries.length + " of " + Object.keys(state.snapshot.packages).length + " packages, filter applied"
      : entries.length + " packages";
  }

  function renderHeader() {
    var snapshot = state.snapshot;
    var portfolio = snapshot.portfolio || {};
    document.getElementById("meta").innerHTML =
      "Collected " + esc(snapshot.collected_at) + " &middot; schema " + esc(snapshot.schema_version) +
      (snapshot.requests && snapshot.requests.total ? " &middot; " + esc(snapshot.requests.total) + " requests" : "") +
      (snapshot.failures && snapshot.failures.length ? ' &middot; <span class="bad">' + snapshot.failures.length + " unreadable</span>" : "");
    var counters = [
      ["packages", portfolio.packages],
      ["CI failing", portfolio.ci_failing],
      ["CRAN not OK", portfolio.cran_not_ok],
      ["unreleased commits", portfolio.unreleased_commits],
      ["open issues", portfolio.open_issues],
      ["unanswered issues", portfolio.issues_no_maintainer_reply],
      ["open PRs", portfolio.open_pull_requests],
      ["dormant", portfolio.dormant],
      ["stale rows", portfolio.stale]
    ];
    document.getElementById("counters").innerHTML = counters
      .map(function (pair) {
        return '<div class="counter"><b>' + num(pair[1]) + "</b><span>" + esc(pair[0]) + "</span></div>";
      })
      .join("");

    var notes = [];
    var clear = Object.keys(snapshot.packages).every(function (slug) {
      var score = snapshot.packages[slug].score;
      return !score || !score.value;
    });
    if (clear) {
      notes.push('<div class="banner">The portfolio is clear: nothing scored above zero in this reading.</div>');
    }
    var flags = snapshot.groups_collected || {};
    if (flags.template !== true) {
      notes.push(
        '<div class="banner problem">Template position was not collected: this reading was taken on a machine without the mirrors. ' +
          "It does not mean every package is in step.</div>"
      );
    }
    document.getElementById("notes").innerHTML = notes.join("");
  }

  function sparkline(values) {
    if (values.length < 2) return "";
    var max = Math.max.apply(null, values) || 1;
    var points = values
      .map(function (value, index) {
        return (index / (values.length - 1)) * 120 + "," + (30 - (value / max) * 28);
      })
      .join(" ");
    return '<svg width="120" height="30" role="img"><polyline fill="none" stroke="currentColor" stroke-width="1.5" points="' + points + '"></polyline></svg>';
  }

  function renderTrend(series) {
    if (!series || series.length < 2) return;
    var keys = ["ci_failing", "unreleased_commits", "open_issues", "issues_no_maintainer_reply", "attention_total"];
    document.getElementById("trend").innerHTML =
      "<h2>Trend over " + series.length + " published readings</h2><div class=\"trend\">" +
      keys
        .map(function (key) {
          var values = series.map(function (point) { return point[key] || 0; });
          return '<div class="spark">' + sparkline(values) + "<span>" + esc(key.replace(/_/g, " ")) + " &middot; now " + esc(values[values.length - 1]) + "</span></div>";
        })
        .join("") +
      "</div>";
  }

  function loadTrend() {
    /* The history is a published file beside the snapshot, so a page opened from disk simply has
     * none: the trend is omitted and the reading itself still renders in full. */
    if (!window.fetch) return;
    fetch("history.jsonl", { cache: "no-store" })
      .then(function (response) { return response.ok ? response.text() : Promise.reject(); })
      .then(function (text) {
        var series = text
          .split("\n")
          .filter(function (line) { return line.trim(); })
          .map(function (line) { try { return JSON.parse(line); } catch (error) { return null; } })
          .filter(Boolean);
        renderTrend(series);
      })
      .catch(function () {});
  }

  function attach() {
    document.getElementById("table").addEventListener("click", function (event) {
      var header = event.target.closest("th");
      if (header) {
        var key = header.getAttribute("data-key");
        state.sort = state.sort.key === key ? { key: key, dir: state.sort.dir === "desc" ? "asc" : "desc" } : { key: key, dir: "desc" };
        renderTable();
        return;
      }
      var row = event.target.closest("tr.row");
      if (row && !event.target.closest("a")) {
        var slug = row.getAttribute("data-slug");
        state.open[slug] = !state.open[slug];
        renderTable();
      }
    });
    document.getElementById("filter").addEventListener("input", function (event) {
      state.filter = event.target.value.trim();
      renderTable();
    });
  }

  function message(text) {
    document.getElementById("notes").innerHTML = '<div class="banner problem">' + esc(text) + "</div>";
  }

  function render(snapshot) {
    state.snapshot = snapshot;
    document.getElementById("main").hidden = false;
    renderHeader();
    renderTable();
    attach();
    loadTrend();
  }

  function start() {
    var embedded = document.getElementById("snapshot-data");
    if (embedded && embedded.textContent.trim()) {
      try {
        render(JSON.parse(embedded.textContent));
        return;
      } catch (error) {
        message("The snapshot embedded in this page could not be parsed: " + error.message);
        return;
      }
    }
    if (!window.fetch) {
      message("No snapshot is embedded in this page and this browser cannot fetch one.");
      return;
    }
    fetch("metrics.json", { cache: "no-store" })
      .then(function (response) { return response.ok ? response.json() : Promise.reject(new Error("HTTP " + response.status)); })
      .then(render)
      .catch(function (error) {
        message(
          "No snapshot could be loaded: metrics.json was not reachable (" + error.message + "). " +
            "Run `mise run metrics` and `mise run dashboard` to produce a page with the reading embedded in it."
        );
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
