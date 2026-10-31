# -*- coding: utf-8 -*-
"""
Extraction Granulaire des 52 Matchs de la CAN 2025 depuis FotMob
Fichier : scripts/05_scrape_fotmob_match_details.py

À partir des 52 matchs extraits dans 'fotmob_matches_can2025.csv', ce script récupère
pour CHAQUE match (via le bloc __NEXT_DATA__ de la page du match ou /api/matchDetails) :
1. Les statistiques complètes du match (Possession, xG, Tirs, Grosses occasions, Passes, Duels...)
2. Les événements minute par minute (Buts, Passeurs, Cartons, Remplacements, Tirs au but)
3. La Shotmap complète (Chaque tir avec ses coordonnées X/Y sur le terrain, xG, xGOT, pied/tête)
4. Les compositions & notes individuelles des joueurs match par match
"""

import os
import re
import sys
import json
import sqlite3
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
DB_PATH = os.path.join(BASE_DIR, "data", "can2025.db")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
}


def fetch_single_match_payload(match_row):
    """
    Récupère le JSON détaillé d'un match FotMob à partir de son URL (via __NEXT_DATA__)
    ou de l'endpoint /api/matchDetails?matchId=...
    """
    match_id = str(match_row["fotmob_match_id"])
    raw_url = str(match_row["match_url"]).split("#")[0]
    # Ajouter ?id=match_id garantit que Next.js charge exactement ce match (et non un ancien H2H)
    page_url = f"{raw_url}?id={match_id}"

    # 1. Essai via la page HTML du match (__NEXT_DATA__)
    try:
        req = urllib.request.Request(page_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>',
            html,
            re.DOTALL
        )
        if m:
            next_data = json.loads(m.group(1))
            page_props = next_data.get("props", {}).get("pageProps", {})
            if "content" in page_props or "general" in page_props:
                return match_id, page_props
            fallback = page_props.get("fallback", {})
            for k, val in fallback.items():
                if isinstance(val, dict) and ("content" in val or "general" in val):
                    return match_id, val
    except Exception:
        pass

    # 2. Essai via l'API directe /api/matchDetails
    try:
        api_url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"
        req = urllib.request.Request(api_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            if "content" in data or "general" in data:
                return match_id, data
    except Exception:
        pass

    return match_id, None


def extract_from_match_payload(match_id, payload, meta_row):
    """Extrait les 4 listes (stats_equipes, evenements, tirs_shotmap, joueurs_match) d'un match."""
    general = payload.get("general") or {}
    header = payload.get("header") or {}
    content = payload.get("content") or {}

    home_team = meta_row["home_team"]
    away_team = meta_row["away_team"]
    round_name = meta_row["round"]
    match_date = str(meta_row["date_utc"])[:10]

    # Informations générales du match (Stade, Ville, Affluence, Arbitre)
    match_facts = content.get("matchFacts") or {}
    info_box = match_facts.get("infoBox") or {}
    stadium_info = info_box.get("Stadium") if isinstance(info_box.get("Stadium"), dict) else {}
    attendance = info_box.get("Attendance")
    referee_info = info_box.get("Referee") if isinstance(info_box.get("Referee"), dict) else {}
    potm_name = ((match_facts.get("playerOfTheMatch") or {}).get("name") or {})
    if isinstance(potm_name, dict):
        potm_full = potm_name.get("fullName")
    else:
        potm_full = str(potm_name) if potm_name else None

    meta_info = {
        "fotmob_match_id": match_id,
        "match_date": match_date,
        "round": round_name,
        "home_team": home_team,
        "away_team": away_team,
        "score_str": meta_row["score_str"],
        "stadium_name": (stadium_info or {}).get("name"),
        "city": (stadium_info or {}).get("city"),
        "attendance": attendance,
        "referee": (referee_info or {}).get("text"),
        "player_of_the_match": potm_full
    }

    # -------------------------------------------------------------------------
    # A. STATISTIQUES COLLECTIVES DU MATCH (content -> stats)
    # -------------------------------------------------------------------------
    stats_rows = []
    stats_root = content.get("stats") or {}
    periods = stats_root.get("Periods") or {}
    all_period = periods.get("All") or stats_root.get("Ede") or {}
    stat_groups = (all_period.get("stats") or []) if isinstance(all_period, dict) else []

    for grp in stat_groups:
        if not isinstance(grp, dict):
            continue
        grp_title = grp.get("title")
        for st_item in (grp.get("stats") or []):
            if not isinstance(st_item, dict) or st_item.get("type") == "title":
                continue
            vals = st_item.get("stats") or [None, None]
            if isinstance(vals, list) and len(vals) >= 2:
                stats_rows.append({
                    "fotmob_match_id": match_id,
                    "match_date": match_date,
                    "home_team": home_team,
                    "away_team": away_team,
                    "stat_group": grp_title,
                    "stat_name": st_item.get("title"),
                    "stat_key": st_item.get("key"),
                    "home_value": str(vals[0]),
                    "away_value": str(vals[1]),
                })

    # -------------------------------------------------------------------------
    # B. ÉVÉNEMENTS MINUTE PAR MINUTE (Buts, Cartons, Remplacements)
    # -------------------------------------------------------------------------
    event_rows = []
    events_list = ((match_facts.get("events") or {}).get("events")) or []
    for ev in events_list:
        if not isinstance(ev, dict):
            continue
        ev_type = ev.get("type")
        if ev_type not in ("Goal", "Card", "Substitution", "MissedPenalty"):
            continue
        is_home = ev.get("isHome")
        player_obj = ev.get("player") if isinstance(ev.get("player"), dict) else {}
        player_name = player_obj.get("name") or ev.get("nameStr")
        swap_list = ev.get("swap") if isinstance(ev.get("swap"), list) and len(ev.get("swap")) > 0 else []
        swap_name = swap_list[-1].get("name") if swap_list and isinstance(swap_list[-1], dict) else None
        assist_str = ev.get("assistStr") or swap_name or ev.get("assistInput") or ""
        new_score = ev.get("newScore") if isinstance(ev.get("newScore"), list) and len(ev.get("newScore")) >= 2 else [None, None]
        event_rows.append({
            "fotmob_match_id": match_id,
            "match_date": match_date,
            "home_team": home_team,
            "away_team": away_team,
            "team_side": home_team if is_home else away_team,
            "minute": ev.get("time"),
            "overload_minute": ev.get("overloadTime"),
            "event_type": ev_type,
            "card_type": ev.get("card"),
            "player_name": player_name,
            "detail": str(assist_str),
            "home_score_after": new_score[0],
            "away_score_after": new_score[1],
        })

    # -------------------------------------------------------------------------
    # C. SHOTMAP COMPLÈTE (Coordonnées X/Y des tirs, xG, xGOT, résultat)
    # -------------------------------------------------------------------------
    shot_rows = []
    shots_list = ((content.get("shotmap") or {}).get("shots")) or []
    for sh in shots_list:
        if not isinstance(sh, dict):
            continue
        shot_rows.append({
            "fotmob_match_id": match_id,
            "match_date": match_date,
            "home_team": home_team,
            "away_team": away_team,
            "team_id": sh.get("teamId"),
            "player_id": sh.get("playerId"),
            "player_name": sh.get("playerName"),
            "minute": sh.get("min"),
            "event_type": sh.get("eventType"),     # Goal, AttemptSaved, Miss, Post
            "situation": sh.get("situation"),       # RegularPlay, Penalty, SetPiece, FastBreak
            "shot_type": sh.get("shotType"),        # RightFoot, LeftFoot, Header
            "x": sh.get("x"),
            "y": sh.get("y"),
            "xg": sh.get("expectedGoals"),
            "xgot": sh.get("expectedGoalsOnTarget"),
            "is_on_target": sh.get("isOnTarget"),
            "is_blocked": sh.get("isBlocked"),
            "is_own_goal": sh.get("isOwnGoal"),
        })

    # -------------------------------------------------------------------------
    # D. STATISTIQUES INDIVIDUELLES DES JOUEURS SUR LE MATCH (playerStats)
    # -------------------------------------------------------------------------
    player_match_rows = []
    pstats_dict = content.get("playerStats") or {}
    if isinstance(pstats_dict, dict):
        for pid, pinfo in pstats_dict.items():
            if not isinstance(pinfo, dict):
                continue
            pname = pinfo.get("name")
            tname = pinfo.get("teamName")
            is_goalkeeper = pinfo.get("isGoalkeeper")

            flat_metrics = {}
            for section in (pinfo.get("stats") or []):
                if not isinstance(section, dict):
                    continue
                sec_stats = section.get("stats") or {}
                if isinstance(sec_stats, dict):
                    for s_label, s_obj in sec_stats.items():
                        if isinstance(s_obj, dict):
                            stat_inner = s_obj.get("stat") if isinstance(s_obj.get("stat"), dict) else {}
                            val = stat_inner.get("value")
                            flat_metrics[s_obj.get("key") or s_label] = val

            player_match_rows.append({
                "fotmob_match_id": match_id,
                "match_date": match_date,
                "player_id": pid,
                "player_name": pname,
                "team_name": tname,
                "is_goalkeeper": is_goalkeeper,
                "fotmob_rating": flat_metrics.get("rating_title"),
                "minutes_played": flat_metrics.get("minutes_played"),
                "goals": flat_metrics.get("goals"),
                "assists": flat_metrics.get("assists"),
                "xg": flat_metrics.get("expected_goals"),
                "xa": flat_metrics.get("expected_assists"),
                "total_shots": flat_metrics.get("total_shots"),
                "chances_created": flat_metrics.get("chances_created"),
                "touches": flat_metrics.get("touches"),
                "accurate_passes": flat_metrics.get("accurate_passes"),
                "tackles_succeeded": flat_metrics.get("Matchstats.headers.tackles"),
                "interceptions": flat_metrics.get("interceptions"),
                "duels_won": flat_metrics.get("duel_won"),
            })

    return meta_info, stats_rows, event_rows, shot_rows, player_match_rows


def main():
    print("=========================================================================")
    print("🏟️ EXTRACTION DÉTAILLÉE DES 52 MATCHS FOTMOB — CAN 2025")
    print("=========================================================================\n")

    matches_csv = os.path.join(RAW_DIR, "fotmob_matches_can2025.csv")
    if not os.path.exists(matches_csv):
        print("❌ Fichier fotmob_matches_can2025.csv introuvable. Lancez d'abord 04_scrape_fotmob_can2025.py")
        return

    df_matches = pd.read_csv(matches_csv)
    print(f"📋 {len(df_matches)} matchs à extraire en parallèle (ThreadPoolExecutor)...\n")

    all_meta = []
    all_stats = []
    all_events = []
    all_shots = []
    all_pstats = []

    rows_list = [r for _, r in df_matches.iterrows()]

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_row = {executor.submit(fetch_single_match_payload, r): r for r in rows_list}
        done_count = 0
        for future in as_completed(future_to_row):
            r = future_to_row[future]
            done_count += 1
            match_id, payload = future.result()
            if payload:
                meta, st_r, ev_r, sh_r, pl_r = extract_from_match_payload(match_id, payload, r)
                all_meta.append(meta)
                all_stats.extend(st_r)
                all_events.extend(ev_r)
                all_shots.extend(sh_r)
                all_pstats.extend(pl_r)
                print(f"  [{done_count:02d}/52] ✅ {r['home_team']} vs {r['away_team']} ({r['score_str']}) -> {len(sh_r)} tirs, {len(ev_r)} événements, {len(pl_r)} joueurs")
            else:
                print(f"  [{done_count:02d}/52] ⚠️ {r['home_team']} vs {r['away_team']} (payload non disponible)")

    conn = sqlite3.connect(DB_PATH)

    def save_table(records, csv_name, sql_name):
        if not records:
            return
        df = pd.DataFrame(records)
        cpath = os.path.join(RAW_DIR, csv_name)
        df.to_csv(cpath, index=False, encoding="utf-8")
        df.to_sql(sql_name, conn, if_exists="replace", index=False)
        print(f"💾 {sql_name:<30} : {len(df):>5} lignes -> {cpath}")

    print("\n=== BILAN DES FICHIERS GÉNÉRÉS & TABLES SQLITE ===")
    save_table(all_meta, "fotmob_matches_metadata.csv", "fotmob_matches_metadata")
    save_table(all_stats, "fotmob_match_stats_can2025.csv", "fotmob_match_stats")
    save_table(all_events, "fotmob_match_events_can2025.csv", "fotmob_match_events")
    save_table(all_shots, "fotmob_shotmap_can2025.csv", "fotmob_shotmap")
    save_table(all_pstats, "fotmob_player_match_stats.csv", "fotmob_player_match_stats")

    conn.close()
    print("\n🎉 Extraction granulaire des 52 matchs terminée avec succès !")


if __name__ == "__main__":
    main()
