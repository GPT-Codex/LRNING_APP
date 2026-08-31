from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from app.models import db, Subject, Chapter, Exam, Question, Attempt, Tag
from app.utils import export_all_data_json, export_attempts_csv, export_exams_csv, export_questions_csv
from sqlalchemy import func

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def dashboard():
    recent_exams = Exam.query.order_by(Exam.date.desc()).limit(5).all()
    total_exams = Exam.query.count()
    total_questions = Question.query.count()
    total_attempts = Attempt.query.count()

    # Review queue items (questions needing review)
    due_review_questions = Question.query.filter(Question.review_state.in_(['Wrong', 'Learning', 'Reviewing'])).all()

    # Mistake distribution breakdown
    mistake_counts = db.session.query(
        Attempt.mistake_type,
        func.count(Attempt.id)
    ).filter(Attempt.mistake_type.isnot(None), Attempt.mistake_type != '')\
     .group_by(Attempt.mistake_type)\
     .order_by(func.count(Attempt.id).desc()).all()

    # Weak areas calculation: Chapters with lowest accuracy or highest wrong count
    chapter_stats = []
    chapters = Chapter.query.all()
    for ch in chapters:
        ch_attempts = Attempt.query.join(Question).filter(Question.chapter_id == ch.id).all()
        if ch_attempts:
            correct_cnt = sum(1 for a in ch_attempts if a.is_correct is True)
            total_cnt = len(ch_attempts)
            acc = round((correct_cnt / total_cnt) * 100, 1)
            wrong_cnt = sum(1 for a in ch_attempts if a.is_correct is False)
            if wrong_cnt > 0 or acc < 70:
                chapter_stats.append({
                    'subject': ch.subject.name,
                    'chapter': ch.name,
                    'accuracy': acc,
                    'wrong_count': wrong_cnt,
                    'total': total_cnt
                })

    # Sort weak areas by accuracy ascending
    weak_areas = sorted(chapter_stats, key=lambda x: x['accuracy'])[:5]

    return render_template(
        'dashboard.html',
        active_page='dashboard',
        recent_exams=recent_exams,
        total_exams=total_exams,
        total_questions=total_questions,
        total_attempts=total_attempts,
        due_review_count=len(due_review_questions),
        mistake_counts=dict(mistake_counts),
        weak_areas=weak_areas
    )

@main_bp.route('/subjects', methods=['GET', 'POST'])
def subjects_list():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_subject':
            name = request.form.get('name', '').strip()
            if name:
                if Subject.query.filter_by(name=name).first():
                    flash(f'Subject "{name}" already exists.', 'error')
                else:
                    subj = Subject(name=name)
                    db.session.add(subj)
                    db.session.commit()
                    flash(f'Subject "{name}" created successfully.', 'success')
        elif action == 'add_chapter':
            subject_id = request.form.get('subject_id')
            name = request.form.get('name', '').strip()
            if subject_id and name:
                chap = Chapter(subject_id=subject_id, name=name)
                db.session.add(chap)
                db.session.commit()
                flash(f'Chapter "{name}" added successfully.', 'success')
        elif action == 'delete_subject':
            subject_id = request.form.get('subject_id')
            subj = Subject.query.get_or_404(subject_id)
            db.session.delete(subj)
            db.session.commit()
            flash('Subject deleted.', 'success')
        elif action == 'delete_chapter':
            chapter_id = request.form.get('chapter_id')
            chap = Chapter.query.get_or_404(chapter_id)
            db.session.delete(chap)
            db.session.commit()
            flash('Chapter deleted.', 'success')
        return redirect(url_for('main.subjects_list'))

    subjects = Subject.query.order_by(Subject.name).all()
    return render_template('subjects.html', active_page='subjects', subjects=subjects)

@main_bp.route('/export')
def export_page():
    return render_template('export.html', active_page='export')

@main_bp.route('/export/json')
def export_json():
    json_data = export_all_data_json()
    return Response(
        json_data,
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment;filename=mistake_tracker_export.json'}
    )

@main_bp.route('/export/csv/attempts')
def export_attempts():
    csv_data = export_attempts_csv()
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=attempts.csv'}
    )

@main_bp.route('/export/csv/exams')
def export_exams():
    csv_data = export_exams_csv()
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=exams.csv'}
    )

@main_bp.route('/export/csv/questions')
def export_questions():
    csv_data = export_questions_csv()
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=questions.csv'}
    )
