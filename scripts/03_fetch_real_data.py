# -*- coding: utf-8 -*-
"""
Étape Bonus Portfolio : Collecte Automatique de Données Réelles (API REST & Open Data)
Fichier : scripts/03_fetch_real_data.py
Auteur  : Amine

Ce script démontre comment un Data Analyst collecte des données depuis le Web via :
1. API-Football (REST API officielle avec clé API : équipes, matchs, joueurs CAN 2025)
2. StatsBomb Open Data API (100% Gratuit sans clé : événements détaillés de la CAN)
3. Sauvegarde automatique en CSV (data/raw/) et dans la base SQLite (data/can2025.db)
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.error
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
DB_PATH = os.path.join(BASE_DIR, "data", "can2025.db")

# ==============================================================================
# CONFIGURATION : CLÉ API-FOOTBALL (Optionnelle)
# Créez un compte gratuit sur https://dashboard.api-football.com (100 req/jour)
# ==============================================================================
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "VOTRE_CLE_API_ICI")
AFCON_LEAGUE_ID = 6      # ID officiel de la Coupe d'Afrique des Nations dans API-Football
AFCON_SEASON = 2025      # Édition Maroc 2025


def fetch_json_url(url, headers=None):
    """Fonction utilitaire pour interroger une URL JSON sans dépendance externe."""
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


# ==============================================================================
# SOURCE 1 : API-FOOTBALL (Calendrier, Scores, Stades & Joueurs CAN 2025)
# ==============================================================================
def fetch_from_api_football(api_key, league_id=AFCON_LEAGUE_ID, season=AFCON_SEASON):
    """
    Récupère tous les matchs et les meilleurs joueurs de la CAN depuis API-Football.
    """
    if not api_key or api_key == "VOTRE_CLE_API_ICI":
        print("ℹ️ [API-Football] Aucune clé API renseignée dans API_FOOTBALL_KEY.")
        print("   -> Pour activer API-Football : inscrivez-vous gratuitement sur https://dashboard.api-football.com")
        print("   -> Puis définissez votre clé : set API_FOOTBALL_KEY=votre_cle dans le terminal.\n")
        return None, None

    headers = {
        "x-apisports-key": api_key,
        "Accept": "application/json"
    }

    print(f"🌐 [API-Football] Téléchargement des matchs (League={league_id}, Season={season})...")
    url_fixtures = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}"
    res_fixtures = fetch_json_url(url_fixtures, headers=headers)

    matches_list = []
    for item in res_fixtures.get("response", []):
        fix = item.get("fixture", {})
        venue = fix.get("venue", {})
        league = item.get("league", {})
        teams = item.get("teams", {})
        goals = item.get("goals", {})

        matches_list.append({
            "api_fixture_id": fix.get("id"),
            "match_date": (fix.get("date") or "")[:10],
            "stage": league.get("round"),
            "stadium": venue.get("name"),
            "host_city": venue.get("city"),
            "home_team": teams.get("home", {}).get("name"),
            "away_team": teams.get("away", {}).get("name"),
            "home_goals": goals.get("home"),
            "away_goals": goals.get("away"),
            "status": fix.get("status", {}).get("short")
        })

    df_api_matches = pd.DataFrame(matches_list)

    print(f"🌐 [API-Football] Téléchargement des meilleurs buteurs (Top Scorers)...")
    url_scorers = f"https://v3.football.api-sports.io/players/topscorers?league={league_id}&season={season}"
    res_scorers = fetch_json_url(url_scorers, headers=headers)

    scorers_list = []
    for item in res_scorers.get("response", []):
        player = item.get("player", {})
        stats = (item.get("statistics") or [{}])[0]
        team = stats.get("team", {})
        games = stats.get("games", {})
        goals = stats.get("goals", {})
        passes = stats.get("passes", {})
        dribbles = stats.get("dribbles", {})

        scorers_list.append({
            "player_id": player.get("id"),
            "player_name": player.get("name"),
            "age": player.get("age"),
            "nationality": player.get("nationality"),
            "team_name": team.get("name"),
            "position": games.get("position"),
            "matches_played": games.get("appearences"),
            "minutes_played": games.get("minutes"),
            "rating": float(games.get("rating") or 0.0),
            "goals": goals.get("total") or 0,
            "assists": goals.get("assists") or 0,
            "key_passes": passes.get("key") or 0,
            "dribbles_success": dribbles.get("success") or 0
        })

    df_api_scorers = pd.DataFrame(scorers_list)
    return df_api_matches, df_api_scorers


# ==============================================================================
# SOURCE 2 : STATSBOMB OPEN DATA (100% GRATUIT - SANS CLÉ API)
# ==============================================================================
def fetch_from_statsbomb_open_data():
    """
    Récupère gratuitement les matchs officiels de la CAN depuis le dépôt GitHub
    StatsBomb Open Data (competition_id = 1267 : African Cup of Nations).
    Aucune clé API n'est requise !
    """
    print("🌐 [StatsBomb Open Data] Connexion au dépôt GitHub officiel StatsBomb...")
    comp_url = "https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json"

    try:
        competitions = fetch_json_url(comp_url)
    except Exception as e:
        print(f"⚠️ Impossible de contacter GitHub StatsBomb ({e}). Vérifiez votre connexion Internet.")
        return None

    afcon_seasons = [
        c for c in competitions
        if "African Cup of Nations" in c.get("competition_name", "") or c.get("competition_id") == 1267
    ]

    if not afcon_seasons:
        print("ℹ️ Compétition CAN non trouvée dans la liste StatsBomb.")
        return None

    # On prend la saison la plus récente disponible dans StatsBomb Open Data
    latest = sorted(afcon_seasons, key=lambda x: x.get("season_name", ""), reverse=True)[0]
    comp_id = latest["competition_id"]
    season_id = latest["season_id"]
    season_name = latest["season_name"]

    print(f"✅ [StatsBomb] Édition trouvée : {latest['competition_name']} ({season_name}) [comp_id={comp_id}, season_id={season_id}]")

    matches_url = f"https://raw.githubusercontent.com/statsbomb/open-data/master/data/matches/{comp_id}/{season_id}.json"
    matches_json = fetch_json_url(matches_url)

    rows = []
    for m in matches_json:
        rows.append({
            "statsbomb_match_id": m.get("match_id"),
            "match_date": m.get("match_date"),
            "stage": m.get("competition_stage", {}).get("name"),
            "home_team": m.get("home_team", {}).get("home_team_name"),
            "away_team": m.get("away_team", {}).get("away_team_name"),
            "home_score": m.get("home_score"),
            "away_score": m.get("away_score"),
            "stadium": (m.get("stadium") or {}).get("name"),
            "referee": (m.get("referee") or {}).get("name")
        })

    df_sb_matches = pd.DataFrame(rows).sort_values("match_date")
    print(f"✅ [StatsBomb] {len(df_sb_matches)} matchs officiels récupérés avec succès !")
    return df_sb_matches


# ==============================================================================
# SAUVEGARDE DANS CSV (data/raw/) ET SQLITE (data/can2025.db)
# ==============================================================================
def main():
    print("==================================================================")
    print("🚀 COLLECTE DE DONNÉES WEB & API — PROJET CAN 2025 (MAROC)")
    print("==================================================================\n")

    conn = sqlite3.connect(DB_PATH)

    # 1. Test API-Football
    df_api_m, df_api_p = fetch_from_api_football(API_FOOTBALL_KEY)
    if df_api_m is not None and not df_api_m.empty:
        csv_m = os.path.join(RAW_DIR, "api_football_matches.csv")
        df_api_m.to_csv(csv_m, index=False, encoding="utf-8")
        df_api_m.to_sql("api_football_matches", conn, if_exists="replace", index=False)
        print(f"💾 Matchs API-Football sauvegardés dans : {csv_m} et table SQL 'api_football_matches'")

    if df_api_p is not None and not df_api_p.empty:
        csv_p = os.path.join(RAW_DIR, "api_football_topscorers.csv")
        df_api_p.to_csv(csv_p, index=False, encoding="utf-8")
        df_api_p.to_sql("api_football_topscorers", conn, if_exists="replace", index=False)
        print(f"💾 Buteurs API-Football sauvegardés dans : {csv_p} et table SQL 'api_football_topscorers'")

    # 2. Collecte gratuite StatsBomb Open Data
    df_sb = fetch_from_statsbomb_open_data()
    if df_sb is not None and not df_sb.empty:
        csv_sb = os.path.join(RAW_DIR, "statsbomb_afcon_matches.csv")
        df_sb.to_csv(csv_sb, index=False, encoding="utf-8")
        df_sb.to_sql("statsbomb_afcon_matches", conn, if_exists="replace", index=False)
        print(f"💾 Matchs StatsBomb sauvegardés dans : {csv_sb}")
        print("💾 Table SQL 'statsbomb_afcon_matches' ajoutée dans data/can2025.db !\n")
        print("Aperçu des 5 derniers matchs récupérés en ligne :")
        print(df_sb[["match_date", "stage", "home_team", "home_score", "away_score", "away_team"]].tail(5).to_string(index=False))

    conn.close()
    print("\n✅ Collecte terminée avec succès !")


if __name__ == "__main__":
    main()
