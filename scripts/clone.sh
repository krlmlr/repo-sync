#!/usr/bin/env bash
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOS_YML="$REPO_ROOT/repos.yml"
MIRRORS_DIR="$REPO_ROOT/mirrors"

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
print(template_slug)  # first entry processed: the template
for e in data['repos']:
    slug = f\"{e['org']}/{e['repo']}\"
    if slug != template_slug:
        print(slug)
" "$REPOS_YML"); then
    echo "FAIL: unable to load repository inventory from $REPOS_YML" >&2
    exit 1
fi

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
