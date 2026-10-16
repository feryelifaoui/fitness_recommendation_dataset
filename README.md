# AI Fitness Coach — Intelligent Exercise Recommendation System

> **Système expert de recommandation kinésiologique et moteur décisionnel pour le coaching sportif intelligent.**

Ce projet fournit le dataset complet, normalisé et documenté, ainsi que le moteur décisionnel en Python permettant de recommander un exercice sportif à un utilisateur selon :
1. L'exercice qu'il vient de réaliser (`current_exercise`),
2. La qualité technique de son exécution (`is_correct`),
3. Son niveau (`user_level` : *beginner*, *intermediate*, *advanced*),
4. Son objectif prioritaire (`goal` : *core_stability*, *muscle_strength*, *endurance*, *balance*, *mobility*),
5. L'historique des exercices déjà complétés durant la séance (`session_history`).

---

## 1. Architecture & Découplage

Le moteur de recommandation est **totalement découplé de la vision par ordinateur (Computer Vision)** :
- Il ne traite **aucune image ni flux vidéo**.
- Il ne dépend d'aucun matériel spécifique (caméra ou capteur).
- Il reçoit exclusivement des **données structurées** issues d'un module de détection amont et retourne une recommandation prioritaire, des alternatives et des justifications textuelles explicites.

```
+------------------------------------+
|  Module Computer Vision (Amont)   |
|  - Détection du mouvement          |
|  - Évaluation de forme technique   |
+-----------------+------------------+
                  | Données structurées JSON
                  v
+------------------------------------+
|   AI Fitness Recommendation Engine |
|   - Filtrage par règles métier     |
|   - Algorithme de scoring pondéré  |
|   - Fallback et explications       |
+-----------------+------------------+
                  |
                  v
     Recommandation + Alternatives + Rationale
```

---

## 2. Organisation des Fichiers

```text
fitness_recommendation_dataset/
├── exercises.csv              # Catalogue des 100 exercices sportifs (Poids du corps / caméra)
├── exercise_relations.csv     # 386 relations kinésiologiques directionnelles typées
├── recommendation_rules.csv   # 200 règles métier déterministes (is_correct = True / False)
├── generate_dataset.py        # Script reproductible de génération des fichiers CSV
├── validate_dataset.py        # Script d'audit automatique et de validation d'intégrité
├── recommendation_engine.py   # Moteur de recommandation, scoring et explications
├── test_scenarios.py          # 8 scénarios de test fonctionnels couvrant tous les cas métier
└── README.md                  # Documentation technique exhaustive
```

---

## 3. Spécification Détaillée des Données (CSV)

Tous les fichiers sont encodés en **UTF-8** avec la virgule `,` comme délimiteur de colonnes. Les listes multiples au sein d'un même champ utilisent le **point-virgule `;`** comme séparateur.

### 3.1. `exercises.csv` (100 exercices)

Catalogue de référence contenant 100 exercices distincts, sans doublons, privilégient le poids du corps (*bodyweight*) et les postures adaptées à la vision par caméra (tapis, chaise, mur).

| Colonne | Type | Description | Valeurs autorisées / Exemples |
| :--- | :--- | :--- | :--- |
| `exercise_id` | String (Clé primaire) | Identifiant unique standardisé | `EX001` à `EX100` |
| `exercise_name` | String (Unique) | Nom standardisé de l'exercice en anglais | `Wall Push-Up`, `Forearm Plank`, `Bodyweight Squat` |
| `muscle_group` | String (Catégoriel) | Groupe fonctionnel ou musculaire principal | `Upper Body`, `Lower Body`, `Core`, `Full Body`, `Balance & Stability`, `Mobility & Flexibility`, `Cardio` |
| `secondary_muscle_groups` | String (Liste `;`) | Groupes musculaires secondaires sollicités | Ex: `Chest;Shoulders;Triceps;Core` |
| `difficulty` | Entier | Niveau de difficulté perçu de 1 à 5 | `1` (Accessible/Éveil), `2` (Novice), `3` (Intermédiaire), `4` (Avancé), `5` (Élite) |
| `movement_type` | String (Catégoriel) | Régime biomécanique du mouvement | `Static hold`, `Repetitive`, `Mobility drill`, `Plyometric` |
| `goals` | String (Liste `;`) | Objectifs auxquels l'exercice contribue | `core_stability`, `muscle_strength`, `endurance`, `balance`, `mobility` |
| `equipment` | String | Équipement minimal requis | `bodyweight`, `mat`, `chair`, `wall` |
| `prerequisites` | String (Liste `;`) | Identifiants des exercices prérequis | Ex: `EX001` ou chaîne vide |
| `easier_alternative_id`| String | ID d'une régression directe plus accessible | Ex: `EX039` ou chaîne vide |
| `harder_alternative_id`| String | ID d'une progression directe plus exigeante | Ex: `EX041` ou chaîne vide |
| `impact_level` | String (Catégoriel) | Niveau de contrainte articulaire / impact sol | `low`, `moderate`, `high` |
| `is_unilateral` | Booléen | Indique si le mouvement est unilatéral | `True`, `False` |
| `description` | String | Brève description fonctionnelle du mouvement | Ex: *Supine cross-pattern arm and leg extension...* |
| `safety_notes` | String | Précautions et points d'attention biomécaniques | Ex: *Keep lower back glued to mat; avoid cervical pull.* |

