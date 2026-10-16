"""
test_scenarios.py
-----------------
Scénarios de test fonctionnels pour le moteur de recommandation 'AI Fitness Coach'.
"""

from recommendation_engine import RecommendationEngine


def print_result(scenario_num: int, title: str, res):
    print("=" * 80)
    print(f"SCÉNARIO {scenario_num} : {title}")
    print("=" * 80)
    print(f"Entrées:")
    print(f"  - Exercice actuel : {res.current_exercise_name} ({res.current_exercise_id})")
    print(f"  - Exécution correcte : {res.is_correct}")
    print(f"  - Niveau utilisateur : {res.user_level}")
    print(f"  - Objectif : {res.goal}")
    print()

    if res.status == "success" and res.primary_recommendation:
        p = res.primary_recommendation
        print(f"Recommandation Principale Sélectionnée:")
        print(f"  -> [{p.exercise_id}] {p.exercise_name} (Difficulté: {p.target_difficulty}, Type: {p.relation_type})")
        print(f"     Score Final: {p.final_score}/100")
        print(f"     Justification: {p.rationale}")
        print(f"     Détail kinésiologique: {p.relation_rationale}")
        print()

        if res.alternatives:
            print("Alternatives proposées:")
            for idx, alt in enumerate(res.alternatives, start=1):
                print(f"  {idx}. [{alt.exercise_id}] {alt.exercise_name} (Score: {alt.final_score}, Type: {alt.relation_type})")
            print()
    else:
        print(f"Statut: Action de repli déclenchée !")
        print(f"  -> Action: {res.fallback_action}")
        print(f"  -> Message: {res.fallback_message}")
        print()


def run_all_tests():
    engine = RecommendationEngine()
    print("\nInitialisation des tests fonctionnels de recommandation...\n")

    # 1. Plank correct, débutant, core_stability
    res1 = engine.recommend(
        current_exercise="Forearm Plank",
        is_correct=True,
        user_level="beginner",
        goal="core_stability"
    )
    print_result(1, "Plank correct - Débutant - core_stability", res1)
    assert res1.status == "success"
    assert res1.primary_recommendation.target_difficulty <= 3

    # 2. Plank incorrect, débutant
    res2 = engine.recommend(
        current_exercise="Forearm Plank",
        is_correct=False,
        user_level="beginner",
        goal="core_stability"
    )
    print_result(2, "Plank incorrect - Débutant (Régression exigée)", res2)
    assert res2.status == "success"
    assert res2.primary_recommendation.target_difficulty <= 2
    assert all(c.relation_type != "progression" for c in [res2.primary_recommendation] + res2.alternatives)

    # 3. Squat correct, intermédiaire, muscle_strength
    res3 = engine.recommend(
        current_exercise="Bodyweight Squat",
        is_correct=True,
        user_level="intermediate",
        goal="muscle_strength"
    )
    print_result(3, "Squat correct - Intermédiaire - muscle_strength", res3)
    assert res3.status == "success"

    # 4. Jumping Jacks incorrects, utilisateur souhaitant low impact
    res4 = engine.recommend(
        current_exercise="Jumping Jacks",
        is_correct=False,
        user_level="beginner",
        goal="endurance",
        preferred_impact="low"
    )
    print_result(4, "Jumping Jacks incorrects - Souhait Low Impact", res4)
    assert res4.status == "success"
    target_ex = engine.exercises[res4.primary_recommendation.exercise_id]
    assert target_ex["impact_level"] == "low"

    # 5. Push-Up correct, avancé, muscle_strength
    res5 = engine.recommend(
        current_exercise="Standard Push-Up",
        is_correct=True,
        user_level="advanced",
        goal="muscle_strength"
    )
    print_result(5, "Push-Up correct - Utilisateur Avancé", res5)
    assert res5.status == "success"

    # 6. Candidats épuisés par l'historique - Repli
    plank_rels = engine.relations_by_source.get("EX040", [])
    all_target_ids = [r["target_exercise_id"] for r in plank_rels]
    res6 = engine.recommend(
        current_exercise="Forearm Plank",
        is_correct=False,
        user_level="beginner",
        session_history=all_target_ids
    )
    print_result(6, "Candidats épuisés par l'historique - Comportement de Repli", res6)
    assert res6.status == "fallback"
    assert res6.fallback_action == "review_technique"

    # 7. Exercice déjà réalisé récemment
    res7 = engine.recommend(
        current_exercise="Forearm Plank",
        is_correct=True,
        user_level="beginner",
        goal="core_stability",
        session_history=["Bird Dog"]
    )
    print_result(7, "Diversité de séance - Évitement de répétition", res7)
    assert res7.status == "success"
    assert res7.primary_recommendation.exercise_name != "Bird Dog"

    # 8. Valeurs par défaut
    res8 = engine.recommend(
        current_exercise="Forearm Plank",
        is_correct=True,
        user_level=None,
        goal=None
    )
    print_result(8, "Gestion robuste des entrées absentes (Niveau et Objectif par défaut)", res8)
    assert res8.status == "success"
    assert res8.user_level == "beginner"

    print("\n" + "=" * 80)
    print("TOUS LES 8 SCÉNARIOS DE TEST ONT ÉTÉ EXÉCUTÉS AVEC SUCCÈS !")
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()
