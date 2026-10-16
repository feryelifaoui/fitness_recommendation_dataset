"""
app.py
------
Point d'entrée de l'API FastAPI pour 'AI Fitness Coach'.
Directement exécutable dans VS Code avec:
    uvicorn app:app --reload --port 8000
"""

import sys
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ajout du sous-dossier au path Python pour importer le moteur
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / "fitness_recommendation_dataset"))

from recommendation_engine import RecommendationEngine

# Initialisation de l'application FastAPI
app = FastAPI(
    title="AI Fitness Coach — API de Recommandation",
    description="Service intelligent de recommandation d'exercices basé sur des règles kinésiologiques",
    version="1.0.0"
)

# Activation CORS pour permettre la communication avec n'importe quelle app Web (React, Vue, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation du moteur avec le dataset du dossier fitness_recommendation_dataset
dataset_path = BASE_DIR / "fitness_recommendation_dataset"
engine = RecommendationEngine(dataset_dir=dataset_path)


# ------------------------------------------------------------------------------
# Modèles Pydantic pour typer les requêtes et réponses
# ------------------------------------------------------------------------------
class RecommendationRequest(BaseModel):
    current_exercise: str = Field(
        ..., 
        example="Forearm Plank",
        description="Nom de l'exercice ou identifiant (ex: 'Forearm Plank' ou 'EX040')"
    )
    is_correct: bool = Field(
        ..., 
        example=True,
        description="True si la posture est validée, False si mauvaise posture"
    )
    user_level: Optional[str] = Field(
        "beginner", 
        example="beginner",
        description="Niveau: beginner, intermediate ou advanced"
    )
    goal: Optional[str] = Field(
        None, 
        example="core_stability",
        description="Objectif: core_stability, muscle_strength, endurance, balance, mobility"
    )
    session_history: Optional[List[str]] = Field(
        default_factory=list,
        example=[],
        description="Liste des exercices déjà réalisés pendant la séance"
    )
    preferred_impact: Optional[str] = Field(
        None,
        example="low",
        description="Contrainte d'impact souhaitée: low, moderate ou high"
    )


class CandidateItem(BaseModel):
    exercise_id: str
    exercise_name: str
    relation_type: str
    difficulty: int
    final_score: float
    rationale: str
    clinical_note: str


class RecommendationResponse(BaseModel):
    status: str
    current_exercise: str
    is_correct: bool
    user_level: str
    goal: str
    primary_recommendation: Optional[CandidateItem] = None
    alternatives: List[CandidateItem] = []
    fallback_action: Optional[str] = None
    fallback_message: Optional[str] = None


# ------------------------------------------------------------------------------
# Endpoints de l'API
# ------------------------------------------------------------------------------
@app.get("/")
def home():
    return {
        "message": "Bienvenue sur l'API AI Fitness Coach Recommender !",
        "documentation": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health():
    return {
        "status": "online",
        "total_exercises_loaded": len(engine.exercises),
        "total_relations_loaded": sum(len(r) for r in engine.relations_by_source.values()),
        "total_rules_loaded": len(engine.rules)
    }


@app.post("/api/v1/recommend", response_model=RecommendationResponse)
def recommend(payload: RecommendationRequest):
    result = engine.recommend(
        current_exercise=payload.current_exercise,
        is_correct=payload.is_correct,
        user_level=payload.user_level,
        goal=payload.goal,
        session_history=payload.session_history,
        preferred_impact=payload.preferred_impact
    )

    primary = None
    if result.primary_recommendation:
        p = result.primary_recommendation
        primary = CandidateItem(
            exercise_id=p.exercise_id,
            exercise_name=p.exercise_name,
            relation_type=p.relation_type,
            difficulty=p.target_difficulty,
            final_score=p.final_score,
            rationale=p.rationale,
            clinical_note=p.relation_rationale
        )

    alts = [
        CandidateItem(
            exercise_id=a.exercise_id,
            exercise_name=a.exercise_name,
            relation_type=a.relation_type,
            difficulty=a.target_difficulty,
            final_score=a.final_score,
            rationale=a.rationale,
            clinical_note=a.relation_rationale
        )
        for a in result.alternatives
    ]

    return RecommendationResponse(
        status=result.status,
        current_exercise=result.current_exercise_name,
        is_correct=result.is_correct,
        user_level=result.user_level,
        goal=result.goal,
        primary_recommendation=primary,
        alternatives=alts,
        fallback_action=result.fallback_action,
        fallback_message=result.fallback_message
    )


if __name__ == "__main__":
    import uvicorn
    print("Démarrage du serveur sur http://127.0.0.1:8000 ...")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
