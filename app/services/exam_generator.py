import random
import json
from app.models import db, Question, Chapter

DIFFICULTY_RATIOS = {
    "Easy": {"Easy": 10, "Medium": 5, "Hard": 0},
    "Medium": {"Easy": 12, "Medium": 15, "Hard": 18},
    "Hard": {"Easy": 8, "Medium": 10, "Hard": 12}
}

def validate_ranges(ranges, total_questions):
    """
    Validates structured range configurations.
    Returns (is_valid, error_message).
    """
    if not ranges or not isinstance(ranges, list):
        return False, "Structured mode requires at least one question range definition."

    covered = [False] * (total_questions + 1)

    for idx, r in enumerate(ranges):
        try:
            start = int(r.get("start"))
            end = int(r.get("end"))
        except (ValueError, TypeError):
            return False, f"Range #{idx + 1} has invalid position values."

        if start < 1 or end < 1:
            return False, f"Range #{idx + 1} positions must be 1 or greater."
        if start > total_questions or end > total_questions:
            return False, f"Range #{idx + 1} positions ({start}–{end}) exceed total questions ({total_questions})."
        if start > end:
            return False, f"Range #{idx + 1} start position ({start}) cannot be greater than end position ({end})."

        for pos in range(start, end + 1):
            if covered[pos]:
                return False, f"Question position #{pos} is covered by multiple overlapping ranges."
            covered[pos] = True

    missing_positions = [pos for pos in range(1, total_questions + 1) if not covered[pos]]
    if missing_positions:
        return False, f"The following question positions are not covered by any range: {', '.join(map(str, missing_positions))}."

    return True, None


def validate_and_generate_exam(scope_type, selected_subject_ids, selected_chapter_ids, difficulty_mode, pattern_sections, total_questions, ordering_mode='Randomized', ranges=None):
    """
    Modular Question Generator Engine with Structured Range Support.
    Satisfies position-by-position constraints (subject/chapter range, question type pattern, non-duplicate selection).
    """
    if ordering_mode == 'Structured':
        is_valid, range_err = validate_ranges(ranges, total_questions)
        if not is_valid:
            return False, None, {"message": range_err}

        # Build position requirements
        # Position i (1-based) -> required question_type from pattern_sections
        pos_type_map = {}
        for sec in pattern_sections:
            sec_start = int(sec.get("start", 1))
            sec_end = int(sec.get("end", total_questions))
            q_type = sec.get("type", "MCQ")
            for pos in range(sec_start, sec_end + 1):
                if pos <= total_questions:
                    pos_type_map[pos] = q_type

        # Sort ranges by start position
        sorted_ranges = sorted(ranges, key=lambda x: int(x.get("start", 1)))
        position_assignments = [None] * (total_questions + 1)
        used_q_ids = set()
        insufficient_reasons = []
        range_breakdown = []

        for r in sorted_ranges:
            start = int(r["start"])
            end = int(r["end"])
            subject_id = r.get("subject_id")
            chapter_id = r.get("chapter_id")
            subject_name = r.get("subject_name", f"Subject #{subject_id}")
            chapter_name = r.get("chapter_name", "All Chapters")

            # Query eligible questions for this range source
            query = Question.query.join(Chapter)
            if chapter_id:
                query = query.filter(Question.chapter_id == int(chapter_id))
            elif subject_id:
                query = query.filter(Chapter.subject_id == int(subject_id))

            range_pool = query.all()

            # Group positions in this range by required question type
            type_reqs = {}
            for pos in range(start, end + 1):
                req_t = pos_type_map.get(pos, "MCQ")
                type_reqs.setdefault(req_t, []).append(pos)

            # Check if pool satisfies required question types for this range
            range_failed = False
            for req_t, pos_list in type_reqs.items():
                needed_cnt = len(pos_list)
                eligible_for_type = [q for q in range_pool if q.question_type == req_t and q.id not in used_q_ids]
                avail_cnt = len(eligible_for_type)

                if avail_cnt < needed_cnt:
                    insufficient_reasons.append(
                        f"Not enough eligible questions for Q{start}–Q{end} ({subject_name} · {chapter_name}). Required: {needed_cnt} '{req_t}' question(s), Available: {avail_cnt}."
                    )
                    range_failed = True
                else:
                    chosen = random.sample(eligible_for_type, needed_cnt)
                    for idx, pos in enumerate(pos_list):
                        q_sel = chosen[idx]
                        used_q_ids.add(q_sel.id)
                        position_assignments[pos] = q_sel.id

            range_breakdown.append({
                "range_label": f"Q{start}–Q{end}",
                "source": f"{subject_name} · {chapter_name}",
                "count": (end - start + 1)
            })

        if insufficient_reasons:
            return False, None, {
                "message": "Not enough eligible questions to fulfill structured range configuration.",
                "details": insufficient_reasons
            }

        selected_question_ids = [position_assignments[pos] for pos in range(1, total_questions + 1)]
        return True, {
            "question_ids": selected_question_ids,
            "total_selected": len(selected_question_ids),
            "ordering_mode": "Structured",
            "ranges": range_breakdown
        }, None

    else: # Randomized Mix
        query = Question.query.join(Chapter)

        # Apply Scope Filters
        if scope_type == 'Subjectwise':
            if not selected_subject_ids:
                return False, None, {"message": "Please select at least one subject for Subjectwise scope."}
            query = query.filter(Chapter.subject_id.in_(selected_subject_ids))
        elif scope_type == 'Chapterwise':
            if not selected_chapter_ids:
                return False, None, {"message": "Please select at least one chapter for Chapterwise scope."}
            query = query.filter(Question.chapter_id.in_(selected_chapter_ids))

        eligible_questions = query.all()
        total_eligible = len(eligible_questions)

        if total_eligible < total_questions:
            return False, None, {
                "message": f"Insufficient questions in selected scope. Requested {total_questions} questions, but only {total_eligible} total questions exist in this pool.",
                "requested": total_questions,
                "available": total_eligible
            }

        selected_question_ids = []
        used_q_ids = set()
        section_breakdown = []
        insufficient_reasons = []

        for sec in pattern_sections:
            sec_name = sec.get("name", "Section")
            q_type = sec.get("type", "MCQ")
            sec_count = sec.get("count", 10)

            type_pool = [q for q in eligible_questions if q.question_type == q_type and q.id not in used_q_ids]
            available_type_count = len(type_pool)

            if available_type_count < sec_count:
                insufficient_reasons.append(
                    f"Section '{sec_name}' requires {sec_count} '{q_type}' questions, but only {available_type_count} exist in selected pool."
                )
                continue

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
