# Changelog

- 2026-11-25: Browser tab icon now matches mismo.org: every prospectus and the contract page point at the shared icon (resources.mismo.org/assets/favicon-48x48.png), CN-030. The contract page's head only; its wording is unchanged.
- 2026-11-23: Once an application is submitted, the page's PDF ends the Sponsor Contract with a Signed Application block (sponsor, program, level, opportunity, contact, signer, title, date, reference, contract version), and the confirmation has a Save a Signed Copy (PDF) button. Before, the PDF left out the signing part, so a sponsor's saved copy had no signature (Guidehouse).
- 2026-11-19: Download PDF on every prospectus: the browser's Save as PDF, named from the page title, with today's availability and a note on where to apply; the application form, summary and signing stay on the web page. `?pdf` opens it straight away (the portal's Download PDF link).
- 2026-11-07: A hidden spam-trap box and the time on the page go with each application, for the portal's spam check.
- 2026-11-07: Spring & Fall 2027 package prospectus (`spring-fall-2027/`), 10% off, for after the Winter Summit.
- 2026-11-07: Every page is now built from `tools/template.html` by `tools/build.py`; packages of summits in `catalog.json`.
- 2026-11-07: Each application sends the contract version it agreed to; the wording is kept in `contracts/`.
- 2026-11-07: The price list (`catalog.json`); `?practice` runs any page on test data.
- 2026-11-05: Spring and Fall 2027 prospectuses; availability counted per summit.
