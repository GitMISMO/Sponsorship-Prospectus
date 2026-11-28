# Sponsorship-Prospectus

The public sponsorship prospectuses, at resources.mismo.org/Sponsorship-Prospectus/:

| Folder | Sells |
| --- | --- |
| (top) | 2027 Summit Series and Winter 2027 Summit |
| `spring-2027/` | Spring 2027 Summit |
| `fall-2027/` | Fall 2027 Summit |
| `spring-fall-2027/` | Spring & Fall 2027 package, 10% off (for after the Winter Summit) |
| `app/` | The phone version for the MyMISMO app: every published program in one step-by-step page |

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

## The MyMISMO App Version (`app/`)

resources.mismo.org/Sponsorship-Prospectus/app/ is the prospectus made for a phone, opened from
the MyMISMO app's Sponsor a Summit button (Jonna, November 27, 2026). Five steps with a bar along
the bottom: choose a summit, choose a level (price, registrations, benefits, live availability),
choose the opportunity and day, your details and logo, then review, read the contract and sign.
It sends exactly what the prospectus pages send, to the same Intake flow, with the same contract
version, so the portal can't tell them apart; the confirmation offers Save a Signed Copy (PDF).

- **Nothing in it is typed by hand.** `tools/build_app.py` (run by `tools/build.py`) makes
  `app/index.html` from `tools/app-template.html` (the app's layout and script), the built pages
  (each program's tiers, prices, benefits, opportunities and built-in availability, the flow
  addresses), and `tools/template.html` (the contract, the audience figures, the quotes, the logo).
  Change wording or prices where you always do and rebuild; change the app's look in
  `tools/app-template.html`.
- **Which programs it offers** is set in the Sponsorship Portal: Prospectuses tab, the Publish on
  MyMISMO box on each card (saved in `settings/main.mymismo`). The website's sponsors job copies the
  boxes to the public `resources.mismo.org/sponsors/prospectus-app.json`
  (`{"pages":{"series-winter":true,"spring":false,"fall":false,"spring-fall":false}}`), and the
  app reads that when it opens. Until that file exists, the app offers the Series and Winter. Add
  `?show=all` to see every program (for checking one before publishing it).
- Availability is counted per summit with the same rules as the pages (a Series slot must be free
  at all three; a package at both); the checks compare the app's count with each page's.
- Selections (never the logo) are kept on the phone for 30 days in case someone leaves part way;
  Start Over clears them. `?practice` works here too.

## Download PDF

The **Download PDF** button in each page's top bar opens the browser's Save as PDF, with the file
named from the page title. The print layout (`@media print` in the template) scales the pages to
letter size, starts each section on a new sheet, shows today's availability and a note on where to
apply, and leaves out the application form, the summary and the signing. Adding `?pdf` to an
address opens it by itself once the live availability is in; the portal's Prospectuses tab uses
that for its Download PDF links.

## Back button

The browser's Back button goes to the last page you were on (a jump from the menu, the Contents
or the search, or the page you stopped scrolling on); Forward goes again. It never undoes
anything on the form, and the address never changes. It's the shared
resources.mismo.org/assets/back.js, loaded in the template's `<head>` (never copy it here); the
template tells it which page you're on (`MismoBack.pages`). The prospectus has no side panels or
drawers, so there is nothing for Back to close first. `tools/back-check.js` checks it (CN-033).

## Practice copy

Add `?practice` to any prospectus address to try it on made-up data. Nothing is sent to the
flows; the application shows up in the practice portal (resources.mismo.org/sponsorship/?practice).

## Checks

The checks live in the `sponsorship` repo (`tests/checks.js`). GitHub runs them after every
change here, then this repo's `tools/back-check.js` (the Back button: `node tools/back-check.js
<sponsorship repo folder>`); a red X on a change means one failed.
