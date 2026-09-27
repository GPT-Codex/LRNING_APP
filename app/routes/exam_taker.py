import json
import random
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import db, Subject, Chapter, Question, Attempt, ExamTemplate, ExamSession, ExamSessionResponse
from app.services.exam_generator import validate_and_generate_exam
from app.utils import sort_subjects, sort_chapters, parse_optional_int

exam_taker_bp = Blueprint('exam_taker', __name__)

@exam_taker_bp.route('/')
def landing():
    templates = ExamTemplate.query.order_by(ExamTemplate.is_default.desc(), ExamTemplate.created_at.desc()).all()
    past_sessions = ExamSession.query.order_by(ExamSession.created_at.desc()).limit(5).all()
    return render_template('exam_taker/landing.html', active_page='exam_taker', templates=templates, past_sessions=past_sessions)

@exam_taker_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        template_id = request.form.get('template_id')
        scope_type = request.form.get('scope_type', 'All Mixed') # Subjectwise, Chapterwise, All Mixed
        difficulty_mode = request.form.get('difficulty_mode', 'Medium')
        duration_minutes = int(request.form.get('duration_minutes') or 60)
        total_questions = int(request.form.get('total_questions') or 30)

        # Parse selected subjects & chapters
        selected_subject_ids = [int(sid) for sid in request.form.getlist('selected_subjects') if sid.isdigit()]
        selected_chapter_ids = [int(cid) for sid, cids in request.form.items() if sid.startswith('selected_chapters_') for cid in request.form.getlist(sid) if cid.isdigit()]

        tmpl = ExamTemplate.query.get(template_id) if template_id else ExamTemplate.query.filter_by(is_default=True).first()
        pattern_sections = json.loads(tmpl.pattern_json) if tmpl else [
            {"name": "Section A: Single Correct MCQ", "type": "MCQ", "start": 1, "end": 20, "count": 20},
            {"name": "Section B: Numerical Answer", "type": "Numerical", "start": 21, "end": 25, "count": 5},
            {"name": "Section C: Multiple Correct MCQ", "type": "Multiple Select", "start": 26, "end": 30, "count": 5}
        ]

        # Generate / validate question pool
        success, gen_data, err_details = validate_and_generate_exam(
            scope_type=scope_type,
            selected_subject_ids=selected_subject_ids,
            selected_chapter_ids=selected_chapter_ids,
            difficulty_mode=difficulty_mode,
            pattern_sections=pattern_sections,
            total_questions=total_questions
        )

        if not success:
            flash(err_details.get('message', 'Not enough eligible questions in selected scope.'), 'error')
            subjects = sort_subjects(Subject.query.all())
            for s in subjects:
                s.sorted_chapters = sort_chapters(s.chapters)
            templates = ExamTemplate.query.all()
            return render_template(
                'exam_taker/setup.html',
                active_page='exam_taker',
                subjects=subjects,
                templates=templates,
                scope_type=scope_type,
                difficulty_mode=difficulty_mode,
                err_details=err_details
            )

        # Create session in 'Created' state ready for preview
        session = ExamSession(
            template_id=tmpl.id if tmpl else None,
            name=f"{scope_type} Practice Exam",
            duration_minutes=duration_minutes,
            total_questions=total_questions,
            scope_type=scope_type,
            selected_subjects_json=json.dumps(selected_subject_ids),
            selected_chapters_json=json.dumps(selected_chapter_ids),
            difficulty_mode=difficulty_mode,
            pattern_json=json.dumps(pattern_sections),
            questions_json=json.dumps(gen_data['question_ids']),
            status='Created'
        )
        db.session.add(session)
        db.session.commit()

        return redirect(url_for('exam_taker.preview', session_id=session.id))

    subjects = sort_subjects(Subject.query.all())
    for s in subjects:
        s.sorted_chapters = sort_chapters(s.chapters)
    templates = ExamTemplate.query.all()
    return render_template('exam_taker/setup.html', active_page='exam_taker', subjects=subjects, templates=templates)

@exam_taker_bp.route('/preview/<int:session_id>')
def preview(session_id):
    session = ExamSession.query.get_or_404(session_id)
    q_ids = json.loads(session.questions_json) if session.questions_json else []
    questions = [Question.query.get(qid) for qid in q_ids if Question.query.get(qid)]

    # Breakdown by subject and chapter
    subject_counts = {}
    for q in questions:
        sname = q.chapter.subject.name if q.chapter and q.chapter.subject else "General"
        subject_counts[sname] = subject_counts.get(sname, 0) + 1

    return render_template('exam_taker/preview.html', active_page='exam_taker', session=session, subject_counts=subject_counts)

@exam_taker_bp.route('/start/<int:session_id>', methods=['POST'])
def start_exam(session_id):
    session = ExamSession.query.get_or_404(session_id)
    session.status = 'Active'
    session.start_time = datetime.utcnow()
    session.end_time = datetime.utcnow() + timedelta(minutes=session.duration_minutes)

    # Initialize empty response records
    q_ids = json.loads(session.questions_json) if session.questions_json else []
    for qid in q_ids:
        resp = ExamSessionResponse(session_id=session.id, question_id=qid)
        db.session.add(resp)

    db.session.commit()
    return redirect(url_for('exam_taker.session', session_id=session.id))

