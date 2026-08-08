#!/usr/bin/env bash
# Bring every mirror back in step, with its own upstream and with the template.
#
# Why this is a task of its own rather than a sweep with `s`:
# `s`/`h` run a git command in every repository below the current directory,
# and they find those repositories by their `.git` entry.
# A bare repository has none -- its HEAD, config, objects and refs
# sit at the top of the directory instead --
# so the template's bare mirror is invisible to that sweep
# and would be the one thing left behind by it.
#
# The order matters. The bare mirror is refreshed first, alone,
# so the template refs the other mirrors then fetch are the ones GitHub has,
# and not the ones it had at the last clone.
# Only once it is current are the mirrors let loose on it, several at a time:
# they read from it and from their own upstreams, and never from each other,
# so nothing among them has to wait for anything else.
#
# `parallel` runs them by re-invoking this script as `sync.sh <slug>`,
# which is also how to reproduce one mirror's failure on its own.
#
# This is the gentle counterpart to `clone`:
# `clone` resets each mirror hard onto origin/HEAD,
# while `sync` rebases, and so keeps local work that has not been pushed yet.
set -uo pipefail

# shellcheck source-path=SCRIPTDIR
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

pull_rebase() {
    local slug="$1"
    local dest="$2"

    echo "==> pull --rebase $slug"
    if ! git -C "$dest" pull --rebase; then
        fail "$slug" "pull --rebase $slug"
        return 1
    fi
}

fetch_template() {
    local slug="$1"
    local dest="$2"

    [[ "$slug" == "$template_slug" ]] && return 0
    # A bare mirror that is missing, or that is not bare, has already been
    # reported once by the parent before the fan-out. Repeating it here, once
    # per mirror, would bury that one fact under forty-seven copies of itself.
    template_bare_usable || return 0

    if ! git -C "$dest" remote get-url template >/dev/null 2>&1; then
        fail "$slug" "$slug has no \`template\` remote -- run \`mise run clone\` first"
        return 1
    fi

    echo "==> fetch template $slug"
    if ! git -C "$dest" fetch --prune template; then
        fail "$slug" "fetch template $slug"
        return 1
    fi
}

# One mirror, in a child process.
run_one() {
    local slug="$1"
    local dest="$MIRRORS_DIR/$slug"
    local status=0

    if [[ ! -d "$dest/.git" ]]; then
        # Cloning is `clone`'s job; sync works on the mirrors that exist.
        echo "==> skip $slug (not cloned)"
        return 0
    fi

    # Both steps run even when the first one fails:
    # a mirror whose rebase stopped on a conflict
    # still wants the template refs it is going to be reconciled against.
    pull_rebase "$slug" "$dest" || status=1
    fetch_template "$slug" "$dest" || status=1
    return $status
}

if [[ $# -gt 0 ]]; then
    if [[ $# -ne 1 ]]; then
        echo "usage: sync.sh [<org/repo>]" >&2
        exit 2
    fi
    load_template_slug
    run_one "$1"
    exit
fi

require_parallel
load_inventory

bare_dir="$(template_bare_dir)"
if template_bare_usable; then
    echo "==> fetch $template_slug.git (bare)"
    if ! git -C "$bare_dir" fetch --prune; then
        # The refs are stale rather than gone,
        # so the mirrors can still fetch from it below.
        fail "$template_slug.git" "fetch $template_slug.git"
    fi
elif [[ -d "$bare_dir" ]]; then
    fail "$template_slug.git" "$bare_dir is not a bare repository"
else
    fail "$template_slug.git" "$bare_dir is missing -- run \`mise run clone\` first"
fi

# Every mirror, the template's checkout among them: it is a mirror like any
# other here, it just has no `template` remote of its own to fetch.
printf '%s\n' "$template_slug" "$other_slugs" | run_parallel "$SCRIPTS_DIR/sync.sh" {}

report_failures
