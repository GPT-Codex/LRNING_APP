import unittest
from app import create_app
from app.models import db, Subject, Chapter, Exam, Question, Attempt, Tag, Option

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

    def test_dashboard_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_create_exam_and_workspace_save(self):
        # Create exam
        res = self.client.post('/exams/create', data={
            'name': 'Unit Test Exam',
            'date': '2026-08-30',
            'total_marks': 100,
            'score': 0
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        exam = Exam.query.filter_by(name='Unit Test Exam').first()
        self.assertIsNotNone(exam)

        # Save question in workspace
        chap = Chapter.query.first()
        res_save = self.client.post(f'/exams/{exam.id}/workspace/save', data={
            'q_index': 1,
            'chapter_id': chap.id,
            'question_text': 'What is velocity?',
            'question_type': 'MCQ',
            'difficulty': 'Easy',
            'correct_answer': 'A',
            'user_answer': 'B',
            'is_correct': 'false',
            'marks_awarded': -1.0,
            'max_marks': 4.0,
            'time_taken_seconds': 60,
            'confidence': 'High',
            'mistake_type': 'Concept Gap',
            'mistake_reason': 'Confused speed and velocity',
            'nav_action': 'next'
        }, follow_redirects=True)
        self.assertEqual(res_save.status_code, 200)

        # Verify Attempt was logged with Concept Gap mistake
        att = Attempt.query.filter_by(exam_id=exam.id).first()
        self.assertIsNotNone(att)
        self.assertEqual(att.mistake_type, 'Concept Gap')
        self.assertEqual(att.question.review_state, 'Wrong')

    def test_active_recall_review_progression(self):
        chap = Chapter.query.first()
        q = Question(chapter_id=chap.id, question_text="Review question", review_state="Wrong")
        db.session.add(q)
        db.session.commit()
        q_id = q.id

        # Perform review attempt marked correct
        res = self.client.post(f'/review/session/{q_id}', data={
            'user_answer': 'A',
            'is_correct': 'true',
            'time_taken_seconds': 45,
            'confidence': 'High'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        q_updated = Question.query.get(q_id)
        self.assertEqual(q_updated.review_state, 'Learning')

    def test_data_export_endpoints(self):
        self.assertEqual(self.client.get('/export/json').status_code, 200)
        self.assertEqual(self.client.get('/export/csv/attempts').status_code, 200)
        self.assertEqual(self.client.get('/export/csv/exams').status_code, 200)
        self.assertEqual(self.client.get('/export/csv/questions').status_code, 200)

if __name__ == '__main__':
    unittest.main()
