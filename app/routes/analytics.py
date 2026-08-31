from flask import Blueprint, render_template
from app.models import db, Exam, Question, Attempt, Subject, Chapter
from sqlalchemy import func

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/')
def index():
    exams = Exam.query.order_by(Exam.date.asc()).all()

    # 1. Performance over time chart data
    exam_dates = [e.date.strftime('%b %d') if e.date else f'Exam #{e.id}' for e in exams]
    exam_percentages = [e.percentage for e in exams]
    exam_scores = [e.score for e in exams]

    # 2. Subject Performance Comparison
    subjects = Subject.query.all()
    subject_stats = []
    for s in subjects:
        s_attempts = Attempt.query.join(Question).join(Chapter).filter(Chapter.subject_id == s.id).all()
        total_a = len(s_attempts)
        correct_a = sum(1 for a in s_attempts if a.is_correct is True)
        wrong_a = sum(1 for a in s_attempts if a.is_correct is False)
        marks_lost = sum(a.max_marks - a.marks_awarded for a in s_attempts if a.is_correct is False)
        acc = round((correct_a / total_a) * 100, 1) if total_a > 0 else 0.0
        subject_stats.append({
            'name': s.name,
            'total': total_a,
            'correct': correct_a,
            'wrong': wrong_a,
            'accuracy': acc,
            'marks_lost': marks_lost
        })

    # 3. Chapter Performance Ranking
    chapters = Chapter.query.all()
    chapter_stats = []
    for c in chapters:
        c_attempts = Attempt.query.join(Question).filter(Question.chapter_id == c.id).all()
        total_a = len(c_attempts)
        if total_a > 0:
            correct_a = sum(1 for a in c_attempts if a.is_correct is True)
            wrong_a = sum(1 for a in c_attempts if a.is_correct is False)
            marks_lost = sum(a.max_marks - a.marks_awarded for a in c_attempts if a.is_correct is False)
            acc = round((correct_a / total_a) * 100, 1)
            chapter_stats.append({
                'subject': c.subject.name,
                'chapter': c.name,
                'accuracy': acc,
                'wrong_count': wrong_a,
                'marks_lost': marks_lost
            })
    # Sort chapters by lowest accuracy
    chapter_stats = sorted(chapter_stats, key=lambda x: x['accuracy'])

    # 4. Mistake Breakdown Category Analysis
    mistake_stats = db.session.query(
        Attempt.mistake_type,
        func.count(Attempt.id).label('count'),
        func.sum(Attempt.max_marks - Attempt.marks_awarded).label('marks_lost')
    ).filter(Attempt.mistake_type.isnot(None), Attempt.mistake_type != '')\
     .group_by(Attempt.mistake_type)\
     .order_by(func.count(Attempt.id).desc()).all()

    # 5. Difficulty Analysis
    diff_levels = ['Easy', 'Medium', 'Hard']
    difficulty_stats = []
    for diff in diff_levels:
        d_attempts = Attempt.query.join(Question).filter(Question.difficulty == diff).all()
        tot = len(d_attempts)
        wrong = sum(1 for a in d_attempts if a.is_correct is False)
        acc = round(((tot - wrong) / tot) * 100, 1) if tot > 0 else 0.0
        difficulty_stats.append({'difficulty': diff, 'total': tot, 'wrong': wrong, 'accuracy': acc})

    # 6. Confidence vs Correctness Misconception Matrix
    high_conf_wrong = Attempt.query.filter(Attempt.confidence == 'High', Attempt.is_correct == False).all()
    high_conf_correct = Attempt.query.filter(Attempt.confidence == 'High', Attempt.is_correct == True).count()
    low_conf_correct = Attempt.query.filter(Attempt.confidence == 'Low', Attempt.is_correct == True).count()
    low_conf_wrong = Attempt.query.filter(Attempt.confidence == 'Low', Attempt.is_correct == False).count()

    return render_template(
        'analytics/index.html',
        active_page='analytics',
        exam_dates=exam_dates,
        exam_percentages=exam_percentages,
        subject_stats=subject_stats,
        chapter_stats=chapter_stats,
        mistake_stats=mistake_stats,
        difficulty_stats=difficulty_stats,
        high_conf_wrong=high_conf_wrong,
        high_conf_correct=high_conf_correct,
        low_conf_correct=low_conf_correct,
        low_conf_wrong=low_conf_wrong
    )