#### Répartition des 100 exercices par groupe :
- **Upper Body** (18 exercices : `EX001` à `EX018`) : Pompes murales, inclinées, standard, diamant, déclinées, pike, dips, tirages dorsaux, élévations scapulaires.
- **Lower Body** (20 exercices : `EX019` à `EX038`) : Squats assis, box squats, squats libres, sumo, fentes arrière, avant, bulgares, ponts fessiers, mollets, abducteurs.
- **Core** (22 exercices : `EX039` à `EX060`) : Gainages sur genoux, coudes, haut, latéraux, dead bug, bird dog, hollow body, relevés de jambes, ciseaux, crunchs.
- **Full Body** (12 exercices : `EX061` à `EX072`) : Burpees pas-à-pas, burpees standard, inchworms, climbers lents/rapides, bear crawl, turkish get-up.
- **Balance & Stability** (10 exercices : `EX073` à `EX082`) : Stance tandem, équilibre unipodal (yeux ouverts/fermés), reaches horloge, RDL unilatéral, pose avion.
- **Mobility & Flexibility** (10 exercices : `EX083` à `EX092`) : Chat-vache, posture de l'enfant, chien tête en bas, stretch du coureur, pigeon, cobra, étirements fessiers et psoas.
- **Cardio** (8 exercices : `EX093` à `EX100`) : Step jacks (faible impact), jumping jacks, seal jacks, montées de genoux marchées/courues, butt kicks, skater hops, shadow boxing.

---

### 3.2. `exercise_relations.csv` (386 relations)

Définit le graphe directionnel des transitions kinésiologiques entre les exercices.

| Colonne | Type | Description |
| :--- | :--- | :--- |
| `relation_id` | String | Identifiant unique (`REL0001`...) |
| `source_exercise_id` | String (FK `exercises`) | Exercice source actuellement réalisé |
| `target_exercise_id` | String (FK `exercises`) | Exercice cible candidat à la recommandation |
| `relation_type` | String | Typologie de la relation : `easier_variant`, `progression`, `complementary`, `alternative`, `recovery` |
| `base_relevance` | Float (0 - 100) | Pertinence heuristique intrinsèque de la transition |
| `goal_match` | String (Liste `;`) | Objectifs pour lesquels cette transition est bénéfique |
| `minimum_user_level` | String | Niveau minimum requis (`beginner`, `intermediate`, `advanced`, `all`) |
| `requires_correct_execution`| Booléen | Exige `is_correct = True` pour être candidate |
| `rationale` | String | Justification biomécanique de la transition |
| `review_status` | String | Statut de validation kinésiologique (`validated`) |

---

### 3.3. `recommendation_rules.csv` (200 règles)

Définit les règles métier déterministes associées à chaque exercice :
- **Cas A (`is_correct = True`)** : Favorise le travail synergique (`complementary`), les alternatives latérales (`alternative`) et permet une `progression` si le niveau de l'utilisateur le permet.
- **Cas B (`is_correct = False`)** : Interdit formellement toute progression. Privilégie une variante allégée (`easier_variant`), une décompression active (`recovery`) ou une révision technique.

| Colonne | Type | Description |
| :--- | :--- | :--- |
| `rule_id` | String | Identifiant de la règle (`RUL0001`...) |
| `current_exercise_id` | String (FK) | Exercice déclencheur |
| `is_correct` | Booléen | Condition d'exécution technique (`True` ou `False`) |
| `allowed_relation_types` | String (Liste `;`) | Types de relations admissibles pour ce cas |
| `priority_relation_types`| String (Liste `;`) | Types prioritaires dans l'ordonnancement |
| `difficulty_policy` | String | Politique de difficulté (`maintain_or_increase`, `decrease_or_maintain`) |
| `goal_filter` | String | Stratégie de filtrage des objectifs (`match_current_or_any`) |
| `history_policy` | String | Gestion des répétitions (`exclude_recent`) |
| `fallback_action` | String | Action par défaut en cas d'absence de candidat (`review_technique`, `active_continuation`) |
| `rule_rationale` | String | Logique pédagogique de la règle |

