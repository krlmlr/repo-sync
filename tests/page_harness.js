/* The page's JavaScript, run against the fixture snapshots outside a browser.
 *
 * The page is a hundred lines of vanilla JavaScript over three or four DOM calls, so the smallest
 * honest way to test it is to provide those calls and run it. What is checked here is what the
 * page promises: the default ranking, the reasons beside it, absent values sorting together, the
 * filter restating the counts, stale and not-applicable reading differently, a group the snapshot
 * does not carry being omitted rather than rendered empty, and both ways of finding the data.
 *
 * Run by `tests/test_page.py`, which skips when node is not installed.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = process.argv[2] || path.join(__dirname, "..");
const source = fs.readFileSync(path.join(root, "scripts", "portfolio", "assets", "page.js"), "utf8");
const failures = [];

function check(name, condition, detail) {
  if (!condition) failures.push(name + (detail ? ": " + detail : ""));
}

function element(id) {
  return {
    id: id,
    innerHTML: "",
    textContent: "",
    hidden: false,
    value: "",
    listeners: {},
    addEventListener: function (type, handler) {
      (this.listeners[type] = this.listeners[type] || []).push(handler);
    }
  };
}

function runPage(options) {
  const elements = {};
  const fetched = [];
  const get = function (id) {
    if (!elements[id]) elements[id] = element(id);
    return elements[id];
  };
  if (options.embedded !== undefined) get("snapshot-data").textContent = options.embedded;

  const context = {
    document: {
      readyState: "complete",
      getElementById: get,
      addEventListener: function () {}
    },
    console: console,
    setTimeout: setTimeout,
    Promise: Promise,
    JSON: JSON,
    Math: Math,
    Object: Object,
    fetch: function (url) {
      fetched.push(url);
      const answer = options.responses && Object.prototype.hasOwnProperty.call(options.responses, url)
        ? options.responses[url]
        : null;
      if (answer === null) return Promise.resolve({ ok: false, status: 404 });
      return Promise.resolve({
        ok: true,
        status: 200,
        json: function () { return Promise.resolve(JSON.parse(answer)); },
        text: function () { return Promise.resolve(answer); }
      });
    }
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(source, context);
  return { elements: elements, fetched: fetched, get: get };
}

function fixture(name) {
  return fs.readFileSync(path.join(root, "tests", "fixtures", name), "utf8");
}

function rowsOf(page) {
  const html = page.elements.table.innerHTML;
  const matches = html.match(/data-slug="[^"]+"/g) || [];
  return matches.map(function (match) { return match.slice(11, -1); });
}

function clickHeader(page, key) {
  page.elements.table.listeners.click[0]({
    target: {
      closest: function (selector) {
        if (selector === "th") return { getAttribute: function () { return key; } };
        return null;
      }
    }
  });
}

function clickRow(page, slug) {
  page.elements.table.listeners.click[0]({
    target: {
      closest: function (selector) {
        if (selector === "tr.row") return { getAttribute: function () { return slug; } };
        return null;
      }
    }
  });
}

function typeFilter(page, text) {
  page.elements.filter.listeners.input[0]({ target: { value: text } });
}

/* 8.2 -- an embedded snapshot is used, and nothing is fetched for the reading itself. */
const embedded = runPage({ embedded: fixture("snapshot.json") });
check("embedded render fills the table", rowsOf(embedded).length === 7);
check("embedded render fetches no snapshot", embedded.fetched.indexOf("metrics.json") === -1, embedded.fetched.join(","));

