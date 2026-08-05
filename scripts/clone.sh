#!/usr/bin/env bash
# Mirror every repository in repos.yml under mirrors/<org>/<repo>/.
#
# The template is mirrored twice: as a checkout like every other repo,
# and as a bare clone at mirrors/<org>/<repo>.git beside it.
# The bare clone is what the `template` remotes point at,
# because a repository with a branch checked out
# is the wrong thing to have on the other end of a fetch or a push.
set -uo pipefail

# shellcheck source-path=SCRIPTDIR
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

load_inventory

clone_or_update() {
    local slug="$1"
    local org="${slug%%/*}"
    local dest="$MIRRORS_DIR/$slug"

    if [[ -d "$dest/.git" ]]; then
        echo "==> update $slug"
        # An `origin` left from an HTTPS clone is rewritten to the SSH URL --
        # the same normalisation the `template` remote gets below.
        # Which transport a mirror speaks should follow from the inventory,
        # not from the day the mirror happened to be created.
        if ! git -C "$dest" remote set-url origin "$(github_url "$slug")"; then
            fail "$slug" "set-url origin $slug"
            return 1
        fi
        if ! git -C "$dest" fetch --prune; then
            fail "$slug" "fetch $slug"
            return 1
        fi
        if ! git -C "$dest" reset --hard origin/HEAD; then
            fail "$slug" "reset $slug"
            return 1
        fi
    else
        echo "==> clone $slug"
        mkdir -p "$MIRRORS_DIR/$org"
        if ! git clone "$(github_url "$slug")" "$dest"; then
            fail "$slug" "clone $slug"
            return 1
        fi
    fi
}

# The template's second mirror.
# `--mirror` rather than `--bare`: it carries the refspec
# that lets a later `git fetch` refresh every ref,
# which a plain bare clone has no configured way to do.
clone_or_update_bare() {
    local slug="$1"
    local org="${slug%%/*}"
    local dest="$MIRRORS_DIR/$slug.git"

    if [[ -d "$dest" ]]; then
        if [[ "$(git -C "$dest" rev-parse --is-bare-repository 2>/dev/null)" != "true" ]]; then
            fail "$slug.git" "$dest exists but is not a bare repository"
            return 1
        fi
        echo "==> update $slug.git (bare)"
        if ! git -C "$dest" remote set-url origin "$(github_url "$slug")"; then
            fail "$slug.git" "set-url origin $slug.git"
            return 1
        fi
        if ! git -C "$dest" fetch --prune; then
            fail "$slug.git" "fetch $slug.git"
            return 1
        fi
    else
        echo "==> clone $slug.git (bare)"
        mkdir -p "$MIRRORS_DIR/$org"
        if ! git clone --mirror "$(github_url "$slug")" "$dest"; then
            fail "$slug.git" "clone $slug.git"
            return 1
        fi
    fi
}

configure_template_remote() {
    local slug="$1"
    [[ "$slug" == "$template_slug" ]] && return 0
    local dest="$MIRRORS_DIR/$slug"
    local url
    url="$(template_remote_url)"
    if git -C "$dest" remote get-url template >/dev/null 2>&1; then
        if ! git -C "$dest" remote set-url template "$url"; then
            fail "$slug" "set-url template $slug"
            return 1
        fi
    else
        if ! git -C "$dest" remote add template "$url"; then
            fail "$slug" "add template $slug"
            return 1
        fi
    fi
}

while IFS= read -r slug; do
    [[ -z "$slug" ]] && continue

    if [[ "$slug" == "$template_slug" ]]; then
        # Both mirrors of the template, and both before anything points at them.
        # They are independent clones of the same upstream,
        # so one failing says nothing about the other: attempt both.
        clone_or_update "$slug"
        clone_or_update_bare "$slug"
        continue
    fi

    if clone_or_update "$slug"; then
        configure_template_remote "$slug"
    fi
done <<< "$ordered_slugs"

report_failures