---

## 4. Logique de Classement & Scoring

### Formule Multi-Critères Explicite

Pour chaque candidat admissible ayant franchi les filtres de sécurité, le moteur calcule un score composite normalisé sur 100 :

$$\text{Final Score} = w_1 \cdot \text{BaseRelevance} + w_2 \cdot \text{GoalScore} + w_3 \cdot \text{DifficultyFit} + w_4 \cdot \text{DiversityScore}$$

Pondérations configurables par défaut :
- $w_1 = 0.35$ : Pertinence kinésiologique de base de la transition (`base_relevance` de 0 à 100).
- $w_2 = 0.30$ : Alignement avec l'objectif de l'utilisateur (`100` si l'objectif correspond directement aux attributs de l'exercice cible, `85` si présent dans la relation, `40` sinon).
- $w_3 = 0.20$ : Adéquation de la difficulté avec le profil et l'état d'exécution :
  - Si `is_correct = True` : $\Delta \text{diff} \in [0, +1]$ valorisé ($95$ à $100$ pts).
  - Si `is_correct = False` : régression $\Delta \text{diff} \in [-1, -2]$ valorisée ($90$ à $100$ pts) ; augmentation strictement interdite.
- $w_4 = 0.15$ : Nouveauté et diversité dans la séance ($100$ pts si l'exercice n'a pas encore été réalisé).

> [!NOTE]
> Le score `base_relevance` est un score heuristique initial établi selon des principes kinésiologiques et non une probabilité issue d'un modèle d'apprentissage supervisé. Aucun modèle de Machine Learning n'est prétendu entraîné sans données d'interactions réelles annotées.

---

## 5. Installation & Exécution Rapide

### Prérequis
- Python 3.8+ (testé avec Python 3.12).
- **Aucune dépendance externe requise** pour la génération, la validation et les tests unitaires (fonctionne exclusivement avec la bibliothèque standard Python : `csv`, `pathlib`, `typing`, `dataclasses`).

### Commandes

1. **Régénérer le dataset** :
   ```powershell
   python generate_dataset.py
   ```
   *Génère `exercises.csv`, `exercise_relations.csv` et `recommendation_rules.csv` de manière reproductible et sans doublons.*

2. **Exécuter l'audit et la validation automatique** :
   ```powershell
   python validate_dataset.py
   ```
   *Vérifie l'ensemble des 16 règles d'intégrité référentielle, d'unicité, de bornes et de sécurité. Retourne le code `0` en cas de succès.*

3. **Exécuter les scénarios de test fonctionnels** :
   ```powershell
   python test_scenarios.py
   ```
   *Valide les 8 scénarios d'usage (exécutions correctes, échecs techniques, contraintes low impact, profils débutant/avancé, gestion des historiques et fallbacks).*

---

## 6. Analyse des 8 Scénarios de Test

Le script `test_scenarios.py` démontre le comportement attendu sur les cas métiers clés :

| # | Scénario | Entrée (`is_correct`, niveau, goal) | Recommandation Principale | Justification du Choix & Filtrage |
| :-: | :--- | :--- | :--- | :--- |
| **1** | Gainage réussi par débutant | `Forearm Plank`, `True`, `beginner`, `core_stability` | `Bird Dog` (`EX046`, diff 2) ou `High Plank` (`EX041`, diff 2) | Propose un exercice complémentaire de stabilité controlatérale sans surcharger la difficulté. |
| **2** | Gainage raté par débutant | `Forearm Plank`, `False`, `beginner`, `core_stability` | `Knee Plank` (`EX039`, diff 1) | Régression immédiate sur genoux pour réapprendre le verrouillage pelvien sans risque lombaire. |
| **3** | Squat réussi par intermédiaire | `Bodyweight Squat`, `True`, `intermediate`, `muscle_strength` | `Sumo Squat` (`EX022`) ou `Reverse Lunge` (`EX025`) | Consolidation unilatérale ou ouverture d'angle de hanche adaptée au niveau intermédiaire. |
| **4** | Jumping Jacks ratés avec contrainte low-impact | `Jumping Jacks`, `False`, `beginner`, `endurance`, `impact="low"` | `Step Jacks` (`EX093`, diff 1, low impact) | Élimine les impacts articulaires au sol tout en préservant le stimulus cardiovasculaire. |
| **5** | Pompes réussies par avancé | `Standard Push-Up`, `True`, `advanced`, `muscle_strength` | `Diamond Push-Up` (`EX005`, diff 4) | Autorise la progression exigeante grâce au niveau avancé validé. |
| **6** | Candidats épuisés par historique | `Forearm Plank`, `False`, historique saturé | **Fallback Déclenché** (`review_technique`) | Aucun candidat frais disponible : le système invite à une pause technique et pédagogique. |
| **7** | Diversité de séance | `Forearm Plank`, `True`, `Bird Dog` déjà réalisé | `High Plank` (`EX041`) | Écarte `Bird Dog` de la sélection pour éviter la redondance et maximise la variété. |
| **8** | Entrées incomplètes | `Forearm Plank`, `True`, sans niveau ni objectif | `Bird Dog` (`EX046`) | Application automatique des valeurs par défaut (`beginner`, `core_stability`) sans blocage. |

