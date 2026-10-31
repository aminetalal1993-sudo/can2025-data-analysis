# -*- coding: utf-8 -*-
"""
Application Interactive de Data Analyse & Scouting : CAN 2025 (Maroc)
Intègre les données officielles + l'extraction granulaire FotMob (1 026 tirs, 710 événements, 2 445 prestations joueurs)
Lancez avec : python -m streamlit run app/streamlit_app.py
"""

import os
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="CAN 2025 Maroc - Data Analyse, Shotmap & Match Center FotMob",
    page_icon="🏆",
    layout="wide"
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "can2025.db")


@st.cache_data
def load_all_data(db_mtime):
    conn = sqlite3.connect(DB_PATH)
    hist = pd.read_sql_query("SELECT * FROM historical_afcon ORDER BY year", conn)
    teams = pd.read_sql_query("SELECT * FROM teams", conn)
    matches = pd.read_sql_query("SELECT * FROM matches", conn)
    players = pd.read_sql_query("SELECT * FROM players", conn)

    # Tables FotMob extraites
    def safe_read_table(tname):
        try:
            return pd.read_sql_query(f"SELECT * FROM {tname}", conn)
        except Exception:
            return pd.DataFrame()

    fm_standings = safe_read_table("fotmob_standings")
    fm_pstats = safe_read_table("fotmob_player_stats")
    fm_meta = safe_read_table("fotmob_matches_metadata")
    fm_mstats = safe_read_table("fotmob_match_stats")
    fm_events = safe_read_table("fotmob_match_events")
    fm_shots = safe_read_table("fotmob_shotmap")
    fm_pmatch = safe_read_table("fotmob_player_match_stats")

    conn.close()

    # Associer le nom de l'équipe aux tirs FotMob via team_id
    if not fm_shots.empty and not fm_standings.empty:
        tid_map = dict(zip(fm_standings["team_id"].astype(str), fm_standings["team_name"]))
        fm_shots["team_name"] = fm_shots["team_id"].astype(str).map(tid_map).fillna("Autre")

    return hist, teams, matches, players, fm_standings, fm_pstats, fm_meta, fm_mstats, fm_events, fm_shots, fm_pmatch


db_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else 0
(
    df_hist, df_teams, df_matches, df_players,
    df_fm_standings, df_fm_pstats, df_fm_meta,
    df_fm_mstats, df_fm_events, df_fm_shots, df_fm_pmatch
) = load_all_data(db_mtime)


