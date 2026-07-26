-- Insert into athletes
INSERT INTO athletes (name, country) 
SELECT DISTINCT athlete_name, 'Unknown' 
FROM {{ ref('stg_results') }} 
WHERE name NOT IN (SELECT name FROM athletes);

-- Insert into results (The Fact Table)
INSERT INTO results (athlete_id, total_weight, date)
SELECT a.athlete_id, s.total_weight, s.event_date
FROM {{ ref('stg_results') }} s
JOIN athletes a ON s.athlete_name = a.name;

