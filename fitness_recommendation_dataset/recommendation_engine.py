"""
recommendation_engine.py
------------------------
Moteur de recommandation intelligent pour 'AI Fitness Coach'.

Ce module implémente:
1. Le chargement et l'indexation du catalogue, des relations et des règles.
2. La sélection des candidats pertinents selon les règles métier.
3. Le filtrage de sécurité (difficulté, niveau utilisateur, historique de séance).
4. Le calcul de score heuristique multi-critères explicite et pondéré.
5. La sélection de la meilleure recommandation et des alternatives.
6. La génération d'explications détaillées et transparentes (rationale).
7. La gestion des scénarios de repli (fallback).
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple


USER_LEVEL_WEIGHTS = {
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
    "all": 1,
    "": 1
}


@dataclass
class CandidateScore:
    exercise_id: str
    exercise_name: str
    relation_type: str
    target_difficulty: int
    base_relevance: float
    goal_score: float
    difficulty_fit_score: float
    diversity_score: float
    final_score: float
    rationale: str
    relation_rationale: str


@dataclass
class RecommendationResult:
    status: str  # "success" ou "fallback"
    current_exercise_id: str
    current_exercise_name: str
    is_correct: bool
    user_level: str
    goal: str
    primary_recommendation: Optional[CandidateScore]
    alternatives: List[CandidateScore] = field(default_factory=list)
    excluded_candidates: List[Dict[str, str]] = field(default_factory=list)
    fallback_action: Optional[str] = None
    fallback_message: Optional[str] = None


class RecommendationEngine:
    def __init__(self, dataset_dir: Optional[Path] = None):
        if dataset_dir is None:
            dataset_dir = Path(__file__).resolve().parent
        self.dataset_dir = dataset_dir

        self.exercises: Dict[str, Dict[str, Any]] = {}
        self.name_to_id: Dict[str, str] = {}
        self.relations_by_source: Dict[str, List[Dict[str, Any]]] = {}
        self.rules: Dict[Tuple[str, bool], Dict[str, Any]] = {}

        # Poids configurables de la formule de classement
        self.weights = {
            "base_relevance": 0.35,
            "goal_alignment": 0.30,
            "difficulty_fit": 0.20,
            "diversity": 0.15
        }

        self._load_dataset()

    def _load_dataset(self):
        # 1. exercises.csv
        ex_path = self.dataset_dir / "exercises.csv"
        with open(ex_path, mode="r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                eid = row["exercise_id"]
                row["difficulty"] = int(row["difficulty"])
                row["is_unilateral"] = row["is_unilateral"].lower() in ["true", "1"]
                row["goals_list"] = [g.strip() for g in row["goals"].split(";") if g.strip()]
                self.exercises[eid] = row
                self.name_to_id[row["exercise_name"].lower()] = eid

        # 2. exercise_relations.csv
        rel_path = self.dataset_dir / "exercise_relations.csv"
        with open(rel_path, mode="r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                sid = row["source_exercise_id"]
                row["base_relevance"] = float(row["base_relevance"])
                row["requires_correct_execution"] = row["requires_correct_execution"].lower() in ["true", "1"]
                row["goal_match_list"] = [g.strip() for g in row["goal_match"].split(";") if g.strip()]
                if sid not in self.relations_by_source:
                    self.relations_by_source[sid] = []
                self.relations_by_source[sid].append(row)

        # 3. recommendation_rules.csv
        rule_path = self.dataset_dir / "recommendation_rules.csv"
        with open(rule_path, mode="r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                eid = row["current_exercise_id"]
                is_corr = row["is_correct"].lower() in ["true", "1"]
                row["allowed_relation_types_list"] = [t.strip() for t in row["allowed_relation_types"].split(";") if t.strip()]
                row["priority_relation_types_list"] = [t.strip() for t in row["priority_relation_types"].split(";") if t.strip()]
                self.rules[(eid, is_corr)] = row

    def resolve_exercise_id(self, identifier: str) -> Optional[str]:
        if not identifier:
            return None
        clean = identifier.strip()
        if clean in self.exercises:
            return clean
        clean_lower = clean.lower()
        if clean_lower in self.name_to_id:
            return self.name_to_id[clean_lower]
        for name, eid in self.name_to_id.items():
            if clean_lower in name:
                return eid
        return None

    def recommend(
        self,
        current_exercise: str,
        is_correct: bool = True,
        user_level: Optional[str] = "beginner",
        goal: Optional[str] = None,
        session_history: Optional[List[str]] = None,
        preferred_impact: Optional[str] = None
    ) -> RecommendationResult:
        exercise_id = self.resolve_exercise_id(current_exercise)
        if not exercise_id:
            return RecommendationResult(
                status="fallback",
                current_exercise_id=current_exercise,
                current_exercise_name=current_exercise,
                is_correct=is_correct,
                user_level=user_level or "beginner",
                goal=goal or "core_stability",
                primary_recommendation=None,
                alternatives=[],
                fallback_action="manual_selection",
                fallback_message=f"L'exercice '{current_exercise}' n'a pas été trouvé dans le catalogue."
            )

        current_ex = self.exercises[exercise_id]
        norm_level = (user_level or "beginner").strip().lower()
        if norm_level not in ["beginner", "intermediate", "advanced"]:
            norm_level = "beginner"

        norm_goal = goal.strip().lower() if goal else (current_ex["goals_list"][0] if current_ex["goals_list"] else "core_stability")
        
        history_ids = set()
        if session_history:
            for item in session_history:
                hid = self.resolve_exercise_id(item)
                if hid:
                    history_ids.add(hid)

        rule = self.rules.get((exercise_id, is_correct))
        allowed_types = set(rule["allowed_relation_types_list"]) if rule else {"complementary", "alternative", "easier_variant", "recovery"}
        fallback_action = rule["fallback_action"] if rule else ("active_continuation" if is_correct else "review_technique")

        candidate_relations = self.relations_by_source.get(exercise_id, [])

        scored_candidates: List[CandidateScore] = []
        excluded_candidates: List[Dict[str, str]] = []

        user_weight = USER_LEVEL_WEIGHTS.get(norm_level, 1)

        for rel in candidate_relations:
            target_id = rel["target_exercise_id"]
            target_ex = self.exercises.get(target_id)
            if not target_ex:
                continue

            rel_type = rel["relation_type"]
            target_diff = target_ex["difficulty"]
            current_diff = current_ex["difficulty"]
            min_lvl = rel.get("minimum_user_level", "beginner")
            min_weight = USER_LEVEL_WEIGHTS.get(min_lvl, 1)

            # --- FILTRAGE 1: Types autorisés ---
            if rel_type not in allowed_types:
                excluded_candidates.append({
                    "exercise_id": target_id,
                    "exercise_name": target_ex["exercise_name"],
                    "reason": f"Type de relation '{rel_type}' non autorisé lorsque is_correct={is_correct}."
                })
                continue

            # --- FILTRAGE 2: Sécurité stricte sur échec ---
            if not is_correct:
                if rel_type == "progression":
                    excluded_candidates.append({
                        "exercise_id": target_id,
                        "exercise_name": target_ex["exercise_name"],
                        "reason": "Exclusion de sécurité: aucune progression n'est tolérée après une mauvaise exécution."
                    })
                    continue
                if target_diff > current_diff:
                    excluded_candidates.append({
                        "exercise_id": target_id,
                        "exercise_name": target_ex["exercise_name"],
                        "reason": f"Exclusion de sécurité: difficulté ({target_diff}) supérieure à l'exercice actuel ({current_diff}) après échec technique."
                    })
                    continue

            # --- FILTRAGE 3: Niveau utilisateur requis ---
            if user_weight < min_weight:
                excluded_candidates.append({
                    "exercise_id": target_id,
                    "exercise_name": target_ex["exercise_name"],
                    "reason": f"Niveau utilisateur insuffisant ('{norm_level}' < requis '{min_lvl}')."
                })
                continue

            # --- FILTRAGE 4: Historique de séance ---
            if target_id in history_ids:
                excluded_candidates.append({
                    "exercise_id": target_id,
                    "exercise_name": target_ex["exercise_name"],
                    "reason": "Exercice déjà réalisé lors de cette séance (politique de diversité de l'historique)."
                })
                continue

            # --- FILTRAGE 5: Contrainte de faible impact ---
            if preferred_impact == "low" and target_ex["impact_level"] in ["moderate", "high"]:
                excluded_candidates.append({
                    "exercise_id": target_id,
                    "exercise_name": target_ex["exercise_name"],
                    "reason": f"Impact ({target_ex['impact_level']}) incompatible avec la contrainte stricte 'low impact'."
                })
                continue

            # --- CALCUL DU SCORE ---
            base_rel = rel["base_relevance"]

            if norm_goal in target_ex["goals_list"]:
                goal_score = 100.0
            elif norm_goal in rel["goal_match_list"]:
                goal_score = 85.0
            else:
                goal_score = 40.0

            if is_correct:
                if target_diff == current_diff:
                    diff_score = 95.0
                elif target_diff == current_diff + 1:
                    diff_score = 100.0 if norm_level in ["intermediate", "advanced"] else 80.0
                elif target_diff < current_diff:
                    diff_score = 75.0
                else:
                    diff_score = 50.0
            else:
                if target_diff < current_diff:
                    diff_score = 100.0
                elif target_diff == current_diff:
                    diff_score = 80.0
                else:
                    diff_score = 20.0

            diversity_score = 100.0

            final_score = (
                self.weights["base_relevance"] * base_rel +
                self.weights["goal_alignment"] * goal_score +
                self.weights["difficulty_fit"] * diff_score +
                self.weights["diversity"] * diversity_score
            )

            rationale_parts = []
            if rel_type == "easier_variant":
                rationale_parts.append(f"Variante accessible réduisant la charge pour corriger la technique.")
            elif rel_type == "progression":
                rationale_parts.append(f"Progression exigeante adaptée au niveau {norm_level}.")
            elif rel_type == "complementary":
                rationale_parts.append(f"Exercice synergique sollicitant les muscles stabilisateurs ou antagonistes.")
            elif rel_type == "alternative":
                rationale_parts.append(f"Alternative de même intensité pour varier le schéma moteur.")
            elif rel_type == "recovery":
                rationale_parts.append(f"Exercice de récupération active et de décompression articulaire.")

            if norm_goal in target_ex["goals_list"]:
                rationale_parts.append(f"Contribue directement à l'objectif '{norm_goal}'.")

            full_rationale = " ".join(rationale_parts)

            scored_candidates.append(CandidateScore(
                exercise_id=target_id,
                exercise_name=target_ex["exercise_name"],
                relation_type=rel_type,
                target_difficulty=target_diff,
                base_relevance=base_rel,
                goal_score=goal_score,
                difficulty_fit_score=diff_score,
                diversity_score=diversity_score,
                final_score=round(final_score, 2),
                rationale=full_rationale,
                relation_rationale=rel["rationale"]
            ))

        scored_candidates.sort(key=lambda c: c.final_score, reverse=True)

        if not scored_candidates:
            msg = (
                f"Aucun candidat direct admissible pour {current_ex['exercise_name']}. "
                f"Action de repli déclenchée: '{fallback_action}'."
            )
            return RecommendationResult(
                status="fallback",
                current_exercise_id=exercise_id,
                current_exercise_name=current_ex["exercise_name"],
                is_correct=is_correct,
                user_level=norm_level,
                goal=norm_goal,
                primary_recommendation=None,
                alternatives=[],
                excluded_candidates=excluded_candidates,
                fallback_action=fallback_action,
                fallback_message=msg
            )

        return RecommendationResult(
            status="success",
            current_exercise_id=exercise_id,
            current_exercise_name=current_ex["exercise_name"],
            is_correct=is_correct,
            user_level=norm_level,
            goal=norm_goal,
            primary_recommendation=scored_candidates[0],
            alternatives=scored_candidates[1:4],
            excluded_candidates=excluded_candidates,
            fallback_action=None,
            fallback_message=None
        )