def draw_half_pitch_shotmap(df_s, title="Carte des Tirs (Shotmap FotMob)"):
    """Dessine un demi-terrain de football réglementaire (dimensions Opta/FotMob 105x68) avec les tirs."""
    fig = go.Figure()

    # Couleur de fond terrain et lignes blanches (demi-terrain offensif : x de 52.5 à 106, y de -2 à 70)
    pitch_shapes = [
        # Pelouse
        dict(type="rect", x0=52.5, y0=0, x1=105, y1=68, line=dict(color="white", width=2), fillcolor="#1e7b34", layer="below"),
        # Grande surface de réparation (16.5m : x de 88.5 à 105, y de 13.84 à 54.16)
        dict(type="rect", x0=88.5, y0=13.84, x1=105, y1=54.16, line=dict(color="white", width=2), fillcolor="rgba(0,0,0,0)", layer="below"),
        # Surface de but (5.5m : x de 99.5 à 105, y de 24.84 à 43.16)
        dict(type="rect", x0=99.5, y0=24.84, x1=105, y1=43.16, line=dict(color="white", width=2), fillcolor="rgba(0,0,0,0)", layer="below"),
        # Cages du but (y de 30.34 à 37.66)
        dict(type="rect", x0=105, y0=30.34, x1=106.2, y1=37.66, line=dict(color="#f1c40f", width=3), fillcolor="rgba(255,255,255,0.25)", layer="below"),
        # Point de penalty (x=94, y=34)
        dict(type="circle", x0=93.6, y0=33.6, x1=94.4, y1=34.4, line=dict(color="white", width=2), fillcolor="white", layer="below"),
    ]

    color_map = {
        "Goal": "#f1c40f",          # Or vif pour les buts
        "AttemptSaved": "#3498db",  # Bleu pour les tirs arrêtés/bloqués
        "Miss": "#e74c3c",          # Rouge pour les tirs hors cadre
        "Post": "#9b59b6"           # Violet pour les poteaux
    }
    symbol_map = {
        "Goal": "star",
        "AttemptSaved": "circle",
        "Miss": "x",
        "Post": "diamond"
    }

    for ev_type, group in df_s.groupby("event_type"):
        xg_vals = pd.to_numeric(group["xg"], errors="coerce").fillna(0.05)
        marker_sizes = (xg_vals * 38 + 9).clip(9, 32)
        fig.add_trace(go.Scatter(
            x=group["x"],
            y=group["y"],
            mode="markers",
            name=f"{ev_type} ({len(group)})",
            marker=dict(
                size=marker_sizes,
                color=color_map.get(ev_type, "#ecf0f1"),
                symbol=symbol_map.get(ev_type, "circle"),
                line=dict(width=1.2, color="black"),
                opacity=0.9
            ),
            customdata=group[["player_name", "team_name", "minute", "xg", "xgot", "shot_type", "situation", "home_team", "away_team"]],
            hovertemplate=(
                "<b>%{customdata[0]}</b> (%{customdata[1]}) — %{customdata[2]}'<br>"
                "Match : %{customdata[7]} vs %{customdata[8]}<br>"
                "Résultat : <b>" + str(ev_type) + "</b> | Type : %{customdata[5]} (%{customdata[6]})<br>"
                "xG : <b>%{customdata[3]:.2f}</b> | xGOT : %{customdata[4]:.2f}<extra></extra>"
            )
        ))

    fig.update_layout(
        title=title,
        shapes=pitch_shapes,
        xaxis=dict(range=[52, 107], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[-2, 70], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
        plot_bgcolor="#145a23",
        height=540,
        margin=dict(l=10, r=10, t=45, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1)
    )
    return fig


# ==============================================================================
# EN-TÊTE GLOBAL & KPIS OFFICIELS DU TOURNOI (CAN 2025 MAROC)
# ==============================================================================
st.title("🏆 CAN 2025 (Maroc) — Plateforme Data Analyse, Shotmap & Match Center FotMob")
st.markdown(
    "**Données Officielles & Extraction Temps Réel FotMob** | **52 matchs**, **1 026 tirs géolocalisés (xG)**, "
    "**710 événements minute par minute** et **2 445 prestations individuelles de joueurs**."
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Matchs & Tirs FotMob", f"52 matchs | {len(df_fm_shots)} tirs", f"{len(df_fm_pmatch)} fiches joueurs")
c2.metric("Buts Marqués", int(df_matches["total_goals"].sum()), f"Moyenne : {df_matches['total_goals'].mean():.2f} / match")
c3.metric("Soulier d'Or (Buteur)", "Brahim Díaz 🇲🇦", "5 buts (Osimhen & Salah : 4)")
c4.metric("Meilleur Joueur & Gardien", "Mané 🇸🇳 / Bounou 🇲🇦", "Lookman 🇳🇬 : 4 passes D")
c5.metric("Champion CAN 2025", "🇲🇦 Maroc (3-0 CAF)", "Finaliste : Sénégal 🇸🇳")

st.divider()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🎯 1. Diagnostic par Équipe (24 Nations)",
    "🥅 2. Shotmap Interactive FotMob (1 026 Tirs)",
    "🏟️ 3. Feuille de Match FotMob (Match Center)",
    "📊 4. Bilan des 24 Équipes & Groupes",
    "🔍 5. Scouting & Stats Joueurs FotMob",
    "📜 6. Historique CAN (1957-2025)"
])

