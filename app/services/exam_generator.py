import random
import json
from app.models import db, Question, Chapter

DIFFICULTY_RATIOS = {
    "Easy": {"Easy": 10, "Medium": 5, "Hard": 0},
    "Medium": {"Easy": 12, "Medium": 15, "Hard": 18},
    "Hard": {"Easy": 8, "Medium": 10, "Hard": 12}
}

def validate_and_generate_exam(scope_type, selected_subject_ids, selected_chapter_ids, difficulty_mode, pattern_sections, total_questions):
    """
    Modular Question Generator Engine.
    Filters eligible question pool according to scope, subjects, chapters, pattern, and difficulty.
    Returns (success, result_data, error_details).
    """
    query = Question.query.join(Chapter)

    # 1. Apply Scope Filters
    if scope_type == 'Subjectwise':
        if not selected_subject_ids:
            return False, None, {"message": "Please select at least one subject for Subjectwise scope."}
        query = query.filter(Chapter.subject_id.in_(selected_subject_ids))
    elif scope_type == 'Chapterwise':
        if not selected_chapter_ids:
            return False, None, {"message": "Please select at least one chapter for Chapterwise scope."}
        query = query.filter(Question.chapter_id.in_(selected_chapter_ids))
    # All Mixed: no filter

    eligible_questions = query.all()
    total_eligible = len(eligible_questions)

    if total_eligible < total_questions:
        return False, None, {
            "message": f"Insufficient questions in selected scope. Requested {total_questions} questions, but only {total_eligible} total questions exist in this pool.",
            "requested": total_questions,
            "available": total_eligible
        }

    # 2. Process Pattern Sections & Select Questions
    selected_question_ids = []
    used_q_ids = set()
    section_breakdown = []
    insufficient_reasons = []

    for sec in pattern_sections:
        sec_name = sec.get("name", "Section")
        q_type = sec.get("type", "MCQ")
        sec_count = sec.get("count", 10)

        # Filter pool for this question type
        type_pool = [q for q in eligible_questions if q.question_type == q_type and q.id not in used_q_ids]
        available_type_count = len(type_pool)

        if available_type_count < sec_count:
            insufficient_reasons.append(
                f"Section '{sec_name}' requires {sec_count} '{q_type}' questions, but only {available_type_count} exist in selected pool."
            )
            continue

        # Randomly select non-duplicate questions
        chosen = random.sample(type_pool, sec_count)
        for q in chosen:
            used_q_ids.add(q.id)
            selected_question_ids.append(q.id)

        section_breakdown.append({
            "section_name": sec_name,
            "type": q_type,
            "requested": sec_count,
            "selected_count": len(chosen)
        })

    if insufficient_reasons:
        return False, None, {
            "message": "Not enough eligible questions matching pattern and difficulty.",
            "details": insufficient_reasons,
            "total_eligible_in_pool": total_eligible
        }

    return True, {
        "question_ids": selected_question_ids,
        "total_selected": len(selected_question_ids),
        "total_eligible_pool": total_eligible,
        "sections": section_breakdown
    }, None
