# -*- coding: utf-8 -*-
"""
Extraction Complète de la CAN 2025 depuis FotMob (League ID = 289)
URL cible : https://www.fotmob.com/fr/leagues/289/overview/africa-cup-nations
Fichier   : scripts/04_scrape_fotmob_can2025.py

Ce script utilise une double stratégie robuste :
1. Interrogation de l'API JSON interne de FotMob (/api/leagues?id=289)
2. Extraction automatique du bloc Next.js (<script id="__NEXT_DATA__">) depuis la page HTML
   https://www.fotmob.com/fr/leagues/289/overview/africa-cup-nations
3. Téléchargement des sous-fichiers JSON de statistiques détaillées (Joueurs & Équipes)
4. Export en CSV dans data/raw/ et sauvegarde dans la base SQLite data/can2025.db
"""

import os
import re
import sys
import json
import sqlite3
import urllib.request
import urllib.parse
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
DB_PATH = os.path.join(BASE_DIR, "data", "can2025.db")
os.makedirs(RAW_DIR, exist_ok=True)

FOTMOB_OVERVIEW_URL = "https://www.fotmob.com/fr/leagues/289/overview/africa-cup-nations"
FOTMOB_API_URL = "https://www.fotmob.com/api/leagues?id=289"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.fotmob.com/fr/leagues/289/overview/africa-cup-nations",
}