@exam_taker_bp.route('/session/<int:session_id>')
def session(session_id):
    session = ExamSession.query.get_or_404(session_id)

    # Auto timeout check
    if session.status == 'Active' and datetime.utcnow() > session.end_time:
        return redirect(url_for('exam_taker.submit_exam', session_id=session.id))

    q_index = request.args.get('q_index', 1, type=int)
    q_ids = json.loads(session.questions_json) if session.questions_json else []

    responses = ExamSessionResponse.query.filter_by(session_id=session.id).all()
    response_map = {r.question_id: r for r in responses}

    current_qid = q_ids[q_index - 1] if 0 < q_index <= len(q_ids) else None
    current_q = Question.query.get(current_qid) if current_qid else None
    current_resp = response_map.get(current_qid) if current_qid else None

    # Calculate remaining time in seconds
    remaining_seconds = max(0, int((session.end_time - datetime.utcnow()).total_seconds())) if session.end_time else session.duration_minutes * 60

    return render_template(
        'exam_taker/session.html',
        active_page='exam_taker',
        session=session,
        q_ids=q_ids,
        q_index=q_index,
        current_q=current_q,
        current_resp=current_resp,
        responses=response_map,
        remaining_seconds=remaining_seconds
    )

@exam_taker_bp.route('/session/<int:session_id>/answer', methods=['POST'])
def save_answer(session_id):
    session = ExamSession.query.get_or_404(session_id)
    question_id = request.form.get('question_id', type=int)
    q_index = request.form.get('q_index', type=int)
    nav_action = request.form.get('nav_action', 'next')
    user_answer = request.form.get('user_answer', '').strip()

    resp = ExamSessionResponse.query.filter_by(session_id=session.id, question_id=question_id).first()
    if resp:
        resp.user_answer = user_answer
        db.session.commit()

    if nav_action == 'submit':
        return redirect(url_for('exam_taker.submit_exam', session_id=session.id))

    q_ids = json.loads(session.questions_json) if session.questions_json else []
    next_q = q_index + 1 if nav_action == 'next' else max(1, q_index - 1)
    return redirect(url_for('exam_taker.session', session_id=session.id, q_index=next_q))

@exam_taker_bp.route('/session/<int:session_id>/submit', methods=['GET', 'POST'])
def submit_exam(session_id):
    session = ExamSession.query.get_or_404(session_id)
    if session.status != 'Submitted':
        session.status = 'Submitted'
        session.submit_time = datetime.utcnow()

        responses = ExamSessionResponse.query.filter_by(session_id=session.id).all()
        total_score = 0.0
        total_max = len(responses) * 4.0

        for r in responses:
            q = r.question
            if not r.user_answer:
                r.is_correct = None
                r.marks_awarded = 0.0
            else:
                # Basic string comparison matching answer
                is_correct = (r.user_answer.strip().lower() == (q.correct_answer or '').strip().lower())
                r.is_correct = is_correct
                r.marks_awarded = 4.0 if is_correct else -1.0
                total_score += r.marks_awarded

                # Automatically record attempt in history for review queue integration
                att = Attempt(
                    question_id=q.id,
                    attempt_type='EXAM',
                    user_answer=r.user_answer,
                    is_correct=is_correct,
                    marks_awarded=r.marks_awarded,
                    max_marks=4.0,
                    time_taken_seconds=None
                )
                db.session.add(att)
                q.review_state = 'Mastered' if is_correct else 'Wrong'

        session.score = total_score
        session.total_marks = total_max
        db.session.commit()

        flash('Exam session submitted successfully!', 'success')

    return redirect(url_for('exam_taker.session_result', session_id=session.id))

@exam_taker_bp.route('/session/<int:session_id>/result')
def session_result(session_id):
    session = ExamSession.query.get_or_404(session_id)
    responses = ExamSessionResponse.query.filter_by(session_id=session.id).all()

    correct_cnt = sum(1 for r in responses if r.is_correct is True)
    wrong_cnt = sum(1 for r in responses if r.is_correct is False)
    unattempted_cnt = sum(1 for r in responses if r.is_correct is None)
    accuracy = round((correct_cnt / len(responses)) * 100, 1) if responses else 0.0

    return render_template(
        'exam_taker/result.html',
        active_page='exam_taker',
        session=session,
        responses=responses,
        correct_cnt=correct_cnt,
        wrong_cnt=wrong_cnt,
        unattempted_cnt=unattempted_cnt,
        accuracy=accuracy
    )

@exam_taker_bp.route('/templates', methods=['GET', 'POST'])
def templates():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            name = request.form.get('name', '').strip()
            duration = int(request.form.get('duration_minutes') or 60)
            questions_cnt = int(request.form.get('total_questions') or 30)

            pattern = [
                {"name": "Section A: Single Correct MCQ", "type": "MCQ", "start": 1, "end": 20, "count": 20},
                {"name": "Section B: Numerical Answer", "type": "Numerical", "start": 21, "end": 25, "count": 5},
                {"name": "Section C: Multiple Correct MCQ", "type": "Multiple Select", "start": 26, "end": 30, "count": 5}
            ]
            diff = {
                "Easy": {"Easy": 10, "Medium": 5, "Hard": 0},
                "Medium": {"Easy": 12, "Medium": 15, "Hard": 18},
                "Hard": {"Easy": 8, "Medium": 10, "Hard": 12}
            }

            tmpl = ExamTemplate(
                name=name,
                duration_minutes=duration,
                total_questions=questions_cnt,
                pattern_json=json.dumps(pattern),
                difficulty_json=json.dumps(diff),
                is_default=False
            )
            db.session.add(tmpl)
            db.session.commit()
            flash(f'Custom template "{name}" created.', 'success')
        elif action == 'delete':
            tmpl_id = request.form.get('template_id')
            tmpl = ExamTemplate.query.get(tmpl_id)
            if tmpl and not tmpl.is_default:
                db.session.delete(tmpl)
                db.session.commit()
                flash('Template deleted.', 'success')
        return redirect(url_for('exam_taker.templates'))

    all_templates = ExamTemplate.query.order_by(ExamTemplate.is_default.desc(), ExamTemplate.created_at.desc()).all()
    return render_template('exam_taker/templates.html', active_page='exam_taker', templates=all_templates)
