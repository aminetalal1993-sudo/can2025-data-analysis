# -*- coding: utf-8 -*-
"""
Étape 1 & 2 du Projet Portfolio : Nettoyage des données (ETL Python) & Alimentation SQLite
Auteur : Amine
Projet : Data Analyse CAN 2025 (Maroc)
"""

import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
DB_PATH = os.path.join(BASE_DIR, "data", "can2025.db")

def run_etl():
    print("=== 1. CHARGEMENT DES DONNÉES BRUTES ===")
    df_hist = pd.read_csv(os.path.join(RAW_DIR, "historical_afcon.csv"))
    df_teams = pd.read_csv(os.path.join(RAW_DIR, "teams_can2025.csv"))
    df_matches = pd.read_csv(os.path.join(RAW_DIR, "matches_can2025.csv"))
    df_players = pd.read_csv(os.path.join(RAW_DIR, "players_can2025.csv"))

    print(f"Équipes (brut) : {len(df_teams)} lignes")
    print(f"Matchs (brut)  : {len(df_matches)} lignes (Valeurs manquantes attendance : {df_matches['attendance'].isna().sum()})")

    print("\n=== 2. NETTOYAGE DES DONNÉES (DATA CLEANING) ===")
    # A. Suppression des espaces superflus et des doublons dans teams
    df_teams["team_name"] = df_teams["team_name"].str.strip()
    df_teams = df_teams.drop_duplicates(subset=["team_id"], keep="first")
    print(f"Équipes (après suppression des doublons et nettoyage texte) : {len(df_teams)} lignes")

    # B. Imputation des valeurs manquantes d'affluence par la médiane de la ville hôte
    df_matches["attendance"] = df_matches.groupby("host_city")["attendance"].transform(
        lambda x: x.fillna(x.median())
    ).astype(int)

    # C. Feature Engineering sur les joueurs (Normalisation par 90 minutes)
    df_players["goals_per_90"] = ((df_players["goals"] / df_players["minutes_played"]) * 90).round(2)
    df_players["assists_per_90"] = ((df_players["assists"] / df_players["minutes_played"]) * 90).round(2)
    df_players["goal_contributions"] = df_players["goals"] + df_players["assists"]
    df_players["goal_contributions_per_90"] = ((df_players["goal_contributions"] / df_players["minutes_played"]) * 90).round(2)
    df_players["xg_diff"] = (df_players["goals"] - df_players["xg"]).round(2)

    print("\n=== 3. EXPORT DES FICHIERS PROPRES (POUR EXCEL & POWER BI / TABLEAU) ===")
    df_hist.to_csv(os.path.join(PROC_DIR, "historical_afcon_clean.csv"), index=False, encoding="utf-8")
    df_teams.to_csv(os.path.join(PROC_DIR, "teams_can2025_clean.csv"), index=False, encoding="utf-8")
    df_matches.to_csv(os.path.join(PROC_DIR, "matches_can2025_clean.csv"), index=False, encoding="utf-8")
    df_players.to_csv(os.path.join(PROC_DIR, "players_can2025_clean.csv"), index=False, encoding="utf-8")

    print("\n=== 4. MISE À JOUR DE LA BASE DE DONNÉES SQLITE ===")
    conn = sqlite3.connect(DB_PATH)
    df_hist.to_sql("historical_afcon", conn, if_exists="replace", index=False)
    df_teams.to_sql("teams", conn, if_exists="replace", index=False)
    df_matches.to_sql("matches", conn, if_exists="replace", index=False)
    df_players.to_sql("players", conn, if_exists="replace", index=False)

    # Exemple d'exécution d'une requête SQL sur le Maroc
    query_maroc = """
    SELECT player_name, position, club, goals, assists, key_passes, rating
    FROM players
    WHERE team_id = 'MAR'
    ORDER BY rating DESC
    LIMIT 5;
    """
    print("\nTop 5 Joueurs du Maroc (via SQL) :")
    print(pd.read_sql_query(query_maroc, conn).to_string(index=False))
    conn.close()
    print("\nPipeline ETL terminé avec succès !")

if __name__ == "__main__":
    run_etl()
