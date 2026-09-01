from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# M2M Association Table for Question and Tag
question_tags = db.Table(
    'question_tags',
    db.Column('question_id', db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), primary_key=True)
)

class Subject(db.Model):
    __tablename__ = 'subject'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    chapters = db.relationship('Chapter', backref='subject', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'chapter_count': len(self.chapters)
        }

class Chapter(db.Model):
    __tablename__ = 'chapter'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(150), nullable=False)

    questions = db.relationship('Question', backref='chapter', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'subject_name': self.subject.name if self.subject else '',
            'name': self.name
        }

class Exam(db.Model):
    __tablename__ = 'exam'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    total_marks = db.Column(db.Float, nullable=False, default=0.0)
    score = db.Column(db.Float, nullable=False, default=0.0)
    institution_rank = db.Column(db.Integer, nullable=True)
    center_rank = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attempts = db.relationship('Attempt', backref='exam', cascade='all, delete-orphan', lazy=True)

    @property
    def percentage(self):
        if self.total_marks and self.total_marks > 0:
            return round((self.score / self.total_marks) * 100, 1)
        return 0.0

class Tag(db.Model):
    __tablename__ = 'tag'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    def to_dict(self):
        return {'id': self.id, 'name': self.name}

class Question(db.Model):
    __tablename__ = 'question'
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id', ondelete='SET NULL'), nullable=True)
    question_text = db.Column(db.Text, nullable=True)
    question_type = db.Column(db.String(30), nullable=False, default='MCQ') # MCQ, Multiple Select, Numerical, Subjective
    difficulty = db.Column(db.String(20), nullable=False, default='Medium') # Easy, Medium, Hard
    correct_answer = db.Column(db.Text, nullable=True)
    solution = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(100), nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    review_state = db.Column(db.String(30), nullable=False, default='New') # New, Wrong, Learning, Reviewing, Mastered
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    options = db.relationship('Option', backref='question', cascade='all, delete-orphan', lazy=True, order_by='Option.id')
    attempts = db.relationship('Attempt', backref='question', cascade='all, delete-orphan', lazy=True, order_by='Attempt.created_at.desc()')
    tags = db.relationship('Tag', secondary=question_tags, backref=db.backref('questions', lazy='dynamic'))

    @property
    def latest_attempt(self):
        return self.attempts[0] if self.attempts else None

    @property
    def attempt_count(self):
        return len(self.attempts)

class Option(db.Model):
    __tablename__ = 'option'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), nullable=False)
    label = db.Column(db.String(10), nullable=False) # A, B, C, D
    text = db.Column(db.Text, nullable=True) # Text is optional if image is present
    image_path = db.Column(db.String(255), nullable=True) # Option specific image
    is_correct = db.Column(db.Boolean, default=False)

class Attempt(db.Model):
    __tablename__ = 'attempt'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id', ondelete='SET NULL'), nullable=True)
    attempt_type = db.Column(db.String(20), nullable=False, default='EXAM') # EXAM or REVIEW
    user_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True) # True, False, or None if unattempted
    marks_awarded = db.Column(db.Float, nullable=False, default=0.0)
    max_marks = db.Column(db.Float, nullable=False, default=4.0)
    time_taken_seconds = db.Column(db.Integer, nullable=True)
    confidence = db.Column(db.String(20), nullable=True, default='Medium') # Low, Medium, High
    mistake_type = db.Column(db.String(50), nullable=True)
    mistake_reason = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), nullable=False, default='Completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Predefined Mistake Categories
    MISTAKE_TYPES = [
        'Concept Gap',
        'Recall Error',
        'Recognition Error',
        'Algebra / Calculation',
        'Misread Question',
        'Silly Error',
        'Time Pressure',
        'Guess',
        'Incomplete'
    ]
