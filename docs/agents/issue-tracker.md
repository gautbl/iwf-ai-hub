# Issue tracker: Local Markdown

Issues and specs live as markdown files under `.scratch/`.

## Conventions

- One feature per directory : `.scratch/<feature-slug>/`
- Spec : `.scratch/<feature-slug>/spec.md`
- Issues numbered `01-NN` : `.scratch/<feature-slug>/issues/<NN>-<slug>.md`
- Triage state : `Status:` line near the top (roles in `triage-labels.md`)
- Comments appended under `## Comments`

## Create an issue

Create a new `.scratch/<feature-slug>/issues/<NN>-<slug>.md` (create directory if needed).

## Fetch a ticket

Read the file at the referenced path. The user normally passes the path or issue number directly.

## Wayfinding

See `docs/agents/wayfinding.md` for map, frontier, claim, and resolve operations used by `/wayfinder`.