from datetime import date, datetime, timedelta
from app.models import db, Subject, Chapter, Exam, Question, Option, Attempt, Tag

def run_seed():
    db.drop_all()
    db.create_all()

    # 1. Create Subjects
    physics = Subject(name="Physics")
    chem = Subject(name="Chemistry")
    math = Subject(name="Mathematics")

    db.session.add_all([physics, chem, math])
    db.session.commit()

    # 2. Create Chapters
    ch_rel = Chapter(subject_id=physics.id, name="Relative Motion")
    ch_vec = Chapter(subject_id=physics.id, name="Vectors & Kinematics")
    ch_atom = Chapter(subject_id=chem.id, name="Structure of Atom")
    ch_org = Chapter(subject_id=chem.id, name="Organic Chemistry Mechanisms")
    ch_quad = Chapter(subject_id=math.id, name="Quadratic Functions & Relations")
    ch_calc = Chapter(subject_id=math.id, name="Differential Calculus")

    db.session.add_all([ch_rel, ch_vec, ch_atom, ch_org, ch_quad, ch_calc])
    db.session.commit()

    # 3. Create Tags
    tag_disc = Tag(name="discriminant")
    tag_roots = Tag(name="roots")
    tag_param = Tag(name="parameter")
    tag_rel = Tag(name="relative-motion")
    tag_calc = Tag(name="calculation")

    db.session.add_all([tag_disc, tag_roots, tag_param, tag_rel, tag_calc])
    db.session.commit()

    # 4. Create Exams (one with unknown center_rank)
    exam1 = Exam(
        name="JEE Full Mock Test #1",
        date=date.today() - timedelta(days=14),
        total_marks=120.0,
        score=71.0,
        center_rank=1,
        institution_rank=5,
        notes="Felt confident in Physics, but made algebraic errors in Quadratic equations."
    )

    exam2 = Exam(
        name="Physics & Chemistry Midterm",
        date=date.today() - timedelta(days=5),
        total_marks=80.0,
        score=62.0,
        center_rank=None, # Unknown / Not recorded center rank
        institution_rank=8,
        notes="Improvement in Relative motion. Need to re-read Bohr model assumptions."
    )

    db.session.add_all([exam1, exam2])
    db.session.commit()

    # 5. Create Questions
    # Question 1: Quadratic Discriminant with Multiline Solution
    multiline_solution = """Since,

the discriminant is given by:

$$
D = b^2 - 4ac
$$

We can analyze the roots as follows:
- When D > 0, roots are real and distinct.
- When D = 0, roots are real and equal.
- When D < 0, roots are complex conjugate pairs.

Therefore, for $x^2 - 2kx + (k^2 - 1) = 0$:
$$
D = (-2k)^2 - 4(1)(k^2-1) = 4 > 0
$$

Conclusion: $k \\in \\mathbb{R}$."""

    q1 = Question(
        chapter_id=ch_quad.id,
        question_text="Find the set of values of $k$ for which the quadratic equation $x^2 - 2kx + (k^2 - 1) = 0$ has two distinct real roots.",
        question_type="MCQ",
        difficulty="Hard",
        correct_answer="D",
        solution=multiline_solution,
        review_state="Learning"
    )
    q1.tags.extend([tag_disc, tag_roots, tag_param])

    opt1_a = Option(question=q1, label="A", text="$k > 1$", is_correct=False)
    opt1_b = Option(question=q1, label="B", text="$k = 0$", is_correct=False)
    opt1_c = Option(question=q1, label="C", text="$k < -1$", is_correct=False)
    opt1_d = Option(question=q1, label="D", text="$k \\in \\mathbb{R}$", is_correct=True)

    db.session.add(q1)
    db.session.commit()

    # Attempt 1 for Q1 in Exam 1 (Wrong)
    att1_1 = Attempt(
        question_id=q1.id,
        exam_id=exam1.id,
        attempt_type="EXAM",
        user_answer="B",
        is_correct=False,
        marks_awarded=-1.0,
        max_marks=4.0,
        time_taken_seconds=134,
        confidence="High",
        mistake_type="Recognition Error",
        mistake_reason="I knew that two distinct roots require D > 0, but accidentally used D = 0 condition when solving parameters.",
        created_at=datetime.utcnow() - timedelta(days=14)
    )

    # Review Attempt for Q1 (Correct)
    att1_2 = Attempt(
        question_id=q1.id,
        attempt_type="REVIEW",
        user_answer="D",
        is_correct=True,
        marks_awarded=4.0,
        max_marks=4.0,
        time_taken_seconds=90,
        confidence="High",
        created_at=datetime.utcnow() - timedelta(days=2)
    )

    # Question 2: Relative Velocity with unknown time taken in Attempt
    q2 = Question(
        chapter_id=ch_rel.id,
        question_text="Two trains A and B of length 100m moving in opposite directions on parallel tracks cross each other with velocities $v_A = 20\\text{ m/s}$ and $v_B = 30\\text{ m/s}$. Find the time taken to completely cross each other.",
        question_type="MCQ",
        difficulty="Medium",
        correct_answer="A",
        solution="Relative velocity $v_{rel} = v_A + v_B = 20 + 30 = 50\\text{ m/s}$.\nTotal distance $d = 200\\text{ m}$.\nTime $t = 200 / 50 = 4\\text{ s}$.",
        review_state="Mastered"
    )
    q2.tags.extend([tag_rel, tag_calc])

    opt2_a = Option(question=q2, label="A", text="$4.0\\text{ s}$", is_correct=True)
    opt2_b = Option(question=q2, label="B", text="$10.0\\text{ s}$", is_correct=False)
    opt2_c = Option(question=q2, label="C", text="$2.0\\text{ s}$", is_correct=False)
    opt2_d = Option(question=q2, label="D", text="$20.0\\text{ s}$", is_correct=False)

    db.session.add(q2)
    db.session.commit()

    att2 = Attempt(
        question_id=q2.id,
        exam_id=exam1.id,
        attempt_type="EXAM",
        user_answer="A",
        is_correct=True,
        marks_awarded=4.0,
        max_marks=4.0,
        time_taken_seconds=None, # Unknown / Not recorded time
        confidence="High",
        created_at=datetime.utcnow() - timedelta(days=14)
    )

    db.session.add_all([att1_1, att1_2, att2])
    db.session.commit()
