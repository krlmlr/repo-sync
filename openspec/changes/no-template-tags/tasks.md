## 1. Keep the template's tags out

- [x] 1.1 In `configure_template_remote`, set `remote.template.tagOpt` to `--no-tags`,
          after both the add and the set-url branches so existing mirrors are repaired too
- [x] 1.2 Record the failure as `config tagOpt <slug>` and return non-zero, as the sibling steps do
- [x] 1.3 Pass `--no-tags` to `sync`'s `git fetch template`,
          so a mirror configured before 1.1 stops importing tags without waiting for a `clone` run

## 2. Remove the tags already imported

- [x] 2.1 In `clone_or_update`, fetch with `--prune --prune-tags` on the update path
- [x] 2.2 Leave `sync` pruning nothing: it keeps local state that has not been pushed, tags included

## 3. Verification

Against a fixture: three inventory repos served from local bare repositories, reached through `url.<path>.insteadOf git@github.com:`
so the scripts run unmodified.

- [x] 3.1 A fresh `clone` leaves each mirror with its own upstream's tags and none of the template's,
          and `remote.template.tagOpt` set to `--no-tags`
- [x] 3.2 After a new commit and a new tag on the template, `sync` advances every mirror's `refs/remotes/template/*` and adds no tag
- [x] 3.3 A mirror with `tagOpt` unset and the template's tags already in `refs/tags/` imports no further tags across a `sync`,
          and loses none
- [x] 3.4 A `clone` run over that mirror prunes the imported tags and rewrites `tagOpt`
- [x] 3.5 A second `clone` and a second `sync` change nothing and exit zero
- [x] 3.6 A tag pushed to a mirror's own upstream still reaches the mirror
- [x] 3.7 `bash -n` on both scripts

## 4. Roadmap

- [x] 4.1 Record under §2.2 that the `template` remote carries branches and not tags
