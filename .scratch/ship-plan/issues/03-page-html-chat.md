# 03: Page HTML de chat

**What to build:** Un utilisateur ouvre `http://localhost:8000`, voit un champ texte, pose une question sur les regles IWF ou les resultats, recoit une reponse. La session persiste entre les messages.

**Blocked by:** 01 (Dockeriser l'API)

**Status:** ready-for-agent

- [ ] Creer `src/api/static/index.html` (champ texte, bouton envoyer, zone reponse, session_id)
- [ ] Ajouter route `GET /` dans `src/api/main.py` qui sert la page HTML
- [ ] Appels `POST /chat` via `fetch()` en JavaScript
- [ ] Design sobre et responsive
- [ ] Test : `GET /` retourne 200 avec `text/html`
- [ ] Test : la page HTML contient les elements du formulaire