---

## 7. Intégration dans une API FastAPI

Pour intégrer ce moteur de recommandation dans une application web ou mobile de coaching sportif en direct, voici une implémentation prête pour la production avec **FastAPI** et **Pydantic** :

### Installation des dépendances API
```bash
pip install fastapi uvicorn pydantic
```

### Code de l'API (`app.py`)
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from recommendation_engine import RecommendationEngine

app = FastAPI(
    title="AI Fitness Coach — Recommendation Service",
    description="API REST de recommandation d'exercices basée sur des règles kinésiologiques",
    version="1.0.0"
)

# Chargement unique du moteur au démarrage
engine = RecommendationEngine()

class RecommendationRequest(BaseModel):
    current_exercise: str = Field(..., description="Nom ou identifiant de l'exercice actuel (ex: 'Forearm Plank' ou 'EX040')")
    is_correct: bool = Field(True, description="Indicateur d'exécution correcte déterminé par la Vision")
    user_level: Optional[str] = Field("beginner", description="Niveau de l'utilisateur: beginner, intermediate, advanced")
    goal: Optional[str] = Field(None, description="Objectif: core_stability, muscle_strength, endurance, balance, mobility")
    session_history: Optional[List[str]] = Field(default_factory=list, description="Liste des exercices déjà réalisés pendant la séance")
    preferred_impact: Optional[str] = Field(None, description="Filtre d'impact: low, moderate, high")

class CandidateOut(BaseModel):
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
    user_level: str
    goal: str
    primary_recommendation: Optional[CandidateOut]
    alternatives: List[CandidateOut]
    fallback_action: Optional[str] = None
    fallback_message: Optional[str] = None

@app.post("/api/v1/recommend", response_model=RecommendationResponse)
def get_recommendation(payload: RecommendationRequest):
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
        primary = CandidateOut(
            exercise_id=p.exercise_id,
            exercise_name=p.exercise_name,
            relation_type=p.relation_type,
            difficulty=p.target_difficulty,
            final_score=p.final_score,
            rationale=p.rationale,
            clinical_note=p.relation_rationale
        )

    alts = [
        CandidateOut(
            exercise_id=a.exercise_id,
            exercise_name=a.exercise_name,
            relation_type=a.relation_type,
            difficulty=a.target_difficulty,
            final_score=a.final_score,
            rationale=a.rationale,
            clinical_note=a.relation_rationale
        ) for a in result.alternatives
    ]

    return RecommendationResponse(
        status=result.status,
        current_exercise=result.current_exercise_name,
        user_level=result.user_level,
        goal=result.goal,
        primary_recommendation=primary,
        alternatives=alts,
        fallback_action=result.fallback_action,
        fallback_message=result.fallback_message
    )

# Lancement en local: uvicorn app:app --reload --port 8000
```

---

## 8. Limites Actuelles & Perspectives

1. **Absence de capteurs biométriques** : Le système ne prend pas encore en compte la fréquence cardiaque en temps réel (BPM) ou l'indice d'effort perçu (RPE).
2. **Heuristiques expertes vs Apprentissage par renforcement** : Les scores de pertinence reposent sur des règles de bonne pratique biomécanique validées ; une future version pourra intégrer un modèle de *Contextual Bandits* pour affiner les pondérations d'après les taux d'abandon ou de réussite des utilisateurs.
3. **Poids du corps prédominant** : Le catalogue est volontairement restreint aux exercices sans machines lourdes pour rester compatible avec des caméras d'ordinateurs portables ou de smartphones dans un salon standard.
