import unittest
from app import create_app
from app.models import db, Subject, Chapter, Question, Option, ExamTemplate, ExamSession, ExamSessionResponse
from app.utils import natural_sort_key, sort_chapters, sort_subjects
from app.services.exam_generator import validate_and_generate_exam

class ExamTakerTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.drop_all()
        db.create_all()

        # Seed subjects & chapters
        s1 = Subject(name="Physics")
        s2 = Subject(name="Mathematics")
        db.session.add_all([s1, s2])
        db.session.commit()

        c1 = Chapter(subject_id=s1.id, name="Chapter 10", priority=2)
        c2 = Chapter(subject_id=s1.id, name="Chapter 2", priority=1)
        c3 = Chapter(subject_id=s1.id, name="Chapter 1", priority=1)
        db.session.add_all([c1, c2, c3])
        db.session.commit()

        # Seed test questions
        for i in range(1, 15):
            q = Question(
                chapter_id=c2.id if i % 2 == 0 else c3.id,
                question_text=f"Question {i}",
                question_type="MCQ",
                difficulty="Easy" if i <= 5 else "Medium",
                correct_answer="A"
            )
            opt_a = Option(question=q, label="A", text="Opt A", is_correct=True)
            db.session.add(q)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_natural_alphanumeric_sorting(self):
        chaps = Chapter.query.all()
        sorted_c = sort_chapters(chaps)
        self.assertEqual([c.name for c in sorted_c], ["Chapter 1", "Chapter 2", "Chapter 10"])

    def test_exam_generator_subjectwise(self):
        s1 = Subject.query.filter_by(name="Physics").first()
        pattern = [{"name": "MCQ", "type": "MCQ", "count": 5}]
        success, gen_data, err = validate_and_generate_exam(
            scope_type="Subjectwise",
            selected_subject_ids=[s1.id],
            selected_chapter_ids=[],
            difficulty_mode="Medium",
            pattern_sections=pattern,
            total_questions=5
        )
        self.assertTrue(success)
        self.assertEqual(len(gen_data["question_ids"]), 5)

    def test_insufficient_pool_warning(self):
        s1 = Subject.query.filter_by(name="Physics").first()
        pattern = [{"name": "Numerical", "type": "Numerical", "count": 10}]
        success, gen_data, err = validate_and_generate_exam(
            scope_type="Subjectwise",
            selected_subject_ids=[s1.id],
            selected_chapter_ids=[],
            difficulty_mode="Medium",
            pattern_sections=pattern,
            total_questions=10
        )
        self.assertFalse(success)
        self.assertIn("Not enough eligible questions", err["message"])

    def test_exam_taker_session_flow(self):
        # Create a single section custom template for quick testing
        tmpl = ExamTemplate(
            name="Test Template",
            duration_minutes=30,
            total_questions=3,
            pattern_json='[{"name": "MCQ", "type": "MCQ", "count": 3}]',
            difficulty_json='{"Medium": {"Easy": 3}}',
            is_default=False
        )
        db.session.add(tmpl)
        db.session.commit()

        # 1. Setup session
        res_setup = self.client.post('/exam-taker/setup', data={
            'template_id': tmpl.id,
            'scope_type': 'All Mixed',
            'difficulty_mode': 'Medium',
            'duration_minutes': 30,
            'total_questions': 3
        }, follow_redirects=True)
        self.assertEqual(res_setup.status_code, 200)

        session = ExamSession.query.first()
        self.assertIsNotNone(session)

        # 2. Start session
        res_start = self.client.post(f'/exam-taker/start/{session.id}', follow_redirects=True)
        self.assertEqual(res_start.status_code, 200)

        # 3. Submit answer
        q_id = Question.query.first().id
        res_ans = self.client.post(f'/exam-taker/session/{session.id}/answer', data={
            'question_id': q_id,
            'q_index': 1,
            'user_answer': 'A',
            'nav_action': 'next'
        }, follow_redirects=True)
        self.assertEqual(res_ans.status_code, 200)

        # 4. Submit exam
        res_sub = self.client.post(f'/exam-taker/session/{session.id}/submit', follow_redirects=True)
        self.assertEqual(res_sub.status_code, 200)

        session_sub = ExamSession.query.get(session.id)
        self.assertEqual(session_sub.status, 'Submitted')

if __name__ == '__main__':
    unittest.main()
