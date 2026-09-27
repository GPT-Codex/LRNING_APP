import os
from flask import Flask
from config import Config
from app.models import db, Subject, Chapter, Exam, Question, Attempt, Tag, Option

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['BASE_DIR'], 'instance'), exist_ok=True)

    db.init_app(app)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.exams import exams_bp
    from app.routes.questions import questions_bp
    from app.routes.review import review_bp
    from app.routes.analytics import analytics_bp
    from app.routes.exam_taker import exam_taker_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(exams_bp, url_prefix='/exams')
    app.register_blueprint(questions_bp, url_prefix='/questions')
    app.register_blueprint(review_bp, url_prefix='/review')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(exam_taker_bp, url_prefix='/exam-taker')

    # Register context processors & Jinja filters
    @app.template_filter('format_seconds')
    def format_seconds(seconds):
        if not seconds:
            return "00:00"
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    @app.context_processor
    def inject_global_data():
        # Inject due review count into base templates for badge count in sidebar
        due_review_count = Question.query.filter(Question.review_state.in_(['Wrong', 'Learning', 'Reviewing'])).count()
        return dict(due_review_count=due_review_count)

    # CLI command for database seeding
    @app.cli.command("seed-db")
    def seed_db():
        from app.seed import run_seed
        run_seed()
        print("Database populated with sample data successfully!")

    with app.app_context():
        db.create_all()
        # Migration checks
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'option' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('option')]
            if 'image_path' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE option ADD COLUMN image_path VARCHAR(255)"))
                    conn.commit()

        if 'chapter' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('chapter')]
            if 'priority' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE chapter ADD COLUMN priority INTEGER NOT NULL DEFAULT 1"))
                    conn.commit()

        # Seed Default Exam Template if missing
        from app.models import ExamTemplate
        import json
        if not ExamTemplate.query.filter_by(is_default=True).first():
            default_pattern = [
                {"name": "Section A: Single Correct MCQ", "type": "MCQ", "start": 1, "end": 20, "count": 20},
                {"name": "Section B: Numerical Answer", "type": "Numerical", "start": 21, "end": 25, "count": 5},
                {"name": "Section C: Multiple Correct MCQ", "type": "Multiple Select", "start": 26, "end": 30, "count": 5}
            ]
            default_diff = {
                "Easy": {"Easy": 10, "Medium": 5, "Hard": 0},
                "Medium": {"Easy": 12, "Medium": 15, "Hard": 18},
                "Hard": {"Easy": 8, "Medium": 10, "Hard": 12}
            }
            def_tmpl = ExamTemplate(
                name="Default Template (60m / 30Q)",
                duration_minutes=60,
                total_questions=30,
                pattern_json=json.dumps(default_pattern),
                difficulty_json=json.dumps(default_diff),
                is_default=True
            )
            db.session.add(def_tmpl)
            db.session.commit()

    return app
