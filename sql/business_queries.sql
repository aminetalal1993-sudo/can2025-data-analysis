-- ============================================================================
-- 12 REQUÊTES SQL ANALYTIQUES POUR LE PORTFOLIO DATA ANALYST (CAN 2025 MAROC)
-- Compétences : JOIN, GROUP BY, CTE (WITH), CASE WHEN, Window Functions (RANK)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- VOLET 1 : HISTORIQUE & ÉVOLUTION DE LA CAN (1957 - 2025)
-- ----------------------------------------------------------------------------

-- Q1. Évolution de la moyenne de buts et de l'affluence sur les 10 dernières éditions
SELECT 
    year AS edition,
    host_country AS pays_hote,
    winner AS vainqueur,
    matches_played AS matchs,
    total_goals AS buts_totaux,
    ROUND(goals_per_match, 2) AS buts_par_match,
    avg_attendance AS affluence_moyenne,
    CASE WHEN host_won = 1 THEN 'Oui' ELSE 'Non' END AS victoire_pays_hote
FROM historical_afcon
ORDER BY year DESC
LIMIT 10;

-- Q2. Taux de réussite historique des pays organisateurs de la CAN
SELECT 
    COUNT(*) AS total_editions,
    SUM(host_won) AS titres_pays_hote,
    ROUND(100.0 * SUM(host_won) / COUNT(*), 1) AS pourcentage_victoire_hote
FROM historical_afcon;


-- ----------------------------------------------------------------------------
-- VOLET 2 : BILAN COLLECTIF DES ÉQUIPES (CAN 2025)
-- ----------------------------------------------------------------------------

-- Q3. Bilan complet par équipe (Matchs, Buts marqués, Buts encaissés, Différence, xG) via CTE
WITH team_matches AS (
    SELECT 
        home_team_id AS team_id,
        home_goals AS goals_for,
        away_goals AS goals_against,
        home_xg AS xg_for,
        away_xg AS xg_against,
        home_possession AS possession
    FROM matches
    UNION ALL
    SELECT 
        away_team_id AS team_id,
        away_goals AS goals_for,
        home_goals AS goals_against,
        away_xg AS xg_for,
        home_xg AS xg_against,
        away_possession AS possession
    FROM matches
)
SELECT 
    t.team_name AS equipe,
    t.final_stage_2025 AS parcours,
    COUNT(*) AS matchs_joues,
    SUM(tm.goals_for) AS buts_marques,
    SUM(tm.goals_against) AS buts_encaisses,
    SUM(tm.goals_for) - SUM(tm.goals_against) AS diff_buts,
    ROUND(SUM(tm.xg_for), 2) AS xg_total,
    ROUND(SUM(tm.goals_for) - SUM(tm.xg_for), 2) AS surperformance_xg,
    ROUND(AVG(tm.possession), 1) AS possession_moyenne
FROM team_matches tm
JOIN teams t ON tm.team_id = t.team_id
GROUP BY t.team_id, t.team_name, t.final_stage_2025
ORDER BY buts_marques DESC, diff_buts DESC;

-- Q4. Affluence et spectacle par ville hôte marocaine
SELECT 
    host_city AS ville_hote,
    COUNT(*) AS nb_matchs,
    SUM(total_goals) AS total_buts,
    ROUND(AVG(total_goals), 2) AS moyenne_buts_match,
    ROUND(AVG(attendance), 0) AS affluence_moyenne,
    MAX(attendance) AS affluence_record
FROM matches
GROUP BY host_city
ORDER BY affluence_moyenne DESC;


-- ----------------------------------------------------------------------------
-- VOLET 3 : SCOUTING & RECRUTEMENT DE JOUEURS
-- ----------------------------------------------------------------------------

-- Q5. Classement des meilleurs joueurs décisifs (Buts + Passes D) avec Window Function (DENSE_RANK)
SELECT 
    DENSE_RANK() OVER (ORDER BY goal_contributions DESC, goals DESC, minutes_played ASC) AS rang,
    player_name AS joueur,
    team_name AS selection,
    position,
    club,
    goals AS buts,
    assists AS passes_decisives,
    goal_contributions AS total_decisif,
    goal_contributions_per_90 AS decisif_par_90min,
    rating AS note_moyenne
FROM players
ORDER BY rang ASC
LIMIT 10;

-- Q6. Détection des "Pépites U23 sous-cotées" (Âge <= 23 ans, Valeur <= 20 M€, Haute performance)
SELECT 
    player_name AS pepite_u23,
    team_name AS selection,
    age,
    position,
    club,
    market_value_m_eur AS valeur_marchande_meur,
    goals AS buts,
    assists AS passes_d,
    key_passes AS passes_cles,
    progressive_carries AS progressions_balle,
    rating AS note_tournoi
FROM players
WHERE age <= 23 
  AND market_value_m_eur <= 20.0
  AND minutes_played >= 300
ORDER BY rating DESC;

-- Q7. Meilleur joueur par poste (Gardien, Défenseur, Milieu, Attaquant) avec ROW_NUMBER()
WITH ranked_by_pos AS (
    SELECT 
        position,
        player_name,
        team_name,
        club,
        goals,
        assists,
        tackles_won,
        interceptions,
        duels_won_pct,
        rating,
        ROW_NUMBER() OVER (PARTITION BY position ORDER BY rating DESC) AS pos_rank
    FROM players
)
SELECT 
    position,
    player_name AS meilleur_joueur,
    team_name AS selection,
    club,
    rating AS note_moyenne,
    duels_won_pct AS pct_duels_gagnes
FROM ranked_by_pos
WHERE pos_rank <= 2
ORDER BY position, pos_rank;


-- ----------------------------------------------------------------------------
-- VOLET 4 : FOCUS SPÉCIAL MAROC (LIONS DE L'ATLAS)
-- ----------------------------------------------------------------------------

-- Q8. Parcours match par match du Maroc à la CAN 2025
SELECT 
    m.match_id,
    m.match_date AS date_match,
    m.stage AS tour,
    t_opp.team_name AS adversaire,
    CASE WHEN m.home_team_id = 'MAR' THEN m.home_goals ELSE m.away_goals END AS buts_maroc,
    CASE WHEN m.home_team_id = 'MAR' THEN m.away_goals ELSE m.home_goals END AS buts_adversaire,
    CASE WHEN m.home_team_id = 'MAR' THEN m.home_xg ELSE m.away_xg END AS xg_maroc,
    CASE WHEN m.home_team_id = 'MAR' THEN m. away_xg ELSE m.home_xg END AS xg_adversaire,
    CASE WHEN m.home_team_id = 'MAR' THEN m.home_possession ELSE m.away_possession END AS possession_maroc,
    m.host_city AS ville,
    m.attendance AS spectateurs
FROM matches m
JOIN teams t_opp ON (
    CASE WHEN m.home_team_id = 'MAR' THEN m.away_team_id ELSE m.home_team_id END = t_opp.team_id
)
WHERE m.home_team_id = 'MAR' OR m.away_team_id = 'MAR'
ORDER BY m.match_date ASC;

-- Q9. Contributions individuelles de l'effectif du Maroc
SELECT 
    player_name AS joueur_marocain,
    position AS poste,
    club,
    minutes_played AS minutes,
    goals AS buts,
    assists AS passes_d,
    key_passes AS passes_cles,
    progressive_carries AS progressions,
    tackles_won + interceptions AS actions_defensives,
    duels_won_pct AS duels_gagnes_pct,
    rating AS note
FROM players
WHERE team_id = 'MAR'
ORDER BY rating DESC;
