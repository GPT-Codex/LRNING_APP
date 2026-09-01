from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import db, Exam, Question, Attempt, Subject, Chapter, Tag, Option
from app.utils import save_uploaded_image, parse_optional_int, parse_optional_float
from datetime import datetime

exams_bp = Blueprint('exams', __name__)

@exams_bp.route('/')
def list_exams():
    exams = Exam.query.order_by(Exam.date.desc()).all()
    return render_template('exams/list.html', active_page='exams', exams=exams)

@exams_bp.route('/create', methods=['GET', 'POST'])
def create_exam():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        date_str = request.form.get('date')
        total_marks = float(request.form.get('total_marks') or 0.0)
        score = float(request.form.get('score') or 0.0)
        center_rank = request.form.get('center_rank')
        institution_rank = request.form.get('institution_rank')
        notes = request.form.get('notes')

        if not name:
            flash('Exam name is required.', 'error')
            return redirect(url_for('exams.create_exam'))

        # Validation checks
        if score > total_marks and total_marks > 0:
            flash('Score cannot exceed total marks.', 'error')
            return redirect(url_for('exams.create_exam'))

        exam_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()

        try:
            c_rank = parse_optional_int(center_rank)
            i_rank = parse_optional_int(institution_rank)
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('exams.create_exam'))

        exam = Exam(
            name=name,
            date=exam_date,
            total_marks=total_marks,
            score=score,
            center_rank=c_rank,
            institution_rank=i_rank,
            notes=notes
        )
        db.session.add(exam)
        db.session.commit()

        flash(f'Exam "{name}" created! Entering Exam Workspace to log questions.', 'success')
        return redirect(url_for('exams.workspace', exam_id=exam.id, q_index=1))

    subjects = Subject.query.all()
    return render_template('exams/create.html', active_page='new_exam', subjects=subjects)

