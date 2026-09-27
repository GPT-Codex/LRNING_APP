from datetime import date, datetime, timedelta
from app.models import db, Subject, Chapter, Exam, Question, Option, Attempt, Tag, ExamTemplate

def run_seed():
    db.drop_all()
    db.create_all()

    # 1. Create Subjects
    physics = Subject(name="Physics")
    chem = Subject(name="Chemistry")
    math = Subject(name="Mathematics")

    db.session.add_all([physics, chem, math])
    db.session.commit()

    # 2. Create Chapters with Priorities
    ch_rel = Chapter(subject_id=physics.id, name="Relative Motion", priority=1)
    ch_vec = Chapter(subject_id=physics.id, name="Vectors & Kinematics", priority=2)
    ch_atom = Chapter(subject_id=chem.id, name="Structure of Atom", priority=1)
    ch_org = Chapter(subject_id=chem.id, name="Organic Chemistry Mechanisms", priority=2)
    ch_quad = Chapter(subject_id=math.id, name="Quadratic Functions & Relations", priority=1)
    ch_calc = Chapter(subject_id=math.id, name="Differential Calculus", priority=2)

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

    # 4. Create Questions for Exam Taker Generator
    questions = []

    # MCQ Questions (Single Correct)
    for i in range(1, 22):
        q = Question(
            chapter_id=ch_quad.id if i % 2 == 0 else ch_rel.id,
            question_text=f"Sample MCQ Question #{i}: Calculate value of $x_{{{i}}}$ where $D > 0$.",
            question_type="MCQ",
            difficulty="Easy" if i <= 10 else "Medium",
            correct_answer="A",
            solution=f"Solution for Q#{i}:\nStep 1: Apply formula\nStep 2: Calculate result $x = {i}$.",
            review_state="New"
        )
        opt_a = Option(question=q, label="A", text=f"Answer {i}", is_correct=True)
        opt_b = Option(question=q, label="B", text=f"Wrong {i}", is_correct=False)
        questions.append(q)

    # Numerical Questions
    for i in range(1, 8):
        q = Question(
            chapter_id=ch_atom.id if i % 2 == 0 else ch_vec.id,
            question_text=f"Numerical Question #{i}: Find the magnitude of velocity vector $\\vec{{v}}_{{{i}}}$.",
            question_type="Numerical",
            difficulty="Medium" if i <= 4 else "Hard",
            correct_answer=str(i * 10),
            solution=f"Magnitude = $\\sqrt{{{i}^2 + {i*2}^2}} = {i*10}$.",
            review_state="New"
        )
        questions.append(q)

    # Multiple Select Questions
    for i in range(1, 8):
        q = Question(
            chapter_id=ch_calc.id if i % 2 == 0 else ch_org.id,
            question_text=f"Multiple Select Question #{i}: Which of the following conditions hold true for $f(x)$?",
            question_type="Multiple Select",
            difficulty="Hard",
            correct_answer="A",
            solution="Conditions A and B both hold true.",
            review_state="New"
        )
        opt_a = Option(question=q, label="A", text="Statement A", is_correct=True)
        opt_b = Option(question=q, label="B", text="Statement B", is_correct=True)
        questions.append(q)

    db.session.add_all(questions)
    db.session.commit()
