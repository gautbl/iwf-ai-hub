-- Nettoyage des données brutes vers la table finale
-- On normalise les colonnes et on gère les valeurs nulles
INSERT INTO results
SELECT 
    result_id, 
    athlete_id, 
    competition_id, 
    total_weight, 
    CAST(date AS DATE) 
FROM raw_results 
WHERE total_weight IS NOT NULL;
