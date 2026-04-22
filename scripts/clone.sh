#!/usr/bin/env bash
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOS_YML="$REPO_ROOT/repos.yml"
MIRRORS_DIR="$REPO_ROOT/mirrors"

slugs=$(python3 -c "
import yaml, sys
with open(sys.argv[1]) as f:
    data = yaml.safe_load(f)
for e in data['repos']:
    print(e['org'] + '/' + e['repo'])
" "$REPOS_YML")

failures=()

while IFS= read -r slug; do
    org="${slug%%/*}"
    dest="$MIRRORS_DIR/$slug"

    if [[ -d "$dest/.git" ]]; then
        echo "==> update $slug"
        if ! git -C "$dest" fetch --prune; then
            echo "FAIL: fetch $slug" >&2
            failures+=("$slug")
            continue
        fi
        git -C "$dest" reset --hard origin/HEAD
    else
        echo "==> clone $slug"
        mkdir -p "$MIRRORS_DIR/$org"
        if ! gh repo clone "$slug" "$dest"; then
            echo "FAIL: clone $slug" >&2
            failures+=("$slug")
            continue
        fi
    fi
done <<< "$slugs"

if [[ ${#failures[@]} -gt 0 ]]; then
    echo ""
    printf 'FAILED (%d): %s\n' "${#failures[@]}" "${failures[*]}" >&2
    exit 1
fi
