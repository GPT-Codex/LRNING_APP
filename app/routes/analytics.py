from flask import Blueprint, render_template
from app.models import db, Exam, Question, Attempt, Subject, Chapter
from sqlalchemy import func

analytics_bp = Blueprint('analytics', __name__)

from app.models import ExamSession, ExamSessionResponse

@analytics_bp.route('/')
def index():
    # --- LOGGED EXAMS ANALYTICS ---
    exams = Exam.query.order_by(Exam.date.asc()).all()

    exam_dates = [e.date.strftime('%b %d') if e.date else f'Exam #{e.id}' for e in exams]
    exam_percentages = [e.percentage for e in exams]
    exam_scores = [e.score for e in exams]

    subjects = Subject.query.all()
    subject_stats = []
    for s in subjects:
        s_attempts = Attempt.query.join(Question).join(Chapter).filter(
            Attempt.exam_id.isnot(None),
            Chapter.subject_id == s.id
        ).all()
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

    chapters = Chapter.query.all()
    chapter_stats = []
    for c in chapters:
        c_attempts = Attempt.query.join(Question).filter(
            Attempt.exam_id.isnot(None),
            Question.chapter_id == c.id
        ).all()
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
    chapter_stats = sorted(chapter_stats, key=lambda x: x['accuracy'])

    mistake_stats = db.session.query(
        Attempt.mistake_type,
        func.count(Attempt.id).label('count'),
        func.sum(Attempt.max_marks - Attempt.marks_awarded).label('marks_lost')
    ).filter(Attempt.exam_id.isnot(None), Attempt.mistake_type.isnot(None), Attempt.mistake_type != '')\
     .group_by(Attempt.mistake_type)\
     .order_by(func.count(Attempt.id).desc()).all()

    diff_levels = ['Easy', 'Medium', 'Hard']
    difficulty_stats = []
    for diff in diff_levels:
        d_attempts = Attempt.query.join(Question).filter(Attempt.exam_id.isnot(None), Question.difficulty == diff).all()
        tot = len(d_attempts)
        wrong = sum(1 for a in d_attempts if a.is_correct is False)
        acc = round(((tot - wrong) / tot) * 100, 1) if tot > 0 else 0.0
        difficulty_stats.append({'difficulty': diff, 'total': tot, 'wrong': wrong, 'accuracy': acc})

    high_conf_wrong = Attempt.query.filter(Attempt.exam_id.isnot(None), Attempt.confidence == 'High', Attempt.is_correct == False).all()
    high_conf_correct = Attempt.query.filter(Attempt.exam_id.isnot(None), Attempt.confidence == 'High', Attempt.is_correct == True).count()
    low_conf_correct = Attempt.query.filter(Attempt.exam_id.isnot(None), Attempt.confidence == 'Low', Attempt.is_correct == True).count()
    low_conf_wrong = Attempt.query.filter(Attempt.exam_id.isnot(None), Attempt.confidence == 'Low', Attempt.is_correct == False).count()

    # --- TAKEN EXAMS ANALYTICS ---
    taken_sessions = ExamSession.query.filter_by(status='Submitted').order_by(ExamSession.submit_time.asc()).all()
    taken_dates = [s.submit_time.strftime('%b %d') if s.submit_time else f'Session #{s.id}' for s in taken_sessions]
    taken_percentages = [round((s.score / s.total_marks * 100), 1) if s.total_marks > 0 else 0.0 for s in taken_sessions]
    taken_scores = [s.score for s in taken_sessions]

    taken_subject_stats = []
    for s in subjects:
        t_responses = ExamSessionResponse.query.join(ExamSession).join(Question).join(Chapter).filter(
            ExamSession.status == 'Submitted',
            Chapter.subject_id == s.id
        ).all()
        tot = len(t_responses)
        correct = sum(1 for r in t_responses if r.is_correct is True)
        wrong = sum(1 for r in t_responses if r.is_correct is False)
        acc = round((correct / tot) * 100, 1) if tot > 0 else 0.0
        taken_subject_stats.append({
            'name': s.name,
            'total': tot,
            'correct': correct,
            'wrong': wrong,
            'accuracy': acc
        })

    taken_chapter_stats = []
    for c in chapters:
        c_responses = ExamSessionResponse.query.join(ExamSession).join(Question).filter(
            ExamSession.status == 'Submitted',
            Question.chapter_id == c.id
        ).all()
        tot = len(c_responses)
        if tot > 0:
            correct = sum(1 for r in c_responses if r.is_correct is True)
            wrong = sum(1 for r in c_responses if r.is_correct is False)
            acc = round((correct / tot) * 100, 1)
            taken_chapter_stats.append({
                'subject': c.subject.name,
                'chapter': c.name,
                'accuracy': acc,
                'wrong_count': wrong
            })
    taken_chapter_stats = sorted(taken_chapter_stats, key=lambda x: x['accuracy'])

    taken_difficulty_stats = []
    for diff in diff_levels:
        d_responses = ExamSessionResponse.query.join(ExamSession).join(Question).filter(
            ExamSession.status == 'Submitted',
            Question.difficulty == diff
        ).all()
        tot = len(d_responses)
        correct = sum(1 for r in d_responses if r.is_correct is True)
        wrong = sum(1 for r in d_responses if r.is_correct is False)
        acc = round((correct / tot) * 100, 1) if tot > 0 else 0.0
        taken_difficulty_stats.append({'difficulty': diff, 'total': tot, 'correct': correct, 'wrong': wrong, 'accuracy': acc})

    return render_template(
        'analytics/index.html',
        active_page='analytics',
        # Logged stats
        exam_dates=exam_dates,
        exam_percentages=exam_percentages,
        subject_stats=subject_stats,
        chapter_stats=chapter_stats,
        mistake_stats=mistake_stats,
        difficulty_stats=difficulty_stats,
        high_conf_wrong=high_conf_wrong,
        high_conf_correct=high_conf_correct,
        low_conf_correct=low_conf_correct,
        low_conf_wrong=low_conf_wrong,
        # Taken stats
        taken_sessions=taken_sessions,
        taken_dates=taken_dates,
        taken_percentages=taken_percentages,
        taken_scores=taken_scores,
        taken_subject_stats=taken_subject_stats,
        taken_chapter_stats=taken_chapter_stats,
        taken_difficulty_stats=taken_difficulty_stats
    )
