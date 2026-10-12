from flask import Blueprint, render_template, request, redirect, url_for, flash
import json
from app.models import db, Question, Attempt
from app.utils import parse_optional_int, evaluate_answer
from datetime import datetime

review_bp = Blueprint('review', __name__)

@review_bp.route('/')
def queue():
    state_filter = request.args.get('state')

    # Query logged attempts or questions logged in exams needing review
    query = Attempt.query.filter(Attempt.exam_id.isnot(None))
    if state_filter:
        query = query.filter(Attempt.review_state == state_filter)
    else:
        query = query.filter(Attempt.review_state.in_(['Wrong', 'Learning', 'Reviewing']))

    due_attempts = query.order_by(Attempt.created_at.desc()).all()

    wrong_count = Attempt.query.filter(Attempt.exam_id.isnot(None), Attempt.review_state == 'Wrong').count()
    learning_count = Attempt.query.filter(Attempt.exam_id.isnot(None), Attempt.review_state == 'Learning').count()
    reviewing_count = Attempt.query.filter(Attempt.exam_id.isnot(None), Attempt.review_state == 'Reviewing').count()
    mastered_count = Attempt.query.filter(Attempt.exam_id.isnot(None), Attempt.review_state == 'Mastered').count()

    return render_template(
        'review/queue.html',
        active_page='review',
        due_attempts=due_attempts,
        wrong_count=wrong_count,
        learning_count=learning_count,
        reviewing_count=reviewing_count,
        mastered_count=mastered_count,
        current_filter=state_filter
    )

@review_bp.route('/session/<int:attempt_id>', methods=['GET', 'POST'])
def session(attempt_id):
    target_att = Attempt.query.get_or_404(attempt_id)
    question = target_att.question

    if request.method == 'POST':
        user_answer = request.form.get('user_answer', '').strip()
        user_answers_list = request.form.getlist('user_answer_multi')
        if user_answers_list:
            user_answer = json.dumps(sorted(user_answers_list))

        time_taken_seconds = parse_optional_int(request.form.get('time_taken_seconds'))
        confidence = request.form.get('confidence', 'Medium')
        mistake_type = request.form.get('mistake_type')
        mistake_reason = request.form.get('mistake_reason', '').strip()

        is_correct = evaluate_answer(question, user_answer)

        # Create new Attempt record of type 'REVIEW' for Logged Exam
        new_att = Attempt(
            question_id=question.id,
            exam_id=target_att.exam_id,
            attempt_type='REVIEW',
            user_answer=user_answer,
            is_correct=is_correct,
            marks_awarded=4.0 if is_correct else 0.0,
            max_marks=4.0,
            time_taken_seconds=time_taken_seconds,
            confidence=confidence,
            mistake_type=mistake_type if not is_correct else None,
            mistake_reason=mistake_reason if not is_correct else None
        )
        db.session.add(new_att)

        # Update target_att review_state
        if is_correct:
            if target_att.review_state in ['Wrong', 'New']:
                target_att.review_state = 'Learning'
            elif target_att.review_state == 'Learning':
                target_att.review_state = 'Reviewing'
            elif target_att.review_state == 'Reviewing':
                target_att.review_state = 'Mastered'
        else:
            target_att.review_state = 'Wrong'

        db.session.commit()

        next_att = Attempt.query.filter(
            Attempt.exam_id.isnot(None),
            Attempt.review_state.in_(['Wrong', 'Learning', 'Reviewing']),
            Attempt.id != target_att.id
        ).first()

        return render_template(
            'review/session.html',
            active_page='review',
            target_att=target_att,
            question=question,
            is_correct=is_correct,
            submitted_answer=user_answer,
            submitted=True,
            next_att=next_att,
            mistake_types=Attempt.MISTAKE_TYPES
        )

    return render_template(
        'review/session.html',
        active_page='review',
        target_att=target_att,
        question=question,
        submitted=False,
        mistake_types=Attempt.MISTAKE_TYPES
    )
