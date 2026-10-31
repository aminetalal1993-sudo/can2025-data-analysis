# 📊 Guide Étape par Étape : Volet Excel (Audit, Nettoyage & Tableaux Croisés Dynamiques)

Ce guide vous explique comment réaliser la **partie Excel** de votre projet portfolio à partir des fichiers du dossier `data/raw/` et `data/processed/`.

---

## 1. Exercice de Data Cleaning dans Excel (à mentionner en entretien !)

Ouvrez `data/raw/teams_can2025.csv` et `data/raw/matches_can2025.csv` dans Excel :
1. **Supprimer les espaces inutiles** :
   * La cellule `Maroc` contient des espaces avant/après (`" Maroc "`).
   * Utilisez la formule `=SUPPRESPACE(B2)` (ou `=TRIM(B2)` en anglais) pour nettoyer les noms d'équipes.
2. **Supprimer les doublons** :
   * L'équipe des *Comores* apparaît 2 fois dans `teams_can2025.csv`.
   * Allez dans l'onglet **Données > Supprimer les doublons** en cochant la colonne `team_id`.
3. **Gérer les valeurs manquantes** :
   * Dans `matches_can2025.csv`, le match `M12` à Marrakech n'a pas d'affluence (`attendance` vide).
   * Remplacez la cellule vide par la moyenne ou médiane des matchs joués à Marrakech avec `=MOYENNE.SI(Q:Q; "Marrakech"; R:R)`.

---

## 2. Enrichissement avec RECHERCHEX (XLOOKUP)

Dans la feuille `matches_can2025_clean.csv`, ajoutez une colonne `Nom_Equipe_Domicile` :
```excel
=RECHERCHEX(E2; teams_can2025_clean!A:A; teams_can2025_clean!B:B; "Inconnu")
```

---

## 3. Les 3 Tableaux Croisés Dynamiques (TCD) à créer pour votre Dashboard Excel

1. **TCD 1 — Affluence & Buts par Ville Hôte au Maroc** :
   * *Lignes* : `host_city` (Rabat, Tanger, Casablanca, Agadir, Marrakech, Fès)
   * *Valeurs* : Somme de `total_goals`, Moyenne de `attendance`
2. **TCD 2 — Top Buteurs et Passeurs par Poste** (depuis `players_can2025_clean.csv`) :
   * *Filtre (Segment / Slicer)* : `team_name` (Sélectionnez **Maroc** pour analyser les Lions de l'Atlas !)
   * *Lignes* : `player_name`
   * *Valeurs* : Somme de `goals`, Somme de `assists`, Moyenne de `rating`
3. **TCD 3 — Évolution Historique des Buts par Décennie** (depuis `historical_afcon_clean.csv`).
