# -*- coding: utf-8 -*-
"""
Étape 3 du Projet Portfolio : Génération des Visualisations Haute Résolution (Matplotlib / Seaborn)
Génère 5 graphiques prêts à être intégrés sur GitHub, LinkedIn ou dans une présentation.
"""

import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "can2025.db")
VIS_DIR = os.path.join(BASE_DIR, "visuals")
os.makedirs(VIS_DIR, exist_ok=True)

plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#cccccc"
plt.rcParams["axes.linewidth"] = 0.8

def generate_all_charts():
    conn = sqlite3.connect(DB_PATH)

    # -------------------------------------------------------------------------
    # GRAPHIQUE 1 : Évolution historique des buts/match et affluence (1957-2025)
    # -------------------------------------------------------------------------
    df_hist = pd.read_sql_query("SELECT * FROM historical_afcon ORDER BY year", conn)
    fig, ax1 = plt.subplots(figsize=(11, 5.5), dpi=160)
    ax1.plot(df_hist["year"], df_hist["goals_per_match"], color="#c1272d", marker="o", linewidth=2.5, label="Buts / Match")
    ax1.scatter([2025], [df_hist.loc[df_hist["year"] == 2025, "goals_per_match"].values[0]],
                color="#006233", s=130, zorder=5, label="CAN 2025 (Maroc : 2.46 buts/m)")
    ax1.set_title("1. Historique CAN (1957 - 2025) : Rebond Offensif lors de l'Édition Maroc 2025", fontsize=13, fontweight="bold", pad=15)
    ax1.set_xlabel("Année de l'édition", fontsize=11)
    ax1.set_ylabel("Moyenne de buts par match", color="#c1272d", fontsize=11)
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, "01_historique_evolution_buts.png"))
    plt.close()

    # -------------------------------------------------------------------------
    # GRAPHIQUE 2 : Bilan des Équipes 2025 (xG Créés vs xG Concédés par match)
    # -------------------------------------------------------------------------
    q_teams = """
    WITH tm AS (
        SELECT home_team_id AS tid, home_xg AS xgf, away_xg AS xga, home_goals AS gf FROM matches
        UNION ALL
        SELECT away_team_id AS tid, away_xg AS xgf, home_xg AS xga, away_goals AS gf FROM matches
    )
    SELECT t.team_name, t.team_id, COUNT(*) AS mp,
           AVG(tm.xgf) AS xgf_per_match, AVG(tm.xga) AS xga_per_match, SUM(tm.gf) AS total_goals
    FROM tm JOIN teams t ON tm.tid = t.team_id
    GROUP BY t.team_id
    """
    df_t = pd.read_sql_query(q_teams, conn)
    fig, ax = plt.subplots(figsize=(10.5, 6.5), dpi=160)
    colors = ["#c1272d" if tid == "MAR" else "#1f77b4" for tid in df_t["team_id"]]
    sizes = df_t["total_goals"] * 28 + 60
    ax.scatter(df_t["xgf_per_match"], df_t["xga_per_match"], s=sizes, c=colors, alpha=0.82, edgecolors="black")
    for _, r in df_t.iterrows():
        weight = "bold" if r["team_id"] in ("MAR", "SEN", "NGA", "EGY", "ALG", "CIV") else "normal"
        ax.annotate(r["team_name"], (r["xgf_per_match"] + 0.02, r["xga_per_match"] + 0.01), fontsize=8.5, fontweight=weight)
    ax.axvline(df_t["xgf_per_match"].mean(), color="gray", linestyle="--", alpha=0.6, label="Moyenne xG Créés")
    ax.axhline(df_t["xga_per_match"].mean(), color="gray", linestyle=":", alpha=0.6, label="Moyenne xG Concédés")
    ax.invert_yaxis()  # Moins de xG concédés en haut (meilleure défense)
    ax.set_title("2. Matrice d'Efficacité des 24 Équipes : Attaque (xG Créés) vs Défense (xG Concédés / match)", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Danger Offensif : Expected Goals (xG) créés par match →", fontsize=10.5)
    ax.set_ylabel("← Solidité Défensive : Expected Goals (xG) concédés par match (inversé)", fontsize=10.5)
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend(loc="lower left")
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, "02_matrice_equipes_xg.png"))
    plt.close()

    # -------------------------------------------------------------------------
    # GRAPHIQUE 3 : Scouting — Top 12 Joueurs Décisifs (Buts + Passes Décisives)
    # -------------------------------------------------------------------------
    df_top = pd.read_sql_query("""
        SELECT player_name || ' (' || team_id || ')' AS label, goals, assists, goal_contributions
        FROM players
        ORDER BY goal_contributions DESC, goals DESC, minutes_played ASC
        LIMIT 12
    """, conn).iloc[::-1]

    fig, ax = plt.subplots(figsize=(10, 6), dpi=160)
    ax.barh(df_top["label"], df_top["goals"], color="#c1272d", label="Buts")
    ax.barh(df_top["label"], df_top["assists"], left=df_top["goals"], color="#006233", label="Passes Décisives")
    ax.set_title("3. Scouting CAN 2025 : Top 12 des Joueurs les Plus Décisifs (Buts + Passes D)", fontsize=12.5, fontweight="bold", pad=12)
    ax.set_xlabel("Total Contributions Décisives", fontsize=11)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, "03_top_joueurs_decisifs.png"))
    plt.close()

    # -------------------------------------------------------------------------
    # GRAPHIQUE 4 : Focus Maroc 🇲🇦 — Progression xG Maroc vs Adversaires sur les 7 matchs
    # -------------------------------------------------------------------------
    q_mar = """
    SELECT m.match_id, m.stage,
           t.team_name AS opponent,
           CASE WHEN m.home_team_id='MAR' THEN m.home_xg ELSE m.away_xg END AS mar_xg,
           CASE WHEN m.home_team_id='MAR' THEN m.away_xg ELSE m.home_xg END AS opp_xg,
           CASE WHEN m.home_team_id='MAR' THEN m.home_goals ELSE m.away_goals END AS mar_g,
           CASE WHEN m.home_team_id='MAR' THEN m.away_goals ELSE m.home_goals END AS opp_g
    FROM matches m
    JOIN teams t ON (CASE WHEN m.home_team_id='MAR' THEN m.away_team_id ELSE m.home_team_id END) = t.team_id
    WHERE m.home_team_id='MAR' OR m.away_team_id='MAR'
    ORDER BY m.match_date
    """
    df_mar = pd.read_sql_query(q_mar, conn)
    labels = [f"{r['opponent']}\n({r['mar_g']}-{r['opp_g']})" for _, r in df_mar.iterrows()]
    x = range(len(df_mar))

    fig, ax = plt.subplots(figsize=(10.5, 5.5), dpi=160)
    w = 0.36
    ax.bar([i - w/2 for i in x], df_mar["mar_xg"], width=w, color="#c1272d", label="xG Maroc 🇲🇦")
    ax.bar([i + w/2 for i in x], df_mar["opp_xg"], width=w, color="#7f8c8d", label="xG Adversaire")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_title("4. Focus Lions de l'Atlas : Domination des Expected Goals (xG) du Maroc sur ses 7 Matchs", fontsize=12.5, fontweight="bold", pad=12)
    ax.set_ylabel("Expected Goals (xG)", fontsize=11)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, "04_focus_maroc_parcours_xg.png"))
    plt.close()

    # -------------------------------------------------------------------------
    # GRAPHIQUE 5 : Cellule de Recrutement — Les Pépites U23 (Valeur Marchande vs Note)
    # -------------------------------------------------------------------------
    df_u23 = pd.read_sql_query("""
        SELECT player_name, team_id, age, market_value_m_eur, rating, goal_contributions
        FROM players
        WHERE age <= 23
    """, conn)
    fig, ax = plt.subplots(figsize=(10, 5.8), dpi=160)
    c_u23 = ["#c1272d" if tid == "MAR" else "#006233" for tid in df_u23["team_id"]]
    ax.scatter(df_u23["market_value_m_eur"], df_u23["rating"], s=130, c=c_u23, alpha=0.85, edgecolors="black")
    for _, r in df_u23.iterrows():
        ax.annotate(f"{r['player_name']} ({r['age']}a, {r['team_id']})",
                    (r["market_value_m_eur"] + 0.6, r["rating"] + 0.005), fontsize=8.5)
    ax.axvline(20, color="#e67e22", linestyle="--", label="Plafond Budget Recrutement (20 M€)")
    ax.set_title("5. Scouting U23 : Identifier les Pépites à Haute Performance et Faible Coût (< 20 M€)", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Valeur Marchande Estimée (Millions €)", fontsize=11)
    ax.set_ylabel("Note de Performance Tournoi (Rating / 10)", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, "05_scouting_pepites_u23.png"))
    plt.close()

    conn.close()
    print(f"5 graphiques haute définition générés dans : {VIS_DIR}")

if __name__ == "__main__":
    generate_all_charts()