@exams_bp.route('/<int:exam_id>/workspace')
def workspace(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    q_index = request.args.get('q_index', 1, type=int)

    # Get attempts for this exam ordered by id
    attempts = Attempt.query.filter_by(exam_id=exam.id).order_by(Attempt.id.asc()).all()

    current_attempt = attempts[q_index - 1] if 0 < q_index <= len(attempts) else None
    current_question = current_attempt.question if current_attempt else None

    subjects = Subject.query.order_by(Subject.name).all()
    chapters = Chapter.query.order_by(Chapter.name).all()
    all_tags = Tag.query.order_by(Tag.name).all()

    return render_template(
        'exams/workspace.html',
        active_page='exams',
        exam=exam,
        attempts=attempts,
        current_attempt=current_attempt,
        current_question=current_question,
        q_index=q_index,
        subjects=subjects,
        chapters=chapters,
        all_tags=all_tags,
        mistake_types=Attempt.MISTAKE_TYPES
    )

@exams_bp.route('/<int:exam_id>/workspace/save', methods=['POST'])
def workspace_save(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    q_index = request.form.get('q_index', 1, type=int)
    nav_action = request.form.get('nav_action', 'next') # 'next', 'prev', 'finish'

    attempt_id = request.form.get('attempt_id')
    chapter_id = request.form.get('chapter_id')
    question_text = request.form.get('question_text', '').strip()
    question_type = request.form.get('question_type', 'MCQ')
    difficulty = request.form.get('difficulty', 'Medium')
    correct_answer = request.form.get('correct_answer', '').strip()
    solution = request.form.get('solution', '').strip()

    user_answer = request.form.get('user_answer', '').strip()
    is_correct_val = request.form.get('is_correct') # 'true', 'false', 'unattempted'
    marks_awarded = float(request.form.get('marks_awarded') or 0.0)
    max_marks = float(request.form.get('max_marks') or 4.0)

    try:
        time_taken_seconds = parse_optional_int(request.form.get('time_taken_seconds'))
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('exams.workspace', exam_id=exam.id, q_index=q_index))
    confidence = request.form.get('confidence', 'Medium')
    mistake_type = request.form.get('mistake_type')
    mistake_reason = request.form.get('mistake_reason', '').strip()
    tags_str = request.form.get('tags', '').strip()

    # Image upload
    image_file = request.files.get('question_image')
    uploaded_path = save_uploaded_image(image_file) if image_file else None

    # Handle Boolean or None for is_correct
    is_correct = True if is_correct_val == 'true' else (False if is_correct_val == 'false' else None)

    # Automatically set question review state based on attempt correctness
    review_state = 'Wrong' if is_correct is False else ('Mastered' if is_correct is True else 'New')

    if attempt_id:
        attempt = Attempt.query.get(attempt_id)
        question = attempt.question
    else:
        question = Question()
        db.session.add(question)
        db.session.flush() # Ensure question.id is generated
        attempt = Attempt(question_id=question.id, exam_id=exam.id, attempt_type='EXAM')
        db.session.add(attempt)

    # Update Question fields
    if chapter_id:
        question.chapter_id = int(chapter_id)
    question.question_text = question_text
    question.question_type = question_type
    question.difficulty = difficulty
    question.correct_answer = correct_answer
    question.solution = solution
    question.review_state = review_state
    if uploaded_path:
        question.image_path = uploaded_path

    # Process options if MCQ or Multiple Select
    if question_type in ['MCQ', 'Multiple Select']:
        Option.query.filter_by(question_id=question.id).delete()
        idx = 0
        while f'option_text_{idx}' in request.form or f'option_image_{idx}' in request.files or f'option_existing_image_{idx}' in request.form:
            opt_text = request.form.get(f'option_text_{idx}', '').strip()
            opt_img_file = request.files.get(f'option_image_{idx}')
            existing_img = request.form.get(f'option_existing_image_{idx}', '').strip()
            remove_img = request.form.get(f'option_remove_image_{idx}') == '1'

            opt_img_path = None
            if opt_img_file and opt_img_file.filename != '':
                opt_img_path = save_uploaded_image(opt_img_file)
            elif not remove_img and existing_img:
                opt_img_path = existing_img

            if opt_text or opt_img_path:
                opt_label = chr(65 + idx) if idx < 26 else str(idx + 1)
                opt_correct = bool(request.form.get(f'option_correct_{idx}'))
                option = Option(
                    question_id=question.id,
                    label=opt_label,
                    text=opt_text or None,
                    image_path=opt_img_path,
                    is_correct=opt_correct
                )
                db.session.add(option)
            idx += 1

    # Handle Tags
    if tags_str:
        tag_names = [t.strip().lower() for t in tags_str.split(',') if t.strip()]
        tag_objs = []
        for tname in tag_names:
            tag = Tag.query.filter_by(name=tname).first()
            if not tag:
                tag = Tag(name=tname)
                db.session.add(tag)
            tag_objs.append(tag)
        question.tags = tag_objs

    # Update Attempt fields
    attempt.user_answer = user_answer
    attempt.is_correct = is_correct
    attempt.marks_awarded = marks_awarded
    attempt.max_marks = max_marks
    attempt.time_taken_seconds = time_taken_seconds
    attempt.confidence = confidence
    attempt.mistake_type = mistake_type if is_correct is False else None
    attempt.mistake_reason = mistake_reason if is_correct is False else None

    db.session.commit()

    all_attempts = Attempt.query.filter_by(exam_id=exam.id).all()
    exam.total_marks = sum(a.max_marks for a in all_attempts)
    exam.score = sum(a.marks_awarded for a in all_attempts)
    db.session.commit()

    if nav_action == 'finish':
        flash('Exam questions logging completed!', 'success')
        return redirect(url_for('exams.exam_result', exam_id=exam.id))
    elif nav_action == 'prev':
        next_q = max(1, q_index - 1)
    else:
        next_q = q_index + 1

    return redirect(url_for('exams.workspace', exam_id=exam.id, q_index=next_q))

@exams_bp.route('/<int:exam_id>/result')
def exam_result(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    attempts = Attempt.query.filter_by(exam_id=exam.id).all()

    correct_cnt = sum(1 for a in attempts if a.is_correct is True)
    wrong_cnt = sum(1 for a in attempts if a.is_correct is False)
    unattempted_cnt = sum(1 for a in attempts if a.is_correct is None)
    total_cnt = len(attempts)
    marks_lost = sum(a.max_marks - a.marks_awarded for a in attempts if a.is_correct is False)
    recorded_times = [a.time_taken_seconds for a in attempts if a.time_taken_seconds is not None]
    avg_time = round(sum(recorded_times) / len(recorded_times), 1) if recorded_times else None
    accuracy = round((correct_cnt / total_cnt) * 100, 1) if total_cnt > 0 else 0

    return render_template(
        'exams/result.html',
        active_page='exams',
        exam=exam,
        attempts=attempts,
        correct_cnt=correct_cnt,
        wrong_cnt=wrong_cnt,
        unattempted_cnt=unattempted_cnt,
        total_cnt=total_cnt,
        marks_lost=marks_lost,
        avg_time=avg_time,
        accuracy=accuracy
    )
