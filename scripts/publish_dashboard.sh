#!/usr/bin/env bash
# Publish the current snapshot and page to the deploy branch.
#
# `main` stays free of generated data. The deploy branch already exists to hold generated output --
# and the page can fetch its own history from it as a relative URL, with no API and no token --
# so the snapshots, the history series and the page all live there together.
#
# The workspace group never reaches it: `render_dashboard.py --publish` strips it by name while
# writing, so publication cannot happen without the stripping having happened.
#
# A worktree of this repository rather than a fresh clone, because the credentials that can push
# are the ones this checkout already has: the `gh` login or SSH key locally, and the header
# `actions/checkout` configured in CI. A clone into a temporary directory would have neither, and
# the alternative -- a URL with a token in it -- is a token one stray log line away from being
# published. Nothing here prints a remote URL for the same reason.
#
# This does not source `lib.sh`. That file is the inventory and the fan-out -- one network-bound
# git operation per repository, collected and reported at the end -- and publication is one commit
# to one branch. What it borrows is the discipline: say what failed, and exit non-zero.
#
# Environment, all optional, and all there so the whole thing can be exercised against a throwaway
# repository instead of against the real one:
#   REPO_SYNC_SNAPSHOT         the snapshot to publish        (default reports/metrics.json)
#   REPO_SYNC_PUBLISH_WORKDIR  the repository that owns the branch and its remote (default here)
#   REPO_SYNC_PUBLISH_REMOTE   remote name in that repository (default origin)
#   REPO_SYNC_PUBLISH_BRANCH   branch to publish to           (default gh-pages)
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SNAPSHOT="${REPO_SYNC_SNAPSHOT:-$REPO_ROOT/reports/metrics.json}"
WORKDIR="${REPO_SYNC_PUBLISH_WORKDIR:-$REPO_ROOT}"
REMOTE="${REPO_SYNC_PUBLISH_REMOTE:-origin}"
BRANCH="${REPO_SYNC_PUBLISH_BRANCH:-gh-pages}"

worktree=""
temp_branch=""

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

cleanup() {
    [[ -n "$worktree" ]] && git -C "$WORKDIR" worktree remove --force "$worktree" >/dev/null 2>&1
    # The orphan branch exists only to have something to commit onto before the first push.
    [[ -n "$temp_branch" ]] && git -C "$WORKDIR" branch -D "$temp_branch" >/dev/null 2>&1
    rm -rf "$worktree"
}

[[ -f "$SNAPSHOT" ]] || fail "no snapshot at $SNAPSHOT -- run \`mise run metrics\` first"
git -C "$WORKDIR" rev-parse --git-dir >/dev/null 2>&1 || fail "$WORKDIR is not a git repository"
git -C "$WORKDIR" remote get-url "$REMOTE" >/dev/null 2>&1 || fail "$WORKDIR has no remote named $REMOTE"

worktree="$(mktemp -d "${TMPDIR:-/tmp}/repo-sync-publish.XXXXXX")"
trap cleanup EXIT
rmdir "$worktree"  # `git worktree add` wants to create the directory itself

# Depth one: the branch's history is a log of readings, and publishing needs only the last one.
if git -C "$WORKDIR" fetch --quiet --depth 1 "$REMOTE" "$BRANCH" 2>/dev/null; then
    git -C "$WORKDIR" worktree add --quiet --detach "$worktree" FETCH_HEAD ||
        fail "unable to check out $BRANCH"
else
    # First run. The branch is established here rather than by hand, so a fresh checkout of this
    # repository can publish without anyone having prepared anything.
    echo "==> $BRANCH does not exist on $REMOTE yet, creating it"
    temp_branch="repo-sync-publish-$$"
    git -C "$WORKDIR" worktree add --quiet --orphan -b "$temp_branch" "$worktree" ||
        fail "unable to create a worktree for $BRANCH"
fi

if ! python3 "$REPO_ROOT/scripts/render_dashboard.py" --snapshot "$SNAPSHOT" --out "$worktree" --publish; then
    fail "unable to render the published page from $SNAPSHOT"
fi

git -C "$worktree" add -A || fail "unable to stage the published files"
if git -C "$worktree" diff --cached --quiet; then
    # The publication history records changes rather than runs: a reading identical to the one
    # already published is not a new fact about the portfolio.
    echo "==> nothing to publish: the reading is unchanged"
    exit 0
fi

collected_at="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("collected_at", "unknown"))' "$SNAPSHOT")"
git -C "$worktree" \
    -c user.name="${GIT_AUTHOR_NAME:-repo-sync}" \
    -c user.email="${GIT_AUTHOR_EMAIL:-repo-sync@users.noreply.github.com}" \
    commit --quiet -m "chore(dashboard): publish the reading of $collected_at" ||
    fail "unable to commit the published files"

git -C "$worktree" push --quiet "$REMOTE" "HEAD:refs/heads/$BRANCH" || fail "unable to push $BRANCH to $REMOTE"
echo "==> published the reading of $collected_at to $BRANCH"