# ==============================================================================
# ONGLET 1 : DIAGNOSTIC TACTIQUE & PARCOURS DE CHAQUE ÉQUIPE (LISTE DÉROULANTE)
# ==============================================================================
with tab1:
    st.subheader("🎯 Diagnostic Tactique & Parcours Officiel par Équipe Nationale")

    teams_sorted = df_teams.sort_values(["group_name", "fifa_rank"]).copy()
    team_options = [
        f"{r['team_name']} ({r['team_id']}) — {r['group_name']} | {r['final_stage_2025']}"
        for _, r in teams_sorted.iterrows()
    ]
    default_idx = next((i for i, opt in enumerate(team_options) if "(MAR)" in opt), 0)

    col_sel, col_info = st.columns([1.35, 2])
    with col_sel:
        selected_label = st.selectbox(
            "🔽 Choisissez une équipe parmi les 24 nations qualifiées :",
            options=team_options,
            index=default_idx
        )
    selected_team_id = selected_label.split("(")[1].split(")")[0]
    team_info = df_teams[df_teams["team_id"] == selected_team_id].iloc[0]

    with col_info:
        st.info(
            f"**{team_info['team_name']}** | **Groupe :** {team_info['group_name']} | "
            f"**Parcours réel :** *{team_info['final_stage_2025']}* | "
            f"**Style Tactique :** *{team_info['coach_style']}* | "
            f"**Titres CAN avant 2025 :** {team_info['previous_titles']}"
        )

    raw_tm = df_matches[
        (df_matches["home_team_id"] == selected_team_id) |
        (df_matches["away_team_id"] == selected_team_id)
    ].sort_values("match_date").copy()

    team_name_map = dict(zip(df_teams["team_id"], df_teams["team_name"]))

    match_records = []
    wins, draws, losses = 0, 0, 0
    for _, m in raw_tm.iterrows():
        is_home = (m["home_team_id"] == selected_team_id)
        opp_id = m["away_team_id"] if is_home else m["home_team_id"]
        opp_name = team_name_map.get(opp_id, opp_id)
        gf = int(m["home_goals"] if is_home else m["away_goals"])
        ga = int(m["away_goals"] if is_home else m["home_goals"])
        xgf = float(m["home_xg"] if is_home else m["away_xg"])
        xga = float(m["away_xg"] if is_home else m["home_xg"])
        poss = int(m["home_possession"] if is_home else m["away_possession"])
        shots = int(m["home_shots"] if is_home else m["away_shots"])
        sot = int(m["home_shots_on_target"] if is_home else m["away_shots_on_target"])
        stage_str = m["stage"]

        if gf > ga:
            res_label = "✅ Victoire"
            wins += 1
        elif gf == ga:
            draws += 1
            if f"tab {selected_team_id}" in stage_str:
                res_label = "✅ Qualifié (t.a.b.)"
            elif "tab" in stage_str:
                res_label = "❌ Éliminé (t.a.b.)"
            else:
                res_label = "🤝 Match Nul"
        else:
            losses += 1
            res_label = "❌ Défaite"

        match_records.append({
            "Match ID": m["match_id"],
            "Date": m["match_date"],
            "Tour": stage_str,
            "Adversaire": opp_name,
            "Résultat": res_label,
            "Score": f"{gf} - {ga}",
            "Buts Pour": gf,
            "Buts Contre": ga,
            "xG Créés": round(xgf, 2),
            "xG Concédés": round(xga, 2),
            "Possession (%)": poss,
            "Tirs (Cadrés)": f"{shots} ({sot})",
            "Ville Hôte": m["host_city"],
            "Affluence": int(m["attendance"]),
            "Label_Graph": f"vs {opp_name} ({gf}-{ga})"
        })

    df_tm_view = pd.DataFrame(match_records)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Parcours CAN 2025", team_info["final_stage_2025"])
    k2.metric("Bilan", f"{wins}V - {draws}N - {losses}D", f"{len(df_tm_view)} matchs joués")
    total_gf = int(df_tm_view["Buts Pour"].sum())
    total_ga = int(df_tm_view["Buts Contre"].sum())
    k3.metric("Buts Marqués / Encaissés", f"{total_gf} BP / {total_ga} BC", f"Diff : {total_gf - total_ga:+d}")
    tot_xgf = df_tm_view["xG Créés"].sum()
    tot_xga = df_tm_view["xG Concédés"].sum()
    k4.metric("Total Expected Goals (xG)", f"{tot_xgf:.2f} xG", f"xG Concédés : {tot_xga:.2f}")
    k5.metric("Possession Moyenne", f"{df_tm_view['Possession (%)'].mean():.1f}%")
    k6.metric("Classement FIFA & Valeur", f"#{team_info['fifa_rank']} FIFA", f"{team_info['market_value_m_eur']:.1f} M€")

    g_col1, g_col2 = st.columns([1.15, 1])

    with g_col1:
        fig_xg = go.Figure()
        fig_xg.add_trace(go.Bar(
            x=df_tm_view["Label_Graph"],
            y=df_tm_view["xG Créés"],
            name=f"xG Créés ({team_info['team_name']})",
            marker_color="#c1272d",
            text=df_tm_view["xG Créés"],
            textposition="auto"
        ))
        fig_xg.add_trace(go.Bar(
            x=df_tm_view["Label_Graph"],
            y=df_tm_view["xG Concédés"],
            name="xG Concédés (Adversaire)",
            marker_color="#7f8c8d",
            text=df_tm_view["xG Concédés"],
            textposition="auto"
        ))
        fig_xg.update_layout(
            barmode="group",
            title=f"Parcours Match par Match : xG de {team_info['team_name']} vs Adversaires",
            xaxis_title="Matchs disputés dans le tournoi",
            yaxis_title="Expected Goals (xG)"
        )
        st.plotly_chart(fig_xg, use_container_width=True)

    with g_col2:
        team_players = df_players[df_players["team_id"] == selected_team_id].sort_values(
            ["goal_contributions", "rating"], ascending=False
        )
        fig_pl = px.bar(
            team_players.head(10),
            x="rating",
            y="player_name",
            color="position",
            orientation="h",
            hover_data=["club", "goals", "assists", "key_passes", "duels_won_pct"],
            title=f"Joueurs Clés de {team_info['team_name']} (Classés par Note & Impact)",
            labels={"rating": "Note Moyenne (/10)", "player_name": "Joueur", "position": "Poste"}
        )
        fig_pl.update_layout(yaxis={"categoryorder": "total ascending"}, xaxis_range=[6.0, 9.0])
        st.plotly_chart(fig_pl, use_container_width=True)

    st.markdown(f"#### 📅 Calendrier & Résultats Officiels — {team_info['team_name']}")
    st.dataframe(
        df_tm_view[[
            "Date", "Tour", "Adversaire", "Résultat", "Score",
            "xG Créés", "xG Concédés", "Possession (%)", "Tirs (Cadrés)", "Ville Hôte", "Affluence"
        ]],
        use_container_width=True,
        hide_index=True
    )

    st.markdown(f"#### 👥 Statistiques Individuelles des Joueurs — {team_info['team_name']}")
    st.dataframe(
        team_players[[
            "player_name", "position", "age", "club", "market_value_m_eur",
            "matches_played", "minutes_played", "goals", "xg", "assists",
            "key_passes", "progressive_carries", "tackles_won", "interceptions",
            "duels_won_pct", "clean_sheets", "rating"
        ]].sort_values("rating", ascending=False),
        use_container_width=True,
        hide_index=True
    )

