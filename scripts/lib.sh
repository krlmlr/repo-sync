# shellcheck shell=bash
#
# Shared by scripts/clone.sh and scripts/sync.sh.
# Deliberately not executable: it is sourced, never run --
# which is also why it has a shell directive and no shebang.
#
# The template designation lives here rather than in either caller,
# so both tools read the inventory the same way
# and reject the same malformed one.
#
# So does the fan-out. Both tools do the same shape of work --
# one independent, network-bound git operation per repository --
# and both do it by being re-invoked once per repository,
# so the machinery that spawns and collects those children
# has one implementation rather than two that can drift.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC2034  # the fan-out target, read by the script that sourced this one
SCRIPTS_DIR="$REPO_ROOT/scripts"
REPOS_YML="$REPO_ROOT/repos.yml"
MIRRORS_DIR="$REPO_ROOT/mirrors"

# How many repositories are worked on at once.
#
# The work is network-bound, not CPU-bound: a clone spends most of its life
# waiting on GitHub rather than on this machine, so the useful degree of
# parallelism is above the core count and not equal to it.
# `REPO_SYNC_JOBS=1` puts the whole run back in single file,
# which is the thing to reach for when reading a confusing failure.
JOBS="${REPO_SYNC_JOBS:-8}"

# Failures are collected in a file rather than in a shell array.
#
# The per-repository work happens in child processes,
# and an array one of them appends to dies with it:
# the parent that has to report at the end would see an empty list
# and exit zero on a run where half the inventory failed.
#
# Each `fail` appends one short line to a file opened with O_APPEND.
# Writes that small are not interleaved, so the children share it
# without a lock and without a line ever landing inside another.
if [[ -z "${REPO_SYNC_FAILURES:-}" ]]; then
    if ! REPO_SYNC_FAILURES="$(mktemp "${TMPDIR:-/tmp}/repo-sync-failures.XXXXXX")"; then
        echo "FAIL: unable to create the failure log" >&2
        exit 1
    fi
    export REPO_SYNC_FAILURES
    # Only the process that created the file removes it.
    # A child inherits the path and must leave the file behind,
    # since the parent has not read it yet.
    trap 'rm -f "$REPO_SYNC_FAILURES"' EXIT
fi

