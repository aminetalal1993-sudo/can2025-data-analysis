# 📈 Guide Étape par Étape : Dashboard Power BI / Tableau

Ce guide vous donne l'architecture exacte et les formules **DAX** pour construire votre rapport **Power BI** (ou **Tableau**) en important les 4 fichiers propres du dossier `data/processed/`.

---

## 1. Modèle de Données (Schéma en Étoile)

Importez les fichiers de `data/processed/` dans Power BI Desktop et créez les relations suivantes dans la **Vue Modèle** :
* `teams_can2025_clean[team_id]` (1) ➔ (*) `players_can2025_clean[team_id]`
* `teams_can2025_clean[team_id]` (1) ➔ (*) `matches_can2025_clean[home_team_id]`

---

## 2. Les 6 Mesures DAX Indispensables à créer

Créez une table de mesures `_Mesures_CAN2025` et copiez ces formules DAX :

```dax
Total Buts Tournoi = SUM(matches_can2025_clean[total_goals])

Moyenne Buts par Match = AVERAGE(matches_can2025_clean[total_goals])

Affluence Moyenne = AVERAGE(matches_can2025_clean[attendance])

Total Actions Décisives = SUM(players_can2025_clean[goals]) + SUM(players_can2025_clean[assists])

Surperformance xG = SUM(players_can2025_clean[goals]) - SUM(players_can2025_clean[xg])

Buts Maroc = 
CALCULATE(
    SUM(players_can2025_clean[goals]),
    players_can2025_clean[team_id] = "MAR"
)
```

---

## 3. Structure du Dashboard en 4 Pages (Storytelling)

### Page 1 : Vue Exécutive & Historique de la CAN
* **4 Cartes KPI en haut** : *52 Matchs*, *128 Buts (2.46/match)*, *48 900 Spectateurs/match*, *Vainqueur : Maroc 🇲🇦*.
* **Courbe temporelle** : `year` en axe X et `goals_per_match` en axe Y (montrant le pic offensif de 2025).
* **Graphique en barres** : Affluence moyenne par ville marocaine (Tanger et Rabat en tête).

### Page 2 : Analyse Collective des 24 Équipes
* **Nuage de points (Scatter Chart)** : Valeur marchande (`market_value_m_eur`) vs Classement FIFA (`fifa_rank`), couleur par `final_stage_2025`.

### Page 3 : Cellule de Scouting & Recrutement
* **Segments (Filtres)** : Poste (`position`), Âge (`age` <= 23 ans), Budget (`market_value_m_eur`).
* **Matrice des pépites** : `player_name`, `team_name`, `club`, `goals_per_90`, `key_passes`, `rating`.

### Page 4 : Focus Spécial Lions de l'Atlas (Maroc 🇲🇦)
* Thème visuel aux couleurs du Maroc (**Rouge `#C1272D`** et **Vert `#006233`**).
* Comparaison `xG Maroc` vs `xG Adversaire` sur les 7 matchs (Comores, Zambie, Mali, Gabon, Algérie, Nigeria, Sénégal).
* Focus joueurs : **Brahim Díaz** (Meilleur buteur - 6 buts), **Achraf Hakimi** (Meilleur passeur/latéral - 4 passes D, 19 passes clés), **Yassine Bounou** (4 Clean Sheets).