def fetch_url_text(url):
    """Télécharge le contenu texte (HTML ou JSON) d'une URL FotMob."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def get_fotmob_league_payload():
    """
    Récupère les données complètes de la ligue 289 (Africa Cup of Nations)
    soit via l'API directe, soit via la balise <script id="__NEXT_DATA__"> de la page HTML.
    """
    # Méthode 1 : Extraction depuis la page HTML officielle demandée (__NEXT_DATA__)
    print(f"🌐 1. Connexion à la page : {FOTMOB_OVERVIEW_URL}")
    try:
        html = fetch_url_text(FOTMOB_OVERVIEW_URL)
        match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>',
            html,
            re.DOTALL
        )
        if match:
            next_data = json.loads(match.group(1))
            page_props = next_data.get("props", {}).get("pageProps", {})
            # Dans FotMob Next.js, les données de la ligue sont soit directement dans pageProps,
            # soit dans pageProps["fallback"] / pageProps["initialState"]
            if "matches" in page_props or "table" in page_props or "details" in page_props:
                print("✅ Données extraites avec succès depuis le bloc __NEXT_DATA__ (pageProps) !")
                return page_props
            fallback = page_props.get("fallback", {})
            for k, val in fallback.items():
                if isinstance(val, dict) and ("matches" in val or "table" in val or "details" in val):
                    print(f"✅ Données extraites avec succès depuis __NEXT_DATA__ (fallback['{k}']) !")
                    return val
    except Exception as e:
        print(f"ℹ️ Passage à la méthode API directe ({e})")

    # Méthode 2 : Interrogation de l'endpoint JSON /api/leagues?id=289
    print(f"🌐 2. Interrogation de l'API FotMob : {FOTMOB_API_URL}")
    try:
        raw_json = fetch_url_text(FOTMOB_API_URL)
        data = json.loads(raw_json)
        print("✅ Données extraites avec succès depuis /api/leagues?id=289 !")
        return data
    except Exception as e:
        print(f"⚠️ Erreur lors de l'accès à l'API FotMob : {e}")
        return None


def parse_matches(payload):
    """Extrait tous les matchs de la CAN depuis le JSON FotMob."""
    matches_root = payload.get("matches", {})
    all_matches = (
        matches_root.get("allMatches")
        or matches_root.get("data", {}).get("allMatches")
        or payload.get("fixtures", {}).get("allMatches")
        or []
    )

    rows = []
    for m in all_matches:
        home = m.get("home", {})
        away = m.get("away", {})
        status = m.get("status", {})
        score_str = status.get("scoreStr", "")
        reason = status.get("reason", {}).get("short", "")

        rows.append({
            "fotmob_match_id": m.get("id"),
            "round": m.get("roundName") or m.get("round"),
            "date_utc": status.get("utcTime"),
            "home_team_id": home.get("id"),
            "home_team": home.get("name"),
            "away_team_id": away.get("id"),
            "away_team": away.get("name"),
            "home_score": home.get("score"),
            "away_score": away.get("score"),
            "score_str": score_str,
            "status_note": reason,
            "finished": status.get("finished"),
            "cancelled": status.get("cancelled"),
            "match_url": "https://www.fotmob.com" + str(m.get("pageUrl", ""))
        })

    return pd.DataFrame(rows)


def parse_standings(payload):
    """Extrait le classement des 6 groupes (Groupes A à F) depuis le JSON FotMob."""
    table_list = payload.get("table", [])
    rows = []

    for tbl_block in table_list:
        data = tbl_block.get("data", tbl_block)
        # Tournoi à plusieurs groupes (tables list)
        tables = data.get("tables", [data])
        for grp in tables:
            group_name = grp.get("leagueName") or grp.get("GroupName") or "Groupe"
            for team in grp.get("table", {}).get("all", []):
                scores_str = str(team.get("scoresStr", "0-0"))
                gf, ga = (scores_str.split("-") + ["0", "0"])[:2]
                rows.append({
                    "group_name": group_name,
                    "rank": team.get("idx"),
                    "team_id": team.get("id"),
                    "team_name": team.get("name"),
                    "played": team.get("played"),
                    "wins": team.get("wins"),
                    "draws": team.get("draws"),
                    "losses": team.get("losses"),
                    "goals_for": int(gf.strip()) if gf.strip().isdigit() else 0,
                    "goals_against": int(ga.strip()) if ga.strip().isdigit() else 0,
                    "goal_diff": team.get("goalConDiff"),
                    "points": team.get("pts"),
                })

    return pd.DataFrame(rows)


def parse_stats_categories(payload, kind="players"):
    """
    Extrait les statistiques de joueurs (buts, passes D, notes FotMob, xG...)
    ou d'équipes depuis la section 'stats' du JSON FotMob.
    """
    stats_root = payload.get("stats", {})
    categories = stats_root.get(kind, [])
    rows = []

    for cat in categories:
        cat_name = cat.get("header") or cat.get("name") or cat.get("title")
        fetch_url = cat.get("fetchAllUrl")

        # 1. Récupérer le Top 3 directement présent dans l'aperçu
        top_three = cat.get("topThree", [])
        for item in top_three:
            rows.append({
                "category": cat_name,
                "participant_id": item.get("id"),
                "name": item.get("name"),
                "team_id": item.get("teamId"),
                "team_name": item.get("teamName"),
                "stat_value": item.get("value"),
                "rank": item.get("rank"),
                "source_url": fetch_url
            })

        # 2. Si une URL JSON complète (fetchAllUrl) est fournie, tenter de récupérer toute la liste
        if fetch_url and fetch_url.startswith("http"):
            try:
                sub_json = json.loads(fetch_url_text(fetch_url))
                top_lists = sub_json.get("TopLists", [])
                for tl in top_lists:
                    for item in tl.get("StatList", []):
                        rows.append({
                            "category": cat_name,
                            "participant_id": item.get("ParticiantId") or item.get("ParticipantId"),
                            "name": item.get("ParticipantName"),
                            "team_id": item.get("TeamId"),
                            "team_name": item.get("TeamName"),
                            "stat_value": item.get("StatValue"),
                            "rank": item.get("Rank"),
                            "source_url": fetch_url
                        })
            except Exception:
                pass

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["category", "name", "team_name"], keep="last")
    return df


def main():
    print("=========================================================================")
    print("🦁 EXTRACTION COMPLÈTE FOTMOB — CAN 2025 (LEAGUE ID = 289)")
    print("=========================================================================\n")

    payload = get_fotmob_league_payload()
    if not payload:
        print("❌ Impossible de récupérer le payload FotMob.")
        return

    # Sauvegarde du JSON brut complet pour archivage et exploration
    raw_json_path = os.path.join(RAW_DIR, "fotmob_can2025_raw.json")
    try:
        with open(raw_json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"💾 JSON brut complet sauvegardé : {raw_json_path}")
    except Exception as e:
        print(f"⚠️ Impossible d'écrire le JSON brut : {e}")

    details = payload.get("details", {})
    print(f"📌 Compétition : {details.get('name', 'Africa Cup of Nations')} | Saison : {details.get('selectedSeason', '2025')}")

    conn = sqlite3.connect(DB_PATH)

    # 1. Extraction des Matchs
    df_matches = parse_matches(payload)
    if not df_matches.empty:
        csv_m = os.path.join(RAW_DIR, "fotmob_matches_can2025.csv")
        df_matches.to_csv(csv_m, index=False, encoding="utf-8")
        df_matches.to_sql("fotmob_matches", conn, if_exists="replace", index=False)
        print(f"✅ Matchs extraits : {len(df_matches)} matchs -> {csv_m}")
        print(df_matches[["date_utc", "round", "home_team", "score_str", "away_team"]].tail(8).to_string(index=False))
    else:
        print("ℹ️ Aucun match trouvé dans la clé 'matches' du payload.")

    # 2. Extraction des Classements des Groupes (Standings)
    df_standings = parse_standings(payload)
    if not df_standings.empty:
        csv_s = os.path.join(RAW_DIR, "fotmob_standings_can2025.csv")
        df_standings.to_csv(csv_s, index=False, encoding="utf-8")
        df_standings.to_sql("fotmob_standings", conn, if_exists="replace", index=False)
        print(f"\n✅ Classements des groupes extraits : {len(df_standings)} équipes -> {csv_s}")
        print(df_standings.head(8).to_string(index=False))

    # 3. Extraction des Statistiques Joueurs (Top Buteurs, Passes D, Notes FotMob, xG...)
    df_pstats = parse_stats_categories(payload, kind="players")
    if not df_pstats.empty:
        csv_p = os.path.join(RAW_DIR, "fotmob_player_stats_can2025.csv")
        df_pstats.to_csv(csv_p, index=False, encoding="utf-8")
        df_pstats.to_sql("fotmob_player_stats", conn, if_exists="replace", index=False)
        print(f"\n✅ Statistiques Joueurs extraites : {len(df_pstats)} entrées -> {csv_p}")
        print(df_pstats.head(10).to_string(index=False))

    # 4. Extraction des Statistiques Équipes
    df_tstats = parse_stats_categories(payload, kind="teams")
    if not df_tstats.empty:
        csv_t = os.path.join(RAW_DIR, "fotmob_team_stats_can2025.csv")
        df_tstats.to_csv(csv_t, index=False, encoding="utf-8")
        df_tstats.to_sql("fotmob_team_stats", conn, if_exists="replace", index=False)
        print(f"\n✅ Statistiques Équipes extraites : {len(df_tstats)} entrées -> {csv_t}")

    conn.close()
    print("\n🎉 Extraction FotMob terminée et synchronisée dans data/can2025.db !")


if __name__ == "__main__":
    main()
