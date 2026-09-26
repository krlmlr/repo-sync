## 1. Inventory

- [x] 1.1 Add `maintained: true` to the 35 maintained entries in `repos.yml`, after `repo` and before `template`

## 2. Inventory writer

- [x] 2.1 In `scripts/fetch_inventory.py`, read the existing `repos.yml` once and derive both flags from it
- [x] 2.2 Re-apply `maintained: true` to matching entries in the freshly built inventory
- [x] 2.3 Name any previously flagged entry missing from the new branch list on stderr, and write the file without it
- [x] 2.4 Apply the template flag first, so a missing template is refused before any note about `maintained`
- [x] 2.5 Write each entry's keys as `org`, `repo`, `maintained`, `template` with `sort_keys=False`

## 3. Verification

Against the writer with `fetch_branches` stubbed to return a given branch list:

- [x] 3.1 A refresh over the current branch list keeps every flag, and a second refresh writes identical bytes
- [x] 3.2 For an inventory without `maintained`, the output is byte-identical to the previous writer's
- [x] 3.3 A flagged repository missing from the branch list is named on stderr and dropped, and the run exits zero
- [x] 3.4 A new repository in the branch list is written without flags
- [x] 3.5 A missing template still exits non-zero, leaves `repos.yml` untouched, and prints only the template error
- [x] 3.6 A first run with no `repos.yml` flags nothing
- [x] 3.7 `load_inventory` in `scripts/lib.sh` reads the flagged `repos.yml` with the same template and the same 44 other slugs

## 4. Roadmap

- [x] 4.1 Record the flag under §1
