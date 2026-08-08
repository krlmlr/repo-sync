#!/usr/bin/env bash
# Mirror every repository in repos.yml under mirrors/<org>/<repo>/.
#
# The template is mirrored twice: as a checkout like every other repo,
# and as a bare clone at mirrors/<org>/<repo>.git beside it.
# The bare clone is what the `template` remotes point at,
# because a repository with a branch checked out
# is the wrong thing to have on the other end of a fetch or a push.
#
# The mirrors are made several at a time. Each is an independent conversation
# with GitHub that spends its time waiting, so running them one after another
# costs the sum of the waits for no reason: `parallel` re-invokes this script
# once per mirror instead.
#
# The re-invocation is the whole child interface -- `clone.sh --checkout <slug>`
# and `clone.sh --bare <slug>` -- so running one by hand does exactly what the
# batch does to that one repository, which is what makes a failing repo
# something you can reproduce on its own.
set -uo pipefail

# shellcheck source-path=SCRIPTDIR
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

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
        # `--prune-tags` as well as `--prune`: tags are the one ref namespace
        # git does not partition by remote, so `--prune` never removes one and
        # anything that ever landed in `refs/tags/` stays -- notably the
        # template's tags, which a fetch of the `template` remote used to
        # auto-follow into every mirror. This is the re-baselining tool, which
        # resets the working tree onto origin/HEAD a line below; a tag the
        # upstream does not have is local state, and goes the same way.
        if ! git -C "$dest" fetch --prune --prune-tags; then
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

    # Nothing from `refs/tags/` comes across this remote.
    #
    # A fetch auto-follows every tag pointing at an object it downloads, and a
    # fetch of the template downloads the template's whole history. Branches
    # survive that because they land in `refs/remotes/template/`, a namespace
    # this remote has to itself; tags have no such namespace, so the template's
    # would arrive indistinguishable from the mirror's own -- and stay, since
    # `--prune` does not remove tags.
    #
    # On the remote rather than on a fetch, so every fetch of it inherits this:
    # `sync`'s, one typed by hand, and whatever reconcile turns out to be.
    # Written on every run, like the URL above, so a mirror configured before
    # this existed is repaired without being re-cloned.
    if ! git -C "$dest" config remote.template.tagOpt --no-tags; then
        fail "$slug" "config tagOpt template $slug"
        return 1
    fi
}

# One mirror, in a child process.
#
# `parallel` re-invokes the script rather than calling an exported shell
# function: it runs its commands through `$SHELL`, which is the operator's
# login shell and need not be bash, and an exported bash function does not
# survive that. A path to a script with its own shebang survives anything.
run_one() {
    local mode="$1"
    local slug="$2"

    case "$mode" in
        --checkout)
            clone_or_update "$slug" || return 1
            configure_template_remote "$slug" || return 1
            ;;
        --bare)
            clone_or_update_bare "$slug" || return 1
            ;;
        *)
            echo "FAIL: unknown mode $mode" >&2
            return 2
            ;;
    esac
}

if [[ $# -gt 0 ]]; then
    if [[ $# -ne 2 ]]; then
        echo "usage: clone.sh [--checkout|--bare <org/repo>]" >&2
        exit 2
    fi
    load_template_slug
    run_one "$1" "$2"
    exit
fi

require_parallel
load_inventory

# Both mirrors of the template, and both before anything points at them.
# They are independent clones of the same upstream,
# so one failing says nothing about the other: both are attempted,
# and side by side, since neither waits on the other either.
printf '%s\n' --checkout --bare | run_parallel "$SCRIPTS_DIR/clone.sh" {} "$template_slug"

# Only once those are on disk does the rest of the inventory follow,
# so that every `template` remote written below
# names a path that already resolves.
printf '%s\n' "$other_slugs" | run_parallel "$SCRIPTS_DIR/clone.sh" --checkout {}

report_failures