# Read repos.yml into `template_slug` and `other_slugs`.
#
# The template is held apart from the rest rather than sorted to the front of
# one list, because the two are no longer walked in one pass: its mirrors are
# made first, on their own, and the rest of the inventory follows once they are
# on disk. That is the same guarantee the ordering used to carry, stated as a
# barrier between two batches instead of as a sort order within one.
load_inventory() {
    local parsed
    if ! parsed=$(python3 -c "
import yaml, sys
with open(sys.argv[1]) as f:
    data = yaml.safe_load(f)
flagged = [(e['org'], e['repo']) for e in data['repos'] if e.get('template') is True]
if len(flagged) == 0:
    print('FAIL: no entry in repos.yml has template: true', file=sys.stderr)
    sys.exit(2)
if len(flagged) > 1:
    print('FAIL: multiple entries in repos.yml have template: true: '
          + ', '.join(f'{o}/{r}' for o, r in flagged), file=sys.stderr)
    sys.exit(2)
template_slug = f'{flagged[0][0]}/{flagged[0][1]}'
print(template_slug)
for e in data['repos']:
    slug = f\"{e['org']}/{e['repo']}\"
    if slug != template_slug:
        print(slug)
" "$REPOS_YML"); then
        echo "FAIL: unable to load repository inventory from $REPOS_YML" >&2
        exit 1
    fi

    template_slug=$(printf '%s\n' "$parsed" | head -n 1)
    # shellcheck disable=SC2034  # read by the script that sourced this one
    other_slugs=$(printf '%s\n' "$parsed" | tail -n +2)

    # Inherited by every child, so repos.yml is parsed once for the run
    # rather than once per repository.
    export REPO_SYNC_TEMPLATE_SLUG="$template_slug"
}

# The designation, and nothing else, for a child process.
#
# It comes from the parent that spawned it; a child run by hand, with nothing
# to inherit, falls back to reading the inventory itself, so the child entry
# points work on their own and not only inside a batch.
load_template_slug() {
    if [[ -n "${REPO_SYNC_TEMPLATE_SLUG:-}" ]]; then
        template_slug="$REPO_SYNC_TEMPLATE_SLUG"
    else
        load_inventory
    fi
}

# The template is mirrored twice.
# The checkout is the one to read, edit and reconcile against;
# the bare mirror next to it is the one every other mirror fetches from,
# so no mirror ever fetches from a repository that has a branch checked out.
template_checkout_dir() {
    printf '%s\n' "$MIRRORS_DIR/$template_slug"
}

template_bare_dir() {
    printf '%s\n' "$MIRRORS_DIR/$template_slug.git"
}

# Whether the bare mirror is something the mirrors can fetch from.
#
# Existing is not enough: a directory at that path that is not a bare
# repository is a mistake to report, not a thing to fetch into. A *failed
# fetch*, on the other hand, leaves it perfectly usable -- the refs it already
# holds are what the mirrors read from it -- which is why this asks about the
# repository on disk and not about how the run has gone so far.
#
# Each process answers it from disk rather than being told, so a child reaches
# the same verdict as the parent that spawned it, and so a child run by hand
# reaches it too.
template_bare_usable() {
    local dir
    dir="$(template_bare_dir)"
    [[ -d "$dir" ]] || return 1
    [[ "$(git -C "$dir" rev-parse --is-bare-repository 2>/dev/null)" == "true" ]]
}

# The URL of the `template` remote, relative to the mirror that carries it.
# Git resolves a relative remote URL from the top of the working tree,
# so this holds wherever mirrors/ sits and from whichever subdirectory it is run.
template_remote_url() {
    printf '%s\n' "../../$template_slug.git"
}

# The SSH clone URL for an inventory slug.
#
# Built from the inventory rather than resolved through the GitHub API.
# `gh repo clone` spends a GraphQL request per repository to do that resolution,
# out of a budget shared with every other `gh` command the same token has run,
# and a clone of the whole inventory is exactly the thing that exhausts it.
# `repos.yml` already knows what each repository is called.
#
# SSH rather than HTTPS: the key is in the agent and the account,
# so there is no credential for the scripts to obtain, hold or hand over --
# no helper to configure, and nothing token-shaped to leak into a remote URL.
github_url() {
    printf 'git@github.com:%s.git\n' "$1"
}

# GNU parallel, and specifically that one.
#
# moreutils ships a different program under the same name which understands
# none of the options used here. Saying so once, before any work starts, beats
# having every job in the batch fail with the same usage error.
require_parallel() {
    local version
    if ! version="$(parallel --version 2>/dev/null | head -n 1)"; then
        echo "FAIL: GNU parallel is not installed -- \`apt install parallel\` or \`brew install parallel\`" >&2
        exit 1
    fi
    if [[ "$version" != "GNU parallel"* ]]; then
        echo "FAIL: the \`parallel\` on PATH is \"$version\", not GNU parallel" >&2
        exit 1
    fi
}

# Run the given command once per line of stdin, `$JOBS` lines at a time.
#
# Blank lines are dropped rather than run: an inventory of nothing but the
# template leaves an empty list behind, and an empty argument is not a repo.
#
# `--will-cite` suppresses the citation notice, which is a one-time interactive
# prompt and has no business appearing in the middle of a mirror run.
# `--halt never` keeps the batch going when a job fails, which is the discipline
# `fail` and `report_failures` already implement: one unreachable repository
# must not end the run.
#
# The output is grouped -- parallel's default, and the reason this is GNU
# parallel rather than `xargs -P`. Each job's stdout and stderr are held and
# printed together when it finishes, so a repository's lines arrive as one
# block; `xargs -P` would shuffle eight repositories' lines into each other and
# leave every failure to be reassembled by eye.
run_parallel() {
    grep -v '^[[:space:]]*$' | parallel --will-cite --halt never --jobs "$JOBS" "$@"
}

# Record a failure and carry on: one unreachable repo must not end the batch.
fail() {
    local slug="$1"
    local message="$2"
    echo "FAIL: $message" >&2
    printf '%s\n' "$slug" >> "$REPO_SYNC_FAILURES"
}

report_failures() {
    local failures=()
    local slug
    # Sorted, because the order the failures were recorded in is the order the
    # jobs happened to finish in, and a report that reshuffles itself between
    # two identical runs is a report that cannot be diffed.
    while IFS= read -r slug; do
        failures+=("$slug")
    done < <(sort "$REPO_SYNC_FAILURES")

    if [[ ${#failures[@]} -gt 0 ]]; then
        echo ""
        printf 'FAILED (%d): %s\n' "${#failures[@]}" "${failures[*]}" >&2
        exit 1
    fi
}