/* 8.2 -- with no embedded snapshot the neighbouring document is fetched, and renders the same. */
const fetchedPage = runPage({ responses: { "metrics.json": fixture("snapshot.json") } });
setTimeout(function () {
  check("fetched render asks for metrics.json", fetchedPage.fetched.indexOf("metrics.json") >= 0);
  check(
    "fetched render matches the embedded one",
    fetchedPage.elements.table.innerHTML === embedded.elements.table.innerHTML
  );

  /* 8.3 -- neither source available. */
  const empty = runPage({});
  setTimeout(function () {
    check("with no snapshot the page says so", /No snapshot could be loaded/.test(empty.elements.notes.innerHTML));

    /* 8.4 -- ranked by attention, with the reasons visible in the row. */
    const order = rowsOf(embedded);
    check("the highest scoring package is first", order[0] === "r-dbi/RKazam", order.join(" > "));
    check(
      "its reasons are in the row itself",
      /CI red for \d+ days/.test(embedded.elements.table.innerHTML) && /CRAN deadline/.test(embedded.elements.table.innerHTML)
    );

    /* 8.5 -- an all-zero reading is stated rather than ranked. */
    const clear = runPage({ embedded: fixture("snapshot_clear.json") });
    check("a clear portfolio says so", /portfolio is clear/.test(clear.elements.notes.innerHTML));

    /* 8.6 -- sorting, with absent values together, and a filter that restates the counts. */
    /* `ghost/never` was never read and `krlmlr/notapackage` has never been released: both are
     * absent rather than zero, so both belong at the end whichever way the column is sorted. */
    const absent = ["ghost/never", "krlmlr/notapackage"];
    clickHeader(embedded, "unreleased");
    const descending = rowsOf(embedded);
    check("sorting puts absent values last", descending.slice(-2).join() === absent.join(), descending.join(" > "));
    clickHeader(embedded, "unreleased");
    const ascending = rowsOf(embedded);
    check("absent values stay last when the direction flips", ascending.slice(-2).join() === absent.join(), ascending.join(" > "));
    check("and the measured values reordered", descending.slice(0, 5).join() !== ascending.slice(0, 5).join());

    typeFilter(embedded, "tib");
    check("filtering narrows the table", rowsOf(embedded).length === 1, rowsOf(embedded).join(","));
    check(
      "filtering restates the counts",
      /Showing 1 of 7 packages, filter applied/.test(embedded.elements.shown.textContent),
      embedded.elements.shown.textContent
    );
    typeFilter(embedded, "");
    check("clearing the filter restores the table", rowsOf(embedded).length === 7);

    /* 8.7 -- measured, not applicable, and stale read differently. */
    const html = embedded.elements.table.innerHTML;
    check("a stale row is marked", /class="row stale"/.test(html));
    check("a stale row shows when it was observed", /stale: last observed \d{4}-\d{2}-\d{2}/.test(html));
    check("a package that is not an R package reads as not applicable", /not an R package/.test(html) && /n\/a/.test(html));

    /* 8.8 -- a group the snapshot does not carry is omitted, with a note. */
    check("no template column without the mirrors", html.indexOf('data-key="template"') === -1);
    check("and the omission is stated", /Template position was not collected/.test(embedded.elements.notes.innerHTML));
    const mirrored = runPage({ embedded: fixture("snapshot_mirrors.json") });
    check("the template column appears when the group is there", mirrored.elements.table.innerHTML.indexOf('data-key="template"') >= 0);
    check("and no note claims otherwise", !/not collected/.test(mirrored.elements.notes.innerHTML));

    /* 8.9 -- the CI strip renders the runs that exist rather than padding. */
    clickRow(embedded, "tidyverse/tibble");
    const detail = embedded.elements.table.innerHTML;
    const cells = (detail.match(/class="run /g) || []).length;
    check("the strip has one cell per retained run", cells === 5, String(cells));

    /* 8.10 -- every link a row offers is in the detail, and comes from the snapshot. */
    check("the row links to the repository", detail.indexOf("https://github.com/tidyverse/tibble") >= 0);
    check("and to its actions", detail.indexOf("/actions?query=branch%3Amain") >= 0);
    check("and to CRAN", detail.indexOf("https://cran.r-project.org/package=tibble") >= 0);
    check("and to actions-sync", detail.indexOf("https://krlmlr.github.io/actions-sync/") >= 0);

    /* 9.5 -- the trend renders from the published series, and is omitted when there is none. */
    const withHistory = runPage({
      embedded: fixture("snapshot.json"),
      responses: {
        "history.jsonl":
          '{"collected_at":"2026-08-30T12:00:00Z","ci_failing":3,"open_issues":40,"attention_total":70}\n' +
          '{"collected_at":"2026-09-01T12:00:00Z","ci_failing":1,"open_issues":7,"attention_total":58}\n'
      }
    });
    setTimeout(function () {
      check("the trend renders from the series", /Trend over 2 published readings/.test(withHistory.elements.trend.innerHTML));
      check("the reading itself still rendered", rowsOf(withHistory).length === 7);
      check(
        "no series means no trend",
        embedded.elements.trend === undefined || embedded.elements.trend.innerHTML === ""
      );

      if (failures.length) {
        console.error(failures.join("\n"));
        process.exit(1);
      }
      console.log("page checks passed");
    }, 10);
  }, 10);
}, 10);