# ==============================================================================
# ONGLET 2 : CARTE INTERACTIVE DES TIRS (SHOTMAP FOTMOB - 1 026 TIRS RÉELS)
# ==============================================================================
with tab2:
    st.subheader("🥅 Carte Interactive des Tirs (Shotmap Officielle FotMob — 1 026 Tirs)")
    if df_fm_shots.empty:
        st.warning("Aucune donnée Shotmap FotMob trouvée.")
    else:
        sc1, sc2, sc3, sc4 = st.columns(4)
        all_shot_teams = ["Toutes les équipes"] + sorted(df_fm_shots["team_name"].dropna().unique().tolist())
        default_shot_team = all_shot_teams.index("Morocco") if "Morocco" in all_shot_teams else 0

        sel_shot_team = sc1.selectbox("Filtrer par Équipe (FotMob) :", options=all_shot_teams, index=default_shot_team)

        sub_shots = df_fm_shots.copy()
        if sel_shot_team != "Toutes les équipes":
            sub_shots = sub_shots[sub_shots["team_name"] == sel_shot_team]

        all_shot_players = ["Tous les joueurs"] + sorted(sub_shots["player_name"].dropna().unique().tolist())
        sel_shot_player = sc2.selectbox("Filtrer par Joueur :", options=all_shot_players, index=0)
        if sel_shot_player != "Tous les joueurs":
            sub_shots = sub_shots[sub_shots["player_name"] == sel_shot_player]

        ev_types = sorted(df_fm_shots["event_type"].dropna().unique().tolist())
        sel_ev_types = sc3.multiselect("Résultat du tir :", options=ev_types, default=ev_types)
        if sel_ev_types:
            sub_shots = sub_shots[sub_shots["event_type"].isin(sel_ev_types)]

        sh_types = sorted(df_fm_shots["shot_type"].dropna().unique().tolist())
        sel_sh_types = sc4.multiselect("Partie du corps :", options=sh_types, default=sh_types)
        if sel_sh_types:
            sub_shots = sub_shots[sub_shots["shot_type"].isin(sel_sh_types)]

        # KPIs des tirs filtrés
        sk1, sk2, sk3, sk4, sk5 = st.columns(5)
        n_shots = len(sub_shots)
        n_goals = int((sub_shots["event_type"] == "Goal").sum())
        tot_xg_s = pd.to_numeric(sub_shots["xg"], errors="coerce").sum()
        tot_xgot_s = pd.to_numeric(sub_shots["xgot"], errors="coerce").sum()
        conv_rate = (100.0 * n_goals / n_shots) if n_shots > 0 else 0.0

        sk1.metric("Tirs Sélectionnés", n_shots)
        sk2.metric("Buts Marqués (Goals)", n_goals, f"Conversion : {conv_rate:.1f}%")
        sk3.metric("Expected Goals Cumulés (xG)", f"{tot_xg_s:.2f}")
        sk4.metric("xG Cadrés (xGOT)", f"{tot_xgot_s:.2f}")
        sk5.metric("xG Moyen / Tir", f"{(tot_xg_s / n_shots):.3f}" if n_shots > 0 else "0.000")

        col_pitch, col_table = st.columns([1.35, 1])
        with col_pitch:
            pitch_fig = draw_half_pitch_shotmap(
                sub_shots,
                title=f"Shotmap sur Demi-Terrain — {sel_shot_team} ({sel_shot_player})"
            )
            st.plotly_chart(pitch_fig, use_container_width=True)

        with col_table:
            st.markdown("#### 📋 Détail des Tirs Sélectionnés (Classés par xG)")
            st.dataframe(
                sub_shots[[
                    "match_date", "player_name", "team_name", "minute",
                    "event_type", "xg", "xgot", "shot_type", "situation", "home_team", "away_team"
                ]].sort_values("xg", ascending=False),
                use_container_width=True,
                hide_index=True,
                height=490
            )

