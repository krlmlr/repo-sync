# shellcheck shell=bash
#
# Shared by scripts/clone.sh and scripts/sync.sh.
# Deliberately not executable: it is sourced, never run --
# which is also why it has a shell directive and no shebang.
#
# The template designation lives here rather than in either caller,
# so both tools read the inventory the same way
# and reject the same malformed one.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOS_YML="$REPO_ROOT/repos.yml"
MIRRORS_DIR="$REPO_ROOT/mirrors"

failures=()

# Read repos.yml into `template_slug` and `ordered_slugs`.
# The order is the whole inventory with the template first,
# so a run that walks it in order finds the template's mirrors already on disk
# by the time it wires up a `template` remote that points at them.
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
    # shellcheck disable=SC2034  # read by the script that sourced this one
    ordered_slugs=$(printf '%s\n' "$parsed" | tail -n +2)
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

# Record a failure and carry on: one unreachable repo must not end the batch.
fail() {
    local slug="$1"
    local message="$2"
    echo "FAIL: $message" >&2
    failures+=("$slug")
}

report_failures() {
    if [[ ${#failures[@]} -gt 0 ]]; then
        echo ""
        printf 'FAILED (%d): %s\n' "${#failures[@]}" "${failures[*]}" >&2
        exit 1
    fi
}
