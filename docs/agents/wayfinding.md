# Wayfinding

Map, frontier, claim, and resolve for `/wayfinder`.

- **Map** : `.scratch/<effort>/map.md` (Notes / Decisions-so-far / Fog)
- **Child ticket** : `.scratch/<effort>/issues/NN-<slug>.md` — `Type:` = `research`/`prototype`/`grilling`/`task`, `Status:` = `claimed`/`resolved`
- **Blocking** : `Blocked by: NN, NN` near the top. Ticket unblocked when every listed file is `resolved`.
- **Frontier** : scan `.scratch/<effort>/issues/` for open, unblocked, unclaimed files ; first by number.
- **Claim** : set `Status: claimed` and save before work.
- **Resolve** : append answer under `## Answer`, set `Status: resolved`, append a context pointer (gist + link) to map's Decisions-so-far in `map.md`.