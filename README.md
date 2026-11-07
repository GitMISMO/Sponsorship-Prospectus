# Sponsorship-Prospectus

The public sponsorship prospectuses, at resources.mismo.org/Sponsorship-Prospectus/:

| Folder | Sells |
| --- | --- |
| (top) | 2027 Summit Series and Winter 2027 Summit |
| `spring-2027/` | Spring 2027 Summit |
| `fall-2027/` | Fall 2027 Summit |
| `spring-fall-2027/` | Spring & Fall 2027 package, 10% off (for after the Winter Summit) |

Applications go to the Sponsorship Intake flow and land in the Sponsorship Portal (the
`sponsorship` repo). Availability comes from the Sponsorship Availability flow.

## How the pages are made

Every page is built from one template by one script. **Don't edit a page directly**: the
checks fail when a page differs from what the script makes.

- `tools/template.html`: the 2027 Series and Winter prospectus. Wording, layout, benefits and
  the contract all change here.
- `tools/prospectuses.json`: which pages exist (folder, summits, package), each summit's
  dates and hotel, and the availability shown before the live numbers arrive.
- `catalog.json`: the price list. A package's price is its summits' single prices less its
  discount.
- `contracts/`: every version of the Sponsor Contract wording, never changed once sponsors
  have agreed to it.

Then run `python3 tools/build.py` and publish what it writes.

**A new prospectus** (one summit, or a package of summits at a discount): add a page to
`tools/prospectuses.json`, and for a package add it to `packages` in `catalog.json`. Run the
build, run the checks, publish the new folder, and add a card for it on the portal's
Prospectuses tab.

**A price change:** edit `catalog.json`, run `node tests/apply-catalog.js` in the sponsorship
repo (it updates the template and the portal too), then run the build.

## Practice copy

Add `?practice` to any prospectus address to try it on made-up data. Nothing is sent to the
flows; the application shows up in the practice portal (resources.mismo.org/sponsorship/?practice).

## Checks

The checks live in the `sponsorship` repo (`tests/checks.js`). GitHub runs them after every
change here; a red X on a change means one failed.
