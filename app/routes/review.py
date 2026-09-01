from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import db, Question, Attempt
from app.utils import parse_optional_int
from datetime import datetime

review_bp = Blueprint('review', __name__)

@review_bp.route('/')
def queue():
    # Questions needing review: Wrong, Learning, Reviewing
    state_filter = request.args.get('state')

    query = Question.query
    if state_filter:
        query = query.filter_by(review_state=state_filter)
    else:
        query = query.filter(Question.review_state.in_(['Wrong', 'Learning', 'Reviewing']))

    due_questions = query.order_by(Question.created_at.desc()).all()

    # Stats breakdown
    wrong_count = Question.query.filter_by(review_state='Wrong').count()
    learning_count = Question.query.filter_by(review_state='Learning').count()
    reviewing_count = Question.query.filter_by(review_state='Reviewing').count()
    mastered_count = Question.query.filter_by(review_state='Mastered').count()

    return render_template(
        'review/queue.html',
        active_page='review',
        due_questions=due_questions,
        wrong_count=wrong_count,
        learning_count=learning_count,
        reviewing_count=reviewing_count,
        mastered_count=mastered_count,
        current_filter=state_filter
    )

@review_bp.route('/session/<int:question_id>', methods=['GET', 'POST'])
def session(question_id):
    question = Question.query.get_or_404(question_id)
    latest_att = question.latest_attempt

    if request.method == 'POST':
        user_answer = request.form.get('user_answer', '').strip()
        is_correct_val = request.form.get('is_correct') # 'true' or 'false'
        try:
            time_taken_seconds = parse_optional_int(request.form.get('time_taken_seconds'))
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('review.session', question_id=question.id))
        confidence = request.form.get('confidence', 'Medium')
        mistake_type = request.form.get('mistake_type')
        mistake_reason = request.form.get('mistake_reason', '').strip()

        is_correct = True if is_correct_val == 'true' else False

        # Create new Attempt record of type 'REVIEW'
        new_att = Attempt(
            question_id=question.id,
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

        # Update Review State based on progression
        if is_correct:
            if question.review_state in ['Wrong', 'New']:
                question.review_state = 'Learning'
            elif question.review_state == 'Learning':
                question.review_state = 'Reviewing'
            elif question.review_state == 'Reviewing':
                question.review_state = 'Mastered'
        else:
            # Drop back to Wrong / Learning if incorrect
            question.review_state = 'Wrong'

        db.session.commit()

        if is_correct:
            flash(f'Great job! Question review recorded as Correct. New status: {question.review_state}', 'success')
        else:
            flash('Review recorded as Wrong. Question remains in review queue.', 'error')

        # Find next question in review queue or return to queue
        next_q = Question.query.filter(Question.review_state.in_(['Wrong', 'Learning', 'Reviewing']), Question.id != question.id).first()
        if next_q:
            return redirect(url_for('review.session', question_id=next_q.id))
        return redirect(url_for('review.queue'))

    return render_template(
        'review/session.html',
        active_page='review',
        question=question,
        latest_att=latest_att,
        mistake_types=Attempt.MISTAKE_TYPES
    )
