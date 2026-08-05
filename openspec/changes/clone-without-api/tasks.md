## 1. Shared transport and credential helpers

- [x] 1.1 Add `github_url` to `scripts/lib.sh`, building `https://github.com/<slug>.git` from an inventory slug
- [x] 1.2 Add `git_authenticated` to `scripts/lib.sh`, running `git` with `credential.helper` cleared and then set to `!gh auth git-credential`
- [x] 1.3 Document in `lib.sh` why the helper list is cleared first, and that local-path git commands deliberately do not go through it

## 2. Clone over git transport

- [x] 2.1 Replace `gh repo clone "$slug" "$dest"` in `scripts/clone.sh` with `git_authenticated clone "$(github_url "$slug")" "$dest"`
- [x] 2.2 Replace the bare mirror's `gh repo clone ... -- --mirror` with `git_authenticated clone --mirror "$(github_url "$slug")" "$dest"`
- [x] 2.3 Route both `origin` fetches in `clone.sh` through `git_authenticated`, leaving `reset --hard`, `rev-parse` and the `remote` commands as plain `git`

## 3. Sync authenticates the same way

- [x] 3.1 Route `git pull --rebase` and the bare mirror's `git fetch --prune` in `scripts/sync.sh` through `git_authenticated`
- [x] 3.2 Leave the `template` fetch as plain `git`, its URL being a relative local path

## 4. Documentation

- [x] 4.1 Update `ROADMAP.md` §2.1 to record the git transport and `gh`-as-credential-source
- [x] 4.2 Update the `clone` prerequisite comment in `mise.toml` to say what `gh` is needed for

## 5. Verification

- [x] 5.1 `bash -n` and `shellcheck` clean on all three scripts
- [x] 5.2 A fresh clone of a public repo produces the same mirror layout as before, with an `origin` URL carrying no credential
- [x] 5.3 A second `clone` run over the same tree changes nothing and exits zero
- [x] 5.4 Confirm no `gh` subcommand other than `auth git-credential` remains in the scripts, and that it is reached only when GitHub asks for a credential
- [x] 5.5 Confirm a clone still runs to completion with the API rate limit spent, which is the failure this change is for