# ==============================================================================
# ONGLET 3 : EXPLORATEUR DE FEUILLE DE MATCH FOTMOB (MATCH CENTER)
# ==============================================================================
with tab3:
    st.subheader("🏟️ Explorateur de Feuille de Match FotMob (Match Center — 52 Matchs)")
    if df_fm_meta.empty:
        st.warning("Aucune métadonnée de match FotMob trouvée.")
    else:
        meta_sorted = df_fm_meta.sort_values("match_date", ascending=False).copy()
        meta_sorted["label"] = (
            meta_sorted["match_date"].astype(str) + " | " +
            meta_sorted["home_team"].astype(str) + " " +
            meta_sorted["score_str"].astype(str) + " " +
            meta_sorted["away_team"].astype(str) + " (" +
            meta_sorted["stadium_name"].fillna("Stade Maroc").astype(str) + ") [ID:" +
            meta_sorted["fotmob_match_id"].astype(str) + "]"
        )
        # Par défaut sur un match du Maroc (ex: Finale ou Maroc vs Comores)
        mar_match_idx = next((i for i, lbl in enumerate(meta_sorted["label"]) if "Morocco" in lbl), 0)

        sel_match_lbl = st.selectbox(
            "🔽 Sélectionnez l'un des 52 matchs de la CAN 2025 pour inspecter sa Feuille de Match :",
            options=meta_sorted["label"].tolist(),
            index=mar_match_idx
        )
        sel_mid = sel_match_lbl.split("[ID:")[1].split("]")[0]
        m_row = meta_sorted[meta_sorted["fotmob_match_id"].astype(str) == str(sel_mid)].iloc[0]

        # Bandeau d'informations officielles du match
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        mc1.metric("Affiche & Score", f"{m_row['home_team']} {m_row['score_str']} {m_row['away_team']}")
        mc2.metric("Stade & Ville", str(m_row["stadium_name"] or "Maroc"), str(m_row["city"] or ""))
        att_val = f"{int(float(m_row['attendance'])):,}".replace(",", " ") if pd.notna(m_row["attendance"]) and str(m_row["attendance"]) != "" else "N/A"
        mc3.metric("Affluence Officielle", f"{att_val} spectateurs")
        mc4.metric("Arbitre Officiel", str(m_row["referee"] or "CAF"))
        mc5.metric("🌟 Homme du Match (FotMob)", str(m_row["player_of_the_match"] or "N/A"))

        col_ev, col_st = st.columns([1.1, 1.1])

        with col_ev:
            st.markdown("#### ⏱️ Chronologie Minute par Minute (Buts, Cartons, Changements)")
            m_events = df_fm_events[df_fm_events["fotmob_match_id"].astype(str) == str(sel_mid)].sort_values("minute")
            if not m_events.empty:
                st.dataframe(
                    m_events[["minute", "team_side", "event_type", "player_name", "card_type", "detail"]],
                    use_container_width=True,
                    hide_index=True,
                    height=360
                )
            else:
                st.info("Aucun événement détaillé enregistré pour ce match.")

        with col_st:
            st.markdown("#### 📊 Face-à-Face Statistique (FotMob Match Stats)")
            m_stats = df_fm_mstats[df_fm_mstats["fotmob_match_id"].astype(str) == str(sel_mid)]
            if not m_stats.empty:
                st.dataframe(
                    m_stats[["stat_group", "stat_name", "home_value", "away_value"]].rename(
                        columns={
                            "stat_group": "Catégorie",
                            "stat_name": "Indicateur",
                            "home_value": str(m_row["home_team"]),
                            "away_value": str(m_row["away_team"])
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                    height=360
                )
            else:
                st.info("Statistiques collectives non disponibles pour ce match.")

        # Shotmap spécifique au match + Notes FotMob des 22 joueurs du match
        col_mshot, col_mp = st.columns([1.2, 1.1])
        with col_mshot:
            m_shots = df_fm_shots[df_fm_shots["fotmob_match_id"].astype(str) == str(sel_mid)]
            if not m_shots.empty:
                st.plotly_chart(
                    draw_half_pitch_shotmap(
                        m_shots,
                        title=f"Shotmap du Match : {m_row['home_team']} vs {m_row['away_team']} ({len(m_shots)} tirs)"
                    ),
                    use_container_width=True
                )
            else:
                st.info("Pas de Shotmap pour ce match.")

        with col_mp:
            st.markdown("#### 🌟 Notes FotMob & Prestations des Joueurs sur ce Match")
            m_players = df_fm_pmatch[df_fm_pmatch["fotmob_match_id"].astype(str) == str(sel_mid)].copy()
            if not m_players.empty:
                m_players["fotmob_rating_num"] = pd.to_numeric(m_players["fotmob_rating"], errors="coerce")
                m_players = m_players.sort_values("fotmob_rating_num", ascending=False)
                st.dataframe(
                    m_players[[
                        "player_name", "team_name", "fotmob_rating", "minutes_played",
                        "goals", "assists", "xg", "xa", "total_shots", "chances_created", "touches", "duels_won"
                    ]],
                    use_container_width=True,
                    hide_index=True,
                    height=490
                )
            else:
                st.info("Notes individuelles non disponibles pour ce match.")

# ==============================================================================
# ONGLET 4 : BILAN COMPARATIF DES 24 ÉQUIPES & GROUPES FOTMOB
# ==============================================================================
with tab4:
    st.subheader("📊 Comparaison Collective des 24 Sélections & Classements FotMob")
    fig_val = px.scatter(
        df_teams,
        x="fifa_rank",
        y="market_value_m_eur",
        color="final_stage_2025",
        size="market_value_m_eur",
        hover_name="team_name",
        text="team_name",
        title="Classement FIFA vs Valeur Marchande et Parcours Réel à la CAN 2025",
        labels={"fifa_rank": "Classement FIFA (plus petit = meilleur)", "market_value_m_eur": "Valeur Marchande (M€)"}
    )
    fig_val.update_traces(textposition="top center")
    st.plotly_chart(fig_val, use_container_width=True)

    if not df_fm_standings.empty:
        st.markdown("#### 🏆 Classements Officiels des Groupes extraits de FotMob")
        st.dataframe(df_fm_standings, use_container_width=True, hide_index=True)

# ==============================================================================
# ONGLET 5 : SCOUTING & CLASSEMENTS OFFICIELS FOTMOB (123 STATS JOUEURS)
# ==============================================================================
with tab5:
    st.subheader("🔍 Cellule de Recrutement & Top Performers FotMob")
    if not df_fm_pstats.empty:
        cats = df_fm_pstats["category"].unique().tolist()
        sel_cat = st.selectbox("Choisissez une catégorie statistique FotMob :", options=cats, index=0)
        sub_cat = df_fm_pstats[df_fm_pstats["category"] == sel_cat].sort_values("rank")
        fig_cat = px.bar(
            sub_cat.head(12),
            x="stat_value",
            y="name",
            color="team_name",
            orientation="h",
            title=f"Classement Officiel FotMob — {sel_cat}",
            labels={"stat_value": sel_cat, "name": "Joueur", "team_name": "Sélection"}
        )
        fig_cat.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_cat, use_container_width=True)

    st.markdown("#### 💎 Table Complète de Scouting (Valeur Marchande, Âge, Stats & Notes)")
    st.dataframe(df_players.sort_values(["goals", "assists", "rating"], ascending=False), use_container_width=True, hide_index=True)

# ==============================================================================
# ONGLET 6 : HISTORIQUE DE LA CAN (1957 - 2025)
# ==============================================================================
with tab6:
    st.subheader("📜 Évolution Historique de la CAN (1957 - 2025)")
    fig_h = px.line(
        df_hist,
        x="year",
        y="goals_per_match",
        markers=True,
        hover_data=["host_country", "winner", "avg_attendance"],
        title="Évolution de la Moyenne de Buts par Match de 1957 à 2025"
    )
    st.plotly_chart(fig_h, use_container_width=True)
    st.dataframe(df_hist.sort_values("year", ascending=False), use_container_width=True, hide_index=True)
