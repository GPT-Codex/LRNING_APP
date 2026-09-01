import unittest
from app import create_app
from app.models import db, Subject, Chapter, Exam, Question, Attempt, Tag, Option
from app.utils import parse_optional_int, parse_optional_float

class ExamTrackerTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.drop_all()
        db.create_all()

        s = Subject(name="Physics")
        db.session.add(s)
        db.session.commit()
        c = Chapter(subject_id=s.id, name="Kinematics")
        db.session.add(c)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_parse_optional_int(self):
        self.assertIsNone(parse_optional_int('-'))
        self.assertIsNone(parse_optional_int('—'))
        self.assertIsNone(parse_optional_int(''))
        self.assertIsNone(parse_optional_int(None))
        self.assertEqual(parse_optional_int('120'), 120)
        self.assertEqual(parse_optional_int(25), 25)
        with self.assertRaises(ValueError):
            parse_optional_int('abc')

    def test_create_exam_with_optional_ranks(self):
        # Create exam with '-' for center_rank
        res = self.client.post('/exams/create', data={
            'name': 'Exam with missing rank',
            'date': '2026-08-31',
            'total_marks': 100,
            'score': 80,
            'center_rank': '-',
            'institution_rank': '10'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        exam = Exam.query.filter_by(name='Exam with missing rank').first()
        self.assertIsNotNone(exam)
        self.assertIsNone(exam.center_rank)
        self.assertEqual(exam.institution_rank, 10)

    def test_workspace_save_optional_time_taken(self):
        exam = Exam(name="Test Exam", date=db.func.current_date(), total_marks=100, score=0)
        db.session.add(exam)
        db.session.commit()
        chap = Chapter.query.first()

        # Save question attempt with '-' for time_taken_seconds
        res = self.client.post(f'/exams/{exam.id}/workspace/save', data={
            'q_index': 1,
            'chapter_id': chap.id,
            'question_text': 'Sample Question',
            'question_type': 'MCQ',
            'time_taken_seconds': '-',
            'is_correct': 'true',
            'marks_awarded': 4.0,
            'max_marks': 4.0,
            'option_text_0': 'Option A Text',
            'option_text_1': 'Option B Text',
            'nav_action': 'next'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        att = Attempt.query.filter_by(exam_id=exam.id).first()
        self.assertIsNotNone(att)
        self.assertIsNone(att.time_taken_seconds)

        # Check options created
        self.assertEqual(len(att.question.options), 2)

    def test_multiline_solution_rendering(self):
        chap = Chapter.query.first()
        multiline_sol = "Since,\n\n$$D = b^2 - 4ac$$\n\nwe conclude that..."
        q = Question(chapter_id=chap.id, question_text="Formula Q", solution=multiline_sol)
        db.session.add(q)
        db.session.commit()

        res = self.client.get(f'/questions/{q.id}')
        self.assertEqual(res.status_code, 200)
        self.assertIn('solution-text', res.get_data(as_text=True))
        self.assertIn('$$D = b^2 - 4ac$$', res.get_data(as_text=True))

if __name__ == '__main__':
    unittest.main()
