"""
validate_dataset.py
-------------------
Script d'audit et de validation automatique de l'intégrité du dataset pour
'AI Fitness Coach — Intelligent Exercise Recommendation System'.
"""

import csv
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple

DATASET_DIR = Path(__file__).resolve().parent

ALLOWED_MUSCLE_GROUPS = {
    "Upper Body",
    "Lower Body",
    "Core",
    "Full Body",
    "Balance & Stability",
    "Mobility & Flexibility",
    "Cardio"
}

ALLOWED_MOVEMENT_TYPES = {
    "Static hold",
    "Repetitive",
    "Mobility drill",
    "Plyometric"
}

ALLOWED_IMPACT_LEVELS = {
    "low",
    "moderate",
    "high"
}

ALLOWED_GOALS = {
    "core_stability",
    "muscle_strength",
    "endurance",
    "balance",
    "mobility"
}

ALLOWED_RELATION_TYPES = {
    "easier_variant",
    "progression",
    "complementary",
    "alternative",
    "recovery"
}

ALLOWED_USER_LEVELS = {
    "beginner",
    "intermediate",
    "advanced",
    "all",
    ""
}


def load_csv(filepath: Path) -> List[Dict[str, str]]:
    if not filepath.exists():
        raise FileNotFoundError(f"Fichier introuvable: {filepath}")
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def validate():
    errors: List[str] = []
    warnings: List[str] = []

    print("=" * 70)
    print("DÉMARRAGE DE LA VALIDATION DU DATASET AI FITNESS COACH")
    print("=" * 70)

    # 1. Validation de exercises.csv
    ex_file = DATASET_DIR / "exercises.csv"
    exercises = load_csv(ex_file)
    print(f"-> Chargement de exercises.csv: {len(exercises)} entrées trouvées.")

    if len(exercises) != 100:
        errors.append(f"exercises.csv doit contenir exactement 100 exercices (actuel: {len(exercises)}).")

    exercise_ids: Set[str] = set()
    exercise_names: Set[str] = set()
    ex_dict: Dict[str, Dict[str, str]] = {}

    required_exercise_columns = [
        "exercise_id", "exercise_name", "muscle_group", "secondary_muscle_groups",
        "difficulty", "movement_type", "goals", "equipment", "prerequisites",
        "easier_alternative_id", "harder_alternative_id", "impact_level",
        "is_unilateral", "description", "safety_notes"
    ]

    for idx, row in enumerate(exercises, start=1):
        for col in required_exercise_columns:
            if col not in row or row[col] is None or (row[col].strip() == "" and col not in ["prerequisites", "easier_alternative_id", "harder_alternative_id"]):
                errors.append(f"Ligne {idx} (exercises.csv): Valeur manquante pour la colonne obligatoire '{col}'.")

        eid = row.get("exercise_id", "").strip()
        ename = row.get("exercise_name", "").strip()

        if eid in exercise_ids:
            errors.append(f"ID en doublon détecté: '{eid}' à la ligne {idx}.")
        else:
            exercise_ids.add(eid)
            ex_dict[eid] = row

        if ename.lower() in exercise_names:
            errors.append(f"Nom d'exercice en doublon détecté: '{ename}' à la ligne {idx}.")
        else:
            exercise_names.add(ename.lower())

        mgroup = row.get("muscle_group", "").strip()
        if mgroup not in ALLOWED_MUSCLE_GROUPS:
            errors.append(f"Exercice '{eid}': groupe musculaire non valide '{mgroup}'.")

        mtype = row.get("movement_type", "").strip()
        if mtype not in ALLOWED_MOVEMENT_TYPES:
            errors.append(f"Exercice '{eid}': movement_type non valide '{mtype}'.")

        ilevel = row.get("impact_level", "").strip().lower()
        if ilevel not in ALLOWED_IMPACT_LEVELS:
            errors.append(f"Exercice '{eid}': impact_level non valide '{ilevel}'.")

        diff_str = row.get("difficulty", "").strip()
        try:
            diff = int(diff_str)
            if not (1 <= diff <= 5):
                errors.append(f"Exercice '{eid}': difficulté {diff} hors bornes [1, 5].")
        except ValueError:
            errors.append(f"Exercice '{eid}': difficulté non entière '{diff_str}'.")

        goals = [g.strip() for g in row.get("goals", "").split(";") if g.strip()]
        if not goals:
            errors.append(f"Exercice '{eid}': aucun objectif spécifié dans 'goals'.")
        for g in goals:
            if g not in ALLOWED_GOALS:
                errors.append(f"Exercice '{eid}': objectif non reconnu '{g}'.")

    for eid, row in ex_dict.items():
        easier = row.get("easier_alternative_id", "").strip()
        harder = row.get("harder_alternative_id", "").strip()
        prereqs = [p.strip() for p in row.get("prerequisites", "").split(";") if p.strip()]

        if easier:
            if easier not in exercise_ids:
                errors.append(f"Exercice '{eid}': easier_alternative_id '{easier}' n'existe pas dans le catalogue.")
            elif easier == eid:
                errors.append(f"Exercice '{eid}': easier_alternative_id pointe vers lui-même.")

        if harder:
            if harder not in exercise_ids:
                errors.append(f"Exercice '{eid}': harder_alternative_id '{harder}' n'existe pas dans le catalogue.")
            elif harder == eid:
                errors.append(f"Exercice '{eid}': harder_alternative_id pointe vers lui-même.")

        for p in prereqs:
            if p not in exercise_ids:
                errors.append(f"Exercice '{eid}': prérequis '{p}' n'existe pas dans le catalogue.")
            elif p == eid:
                errors.append(f"Exercice '{eid}': prérequis pointe vers lui-même.")

    # 2. Validation de exercise_relations.csv
    rel_file = DATASET_DIR / "exercise_relations.csv"
    relations = load_csv(rel_file)
    print(f"-> Chargement de exercise_relations.csv: {len(relations)} relations trouvées.")

    rel_ids: Set[str] = set()
    relation_keys: Set[Tuple[str, str, str]] = set()
    outgoing_relations: Dict[str, List[Dict[str, str]]] = {eid: [] for eid in exercise_ids}

    for idx, row in enumerate(relations, start=1):
        rid = row.get("relation_id", "").strip()
        sid = row.get("source_exercise_id", "").strip()
        tid = row.get("target_exercise_id", "").strip()
        rtype = row.get("relation_type", "").strip()
        relevance_str = row.get("base_relevance", "").strip()
        min_lvl = row.get("minimum_user_level", "").strip().lower()

        if rid in rel_ids:
            errors.append(f"Relation ID en doublon '{rid}' à la ligne {idx}.")
        else:
            rel_ids.add(rid)

        if sid not in exercise_ids:
            errors.append(f"Relation '{rid}': source_exercise_id '{sid}' inconnue.")
        if tid not in exercise_ids:
            errors.append(f"Relation '{rid}': target_exercise_id '{tid}' inconnue.")

        if sid == tid and sid != "":
            errors.append(f"Relation '{rid}': l'exercice source '{sid}' est relié à lui-même.")

        if rtype not in ALLOWED_RELATION_TYPES:
            errors.append(f"Relation '{rid}': type de relation non autorisé '{rtype}'.")

        try:
            rel_val = float(relevance_str)
            if not (0 <= rel_val <= 100):
                errors.append(f"Relation '{rid}': base_relevance {rel_val} hors de [0, 100].")
        except ValueError:
            errors.append(f"Relation '{rid}': base_relevance non numérique '{relevance_str}'.")

        if min_lvl not in ALLOWED_USER_LEVELS:
            errors.append(f"Relation '{rid}': minimum_user_level invalide '{min_lvl}'.")

        rel_key = (sid, tid, rtype)
        if rel_key in relation_keys:
            warnings.append(f"Relation doublon détectée: {rel_key} sous ID {rid}.")
        else:
            relation_keys.add(rel_key)

        if sid in outgoing_relations:
            outgoing_relations[sid].append(row)

    exercises_without_candidates = [eid for eid, rels in outgoing_relations.items() if len(rels) == 0]
    if exercises_without_candidates:
        errors.append(f"Exercices sans aucune relation candidate: {exercises_without_candidates}")
    else:
        min_rels = min(len(rels) for rels in outgoing_relations.values())
        max_rels = max(len(rels) for rels in outgoing_relations.values())
        avg_rels = sum(len(rels) for rels in outgoing_relations.values()) / len(outgoing_relations)
        print(f"   Couverture: Chaque exercice possède au moins {min_rels} relations (Max: {max_rels}, Moyenne: {avg_rels:.1f}).")

    # 3. Validation de recommendation_rules.csv
    rule_file = DATASET_DIR / "recommendation_rules.csv"
    rules = load_csv(rule_file)
    print(f"-> Chargement de recommendation_rules.csv: {len(rules)} règles trouvées.")

    rule_ids: Set[str] = set()
    rules_by_ex: Dict[str, Dict[str, Dict[str, str]]] = {eid: {} for eid in exercise_ids}

    for idx, row in enumerate(rules, start=1):
        rid = row.get("rule_id", "").strip()
        eid = row.get("current_exercise_id", "").strip()
        is_corr_str = row.get("is_correct", "").strip().lower()
        allowed_types = [t.strip() for t in row.get("allowed_relation_types", "").split(";") if t.strip()]

        if rid in rule_ids:
            errors.append(f"Rule ID en doublon '{rid}' à la ligne {idx}.")
        else:
            rule_ids.add(rid)

        if eid not in exercise_ids:
            errors.append(f"Règle '{rid}': current_exercise_id '{eid}' n'existe pas dans le catalogue.")

        is_corr = is_corr_str in ["true", "1", "yes"]

        if not is_corr and "progression" in allowed_types:
            errors.append(f"Règle '{rid}' (is_correct=False): violation de sécurité ! La relation 'progression' est autorisée.")

        if eid in rules_by_ex:
            key = "true" if is_corr else "false"
            if key in rules_by_ex[eid]:
                errors.append(f"Exercice '{eid}': multiples règles pour is_correct={key}.")
            else:
                rules_by_ex[eid][key] = row

    missing_rules = []
    for eid in exercise_ids:
        if "true" not in rules_by_ex[eid] or "false" not in rules_by_ex[eid]:
            missing_rules.append(eid)
    if missing_rules:
        errors.append(f"Exercices sans jeu complet de règles (True/False): {missing_rules}")

    print("=" * 70)
    print("RÉSULTAT DE L'AUDIT DU DATASET")
    print("=" * 70)

    if warnings:
        print(f"[!] {len(warnings)} Avertissement(s):")
        for w in warnings[:10]:
            print(f"    - {w}")

    if errors:
        print(f"[X] ÉCHEC DE LA VALIDATION: {len(errors)} erreur(s) détectée(s) :")
        for e in errors:
            print(f"    * {e}")
        print("=" * 70)
        return False
    else:
        print("[V] TOUTES LES VALIDATIONS ONT RÉUSSI AVEC SUCCÈS !")
        print(f"    - Catalogue: 100 exercices valides.")
        print(f"    - Relations: {len(relations)} relations directionnelles valides et vérifiées.")
        print(f"    - Règles: {len(rules)} règles métier cohérentes et sécurisées.")
        print("=" * 70)
        return True


if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)
