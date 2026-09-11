---
description: Revue GO/NO-GO de la Partie 1 (Phase 1 infra + Phase 2 ETL dbt)
---

Revue de la Partie 1 (Phases 1-2) avant passage a la Phase 3.
Ne modifie rien : produis un rapport puis attends validation.

1. Lance pytest tests/ et rapporte chaque echec (fichier, test, cause).
2. Utilise l agent sql-reviewer sur les modeles dbt/models/ modifies
   depuis le dernier commit (a defaut, sur l ensemble des marts et staging).
3. Verifie la coherence medallion :
   - staging materialise en view, marts en table
   - lineage raw_ -> stg_ -> dim_/fct_
   - tests not_null + unique sur chaque cle primaire dans schema.yml
4. Verifie l infra : docker-compose.yaml (services, ports, volume data/duckdb/)
   et la presence de l extension VSS dans src/db/init.sql.
5. Produis un verdict final : GO (pret pour la Phase 3) ou NO-GO
   avec la liste ordonnee des points bloquants.