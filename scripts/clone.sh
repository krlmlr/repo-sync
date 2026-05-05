#!/usr/bin/env bash
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOS_YML="$REPO_ROOT/repos.yml"
MIRRORS_DIR="$REPO_ROOT/mirrors"

# Validate exactly one template entry
template_count=$(yq '[.repos[] | select(.template == true)] | length' "$REPOS_YML")
if [[ $template_count -eq 0 ]]; then
    echo "FAIL: no entry in repos.yml has template: true" >&2
    exit 2
fi
if [[ $template_count -gt 1 ]]; then
    multiple=$(yq '.repos[] | select(.template == true) | .org + "/" + .repo' "$REPOS_YML" | paste -sd ',' -)
    echo "FAIL: multiple entries in repos.yml have template: true: $multiple" >&2
    exit 2
fi

# Extract template slug and emit ordered list (template first, then all repos)
template_slug=$(yq '.repos[] | select(.template == true) | .org + "/" + .repo' "$REPOS_YML")
if [[ -z "$template_slug" ]]; then
    echo "FAIL: unable to load repository inventory from $REPOS_YML" >&2
    exit 1
fi

parsed=$(
    # Template first
    printf '%s\n' "$template_slug"
    # Template again (for consistency with original behavior)
    printf '%s\n' "$template_slug"
    # Then all repos except template
    yq '.repos[] | select(.template != true) | .org + "/" + .repo' "$REPOS_YML"
)

template_slug=$(printf '%s\n' "$parsed" | head -n 1)
ordered_slugs=$(printf '%s\n' "$parsed" | tail -n +2)

failures=()

clone_or_update() {
    local slug="$1"
    local org="${slug%%/*}"
    local dest="$MIRRORS_DIR/$slug"

    if [[ -d "$dest/.git" ]]; then
        echo "==> update $slug"
        if ! git -C "$dest" fetch --prune; then
            echo "FAIL: fetch $slug" >&2
            failures+=("$slug")
            return 1
        fi
        if ! git -C "$dest" reset --hard origin/HEAD; then
            echo "FAIL: reset $slug" >&2
            failures+=("$slug")
            return 1
        fi
    else
        echo "==> clone $slug"
        mkdir -p "$MIRRORS_DIR/$org"
        if ! gh repo clone "$slug" "$dest"; then
            echo "FAIL: clone $slug" >&2
            failures+=("$slug")
            return 1
        fi
    fi
}

configure_template_remote() {
    local slug="$1"
    [[ "$slug" == "$template_slug" ]] && return 0
    local dest="$MIRRORS_DIR/$slug"
    local url="../../$template_slug"
    if git -C "$dest" remote get-url template >/dev/null 2>&1; then
        if ! git -C "$dest" remote set-url template "$url"; then
            echo "FAIL: set-url template $slug" >&2
            failures+=("$slug")
            return 1
        fi
    else
        if ! git -C "$dest" remote add template "$url"; then
            echo "FAIL: add template $slug" >&2
            failures+=("$slug")
            return 1
        fi
    fi
}

while IFS= read -r slug; do
    [[ -z "$slug" ]] && continue
    if clone_or_update "$slug"; then
        configure_template_remote "$slug"
    fi
done <<< "$ordered_slugs"

if [[ ${#failures[@]} -gt 0 ]]; then
    echo ""
    printf 'FAILED (%d): %s\n' "${#failures[@]}" "${failures[*]}" >&2
    exit 1
fi
