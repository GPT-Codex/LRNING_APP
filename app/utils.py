import os
import re
import uuid
import csv
import io
import json
from datetime import datetime, date
from werkzeug.utils import secure_filename
from flask import current_app
from app.models import db, Subject, Chapter, Exam, Question, Attempt, Tag, Option

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

def natural_sort_key(text):
    if not text:
        return []
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(text))]

def sort_chapters(chapters):
    return sorted(chapters, key=lambda c: (c.priority if c.priority is not None else 1, natural_sort_key(c.name)))

def sort_subjects(subjects):
    return sorted(subjects, key=lambda s: natural_sort_key(s.name))

def parse_optional_int(val):
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    val_str = str(val).strip()
    if val_str in ('', '-', '—', 'none', 'null'):
        return None
    try:
        return int(float(val_str))
    except ValueError:
        raise ValueError(f"Invalid integer value: {val}")

def parse_optional_float(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    if val_str in ('', '-', '—', 'none', 'null'):
        return None
    try:
        return float(val_str)
    except ValueError:
        raise ValueError(f"Invalid numeric value: {val}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_image(file):
    if not file or file.filename == '':
        return None
    if allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        return f"uploads/{unique_filename}"
    return None

def json_serializable(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def export_all_data_json():
    subjects = Subject.query.all()
    exams = Exam.query.all()
    questions = Question.query.all()
    attempts = Attempt.query.all()

    data = {
        'exported_at': datetime.utcnow().isoformat(),
        'subjects': [{
            'id': s.id,
            'name': s.name,
            'chapters': [{'id': c.id, 'name': c.name} for c in s.chapters]
        } for s in subjects],
        'exams': [{
            'id': e.id,
            'name': e.name,
            'date': e.date.isoformat() if e.date else None,
            'total_marks': e.total_marks,
            'score': e.score,
            'institution_rank': e.institution_rank,
            'center_rank': e.center_rank,
            'notes': e.notes,
            'created_at': e.created_at.isoformat() if e.created_at else None
        } for e in exams],
        'questions': [{
            'id': q.id,
            'chapter_id': q.chapter_id,
            'subject_name': q.chapter.subject.name if q.chapter and q.chapter.subject else None,
            'chapter_name': q.chapter.name if q.chapter else None,
            'question_text': q.question_text,
            'question_type': q.question_type,
            'difficulty': q.difficulty,
            'correct_answer': q.correct_answer,
            'solution': q.solution,
            'source': q.source,
            'image_path': q.image_path,
            'review_state': q.review_state,
            'tags': [t.name for t in q.tags],
            'options': [{'label': o.label, 'text': o.text, 'is_correct': o.is_correct} for o in q.options],
            'created_at': q.created_at.isoformat() if q.created_at else None
        } for q in questions],
        'attempts': [{
            'id': a.id,
            'question_id': a.question_id,
            'exam_id': a.exam_id,
            'attempt_type': a.attempt_type,
            'user_answer': a.user_answer,
            'is_correct': a.is_correct,
            'marks_awarded': a.marks_awarded,
            'max_marks': a.max_marks,
            'time_taken_seconds': a.time_taken_seconds,
            'confidence': a.confidence,
            'mistake_type': a.mistake_type,
            'mistake_reason': a.mistake_reason,
            'notes': a.notes,
            'created_at': a.created_at.isoformat() if a.created_at else None
        } for a in attempts]
    }
    return json.dumps(data, indent=2)

def export_attempts_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Attempt ID', 'Date', 'Question ID', 'Exam Name', 'Subject', 'Chapter',
        'Type', 'Is Correct', 'Marks Awarded', 'Max Marks', 'Time (s)',
        'Confidence', 'Mistake Type', 'Mistake Reason'
    ])
    attempts = Attempt.query.order_by(Attempt.created_at.desc()).all()
    for a in attempts:
        q = a.question
        writer.writerow([
            a.id,
            a.created_at.strftime('%Y-%m-%d %H:%M') if a.created_at else '',
            a.question_id,
            a.exam.name if a.exam else 'Standalone Review',
            q.chapter.subject.name if q and q.chapter and q.chapter.subject else '',
            q.chapter.name if q and q.chapter else '',
            a.attempt_type,
            a.is_correct,
            a.marks_awarded,
            a.max_marks,
            a.time_taken_seconds or 0,
            a.confidence or '',
            a.mistake_type or '',
            a.mistake_reason or ''
        ])
    return output.getvalue()

def export_exams_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Exam ID', 'Exam Name', 'Date', 'Score', 'Total Marks', 'Percentage',
        'Center Rank', 'Institution Rank', 'Notes'
    ])
    exams = Exam.query.order_by(Exam.date.desc()).all()
    for e in exams:
        writer.writerow([
            e.id, e.name, e.date.strftime('%Y-%m-%d') if e.date else '',
            e.score, e.total_marks, f"{e.percentage}%",
            e.center_rank or '', e.institution_rank or '', e.notes or ''
        ])
    return output.getvalue()

def export_questions_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Question ID', 'Subject', 'Chapter', 'Type', 'Difficulty',
        'Review State', 'Question Text', 'Correct Answer', 'Tags'
    ])
    questions = Question.query.all()
    for q in questions:
        writer.writerow([
            q.id,
            q.chapter.subject.name if q.chapter and q.chapter.subject else '',
            q.chapter.name if q.chapter else '',
            q.question_type,
            q.difficulty,
            q.review_state,
            q.question_text or '',
            q.correct_answer or '',
            ', '.join([t.name for t in q.tags])
        ])
    return output.getvalue()
