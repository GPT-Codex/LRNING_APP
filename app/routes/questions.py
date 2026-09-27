from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import db, Question, Subject, Chapter, Exam, Attempt, Tag, Option
from app.utils import save_uploaded_image, sort_subjects, sort_chapters

questions_bp = Blueprint('questions', __name__)

@questions_bp.route('/')
def bank():
    subject_id = request.args.get('subject_id', type=int)
    chapter_id = request.args.get('chapter_id', type=int)
    exam_id = request.args.get('exam_id', type=int)
    mistake_type = request.args.get('mistake_type')
    difficulty = request.args.get('difficulty')
    review_state = request.args.get('review_state')
    tag_name = request.args.get('tag')
    search_q = request.args.get('q', '').strip()

    query = Question.query

    if subject_id:
        query = query.join(Chapter).filter(Chapter.subject_id == subject_id)
    if chapter_id:
        query = query.filter(Question.chapter_id == chapter_id)
    if exam_id:
        query = query.join(Attempt).filter(Attempt.exam_id == exam_id)
    if mistake_type:
        query = query.join(Attempt).filter(Attempt.mistake_type == mistake_type)
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    if review_state:
        query = query.filter(Question.review_state == review_state)
    if tag_name:
        query = query.join(Question.tags).filter(Tag.name == tag_name)
    if search_q:
        query = query.filter(
            (Question.question_text.ilike(f'%{search_q}%')) |
            (Question.correct_answer.ilike(f'%{search_q}%')) |
            (Question.solution.ilike(f'%{search_q}%'))
        )

    # Distinct results to prevent duplicate cards when joining attempts
    questions = query.distinct().order_by(Question.created_at.desc()).all()

    subjects = Subject.query.order_by(Subject.name).all()
    chapters = Chapter.query.order_by(Chapter.name).all()
    exams = Exam.query.order_by(Exam.name).all()
    tags = Tag.query.order_by(Tag.name).all()

    return render_template(
        'questions/bank.html',
        active_page='question_bank' if not review_state == 'Wrong' else 'wrong_questions',
        questions=questions,
        subjects=subjects,
        chapters=chapters,
        exams=exams,
        tags=tags,
        mistake_types=Attempt.MISTAKE_TYPES,
        selected_subject_id=subject_id,
        selected_chapter_id=chapter_id,
        selected_exam_id=exam_id,
        selected_mistake_type=mistake_type,
        selected_difficulty=difficulty,
        selected_review_state=review_state,
        selected_tag=tag_name,
        search_q=search_q
    )

@questions_bp.route('/<int:question_id>')
def detail(question_id):
    question = Question.query.get_or_404(question_id)
    attempts = Attempt.query.filter_by(question_id=question.id).order_by(Attempt.created_at.asc()).all()
    return render_template(
        'questions/detail.html',
        active_page='question_bank',
        question=question,
        attempts=attempts
    )

@questions_bp.route('/new', methods=['GET', 'POST'])
def create_question():
    if request.method == 'POST':
        chapter_id = request.form.get('chapter_id')
        question_text = request.form.get('question_text', '').strip()
        question_type = request.form.get('question_type', 'MCQ')
        difficulty = request.form.get('difficulty', 'Medium')
        correct_answer = request.form.get('correct_answer', '').strip()
        solution = request.form.get('solution', '').strip()
        tags_str = request.form.get('tags', '').strip()

        image_file = request.files.get('question_image')
        uploaded_path = save_uploaded_image(image_file) if image_file else None

        question = Question(
            chapter_id=int(chapter_id) if chapter_id else None,
            question_text=question_text,
            question_type=question_type,
            difficulty=difficulty,
            correct_answer=correct_answer,
            solution=solution,
            image_path=uploaded_path,
            review_state='New'
        )
        db.session.add(question)
        db.session.commit()

        # Handle Options
        if question_type in ['MCQ', 'Multiple Select']:
            idx = 0
            while f'option_text_{idx}' in request.form or f'option_image_{idx}' in request.files:
                opt_text = request.form.get(f'option_text_{idx}', '').strip()
                opt_img_file = request.files.get(f'option_image_{idx}')
                opt_img_path = save_uploaded_image(opt_img_file) if opt_img_file else None

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
            for tname in tag_names:
                tag = Tag.query.filter_by(name=tname).first() or Tag(name=tname)
                question.tags.append(tag)

        db.session.commit()

        flash('New question added to library.', 'success')
        return redirect(url_for('questions.detail', question_id=question.id))

    subjects = sort_subjects(Subject.query.all())
    subjects_data = [{
        'id': s.id,
        'name': s.name,
        'sorted_chapters': [{'id': c.id, 'name': c.name} for c in sort_chapters(s.chapters)]
    } for s in subjects]
    return render_template('questions/form.html', active_page='question_bank', subjects=subjects, subjects_data=subjects_data)
