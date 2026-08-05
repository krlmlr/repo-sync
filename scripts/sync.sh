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
# The order matters. The bare mirror is refreshed first,
# so the template refs the other mirrors then fetch are the ones GitHub has,
# and not the ones it had at the last clone.
#
# This is the gentle counterpart to `clone`:
# `clone` resets each mirror hard onto origin/HEAD,
# while `sync` rebases, and so keeps local work that has not been pushed yet.
set -uo pipefail

# shellcheck source-path=SCRIPTDIR
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

load_inventory

bare_dir="$(template_bare_dir)"
bare_present=false

if [[ -d "$bare_dir" ]]; then
    if [[ "$(git -C "$bare_dir" rev-parse --is-bare-repository 2>/dev/null)" != "true" ]]; then
        fail "$template_slug.git" "$bare_dir is not a bare repository"
    else
        bare_present=true
        echo "==> fetch $template_slug.git (bare)"
        if ! git_authenticated -C "$bare_dir" fetch --prune; then
            # The refs are stale rather than gone,
            # so the mirrors can still fetch from it below.
            fail "$template_slug.git" "fetch $template_slug.git"
        fi
    fi
else
    fail "$template_slug.git" "$bare_dir is missing -- run \`mise run clone\` first"
fi

pull_rebase() {
    local slug="$1"
    local dest="$2"

    echo "==> pull --rebase $slug"
    if ! git_authenticated -C "$dest" pull --rebase; then
        fail "$slug" "pull --rebase $slug"
        return 1
    fi
}

fetch_template() {
    local slug="$1"
    local dest="$2"

    [[ "$slug" == "$template_slug" ]] && return 0
    $bare_present || return 0

    if ! git -C "$dest" remote get-url template >/dev/null 2>&1; then
        fail "$slug" "$slug has no \`template\` remote -- run \`mise run clone\` first"
        return 1
    fi

    # Plain `git`: the `template` URL is a relative path to the bare mirror,
    # and a local remote has no credential to ask for.
    echo "==> fetch template $slug"
    if ! git -C "$dest" fetch --prune template; then
        fail "$slug" "fetch template $slug"
        return 1
    fi
}

while IFS= read -r slug; do
    [[ -z "$slug" ]] && continue

    dest="$MIRRORS_DIR/$slug"
    if [[ ! -d "$dest/.git" ]]; then
        # Cloning is `clone`'s job; sync works on the mirrors that exist.
        echo "==> skip $slug (not cloned)"
        continue
    fi

    # Both steps run even when the first one fails:
    # a mirror whose rebase stopped on a conflict
    # still wants the template refs it is going to be reconciled against.
    pull_rebase "$slug" "$dest"
    fetch_template "$slug" "$dest"
done <<< "$ordered_slugs"

report_failures
