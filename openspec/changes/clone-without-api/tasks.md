## 1. Shared URL helper

- [x] 1.1 Add `github_url` to `scripts/lib.sh`,
          building `git@github.com:<slug>.git` from an inventory slug
- [x] 1.2 Record in `lib.sh` why the URL comes from the inventory rather than from the API,
          and why SSH rather than HTTPS

## 2. Clone over SSH

- [x] 2.1 Replace `gh repo clone "$slug" "$dest"` in `scripts/clone.sh` with `git clone "$(github_url "$slug")" "$dest"`
- [x] 2.2 Replace the bare mirror's `gh repo clone ... -- --mirror` with `git clone --mirror "$(github_url "$slug")" "$dest"`
- [x] 2.3 Rewrite `origin` to the SSH URL before fetching an existing checkout,
          recording a failure if the rewrite fails
- [x] 2.4 Do the same for the template's bare mirror
- [x] 2.5 Confirm `scripts/sync.sh` needs no change:
          it works through remotes `clone` configures

## 3. Documentation

- [x] 3.1 Update `ROADMAP.md` §2.0 and §2.1 to record SSH as the transport and the prerequisite
- [x] 3.2 Replace the `gh auth login` prerequisite comment in `mise.toml` with the SSH one,
          naming the `known_hosts` step

## 4. Verification

- [x] 4.1 `bash -n` and `shellcheck -x` clean on all three scripts
- [x] 4.2 A fresh clone produces the same mirror layout as before, over an SSH `origin`,
          with no `upstream` remote and no credential anywhere
- [x] 4.3 A second `clone` run changes nothing and exits zero
- [x] 4.4 A mirror carrying an HTTPS `origin` is rewritten to SSH and fetched, without being re-cloned
- [x] 4.5 `sync` still advances mirrors, updates `template/*` refs and rebases unpushed local work
- [x] 4.6 An unreachable repo is still isolated:
          reported, the rest processed, non-zero exit
- [x] 4.7 Confirm no `gh` invocation remains anywhere in `scripts/`
