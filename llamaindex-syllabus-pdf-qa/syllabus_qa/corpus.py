"""Generate the fictional Larkspur Community College syllabi as PDFs.

Each course states four policies in numbered sections: grading, late work,
office hours, prerequisites. The numbers differ per course on purpose, so a
retriever that grabs the wrong syllabus produces a visibly wrong answer.
"""

import pathlib

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from syllabus_qa.config import SYLLABI_DIR

_s = getSampleStyleSheet()
TITLE = ParagraphStyle("T", parent=_s["Title"], fontName="Helvetica-Bold", fontSize=17)
SUB = ParagraphStyle("S", parent=_s["Normal"], fontName="Helvetica-Oblique", alignment=1, spaceAfter=14)
HEAD = ParagraphStyle("H", parent=_s["Heading2"], fontName="Helvetica-Bold", fontSize=12, spaceBefore=12)
BODY = ParagraphStyle("B", parent=_s["Normal"], fontName="Helvetica", fontSize=10.5, leading=14, spaceAfter=6)

COURSES = {
    "bio101-general-biology.pdf": dict(
        title="BIO 101: General Biology",
        subtitle="Larkspur Community College - Natural Sciences - Instructor: Dr. Marisol Tanaka",
        sections=[
            ("1. Grading", [
                "Your final grade is computed from four components: laboratory reports 30%, "
                "midterm exam 25%, final exam 30%, and weekly quizzes 15%.",
                "A grade of 70% or higher is required to pass the course with credit.",
            ]),
            ("2. Late Work", [
                "Work submitted after the deadline loses 10% of its available points for each "
                "day it is late. Late work is accepted for a maximum of 3 days; after that "
                "it receives a zero.",
            ]),
            ("3. Office Hours", [
                "Dr. Tanaka holds office hours on Tuesdays and Thursdays from 2:00 pm to 4:00 pm "
                "in Science Hall room S214. No appointment is needed.",
            ]),
            ("4. Prerequisites", [
                "Students must have completed BIO 099 (Introduction to Life Science) with a C or "
                "better, or have a placement score of 70 or above.",
            ]),
        ]),
    "mat120-intro-statistics.pdf": dict(
        title="MAT 120: Introduction to Statistics",
        subtitle="Larkspur Community College - Mathematics - Instructor: Prof. Devon Okafor",
        sections=[
            ("1. Grading", [
                "Grades are weighted as follows: homework 20%, midterm exam one 25%, midterm "
                "exam two 25%, and the cumulative final exam 30%.",
                "The lowest homework score is dropped before the homework average is computed.",
            ]),
            ("2. Late Work", [
                "Homework may be turned in up to 48 hours after the deadline for a flat penalty "
                "of 15% of the score. Homework more than 48 hours late is not accepted. "
                "Exams cannot be made up without a documented emergency.",
            ]),
            ("3. Office Hours", [
                "Prof. Okafor holds office hours on Mondays and Wednesdays from 10:00 am to "
                "11:30 am in the Math Lab (Building C, room 108).",
            ]),
            ("4. Prerequisites", [
                "MAT 095 (Intermediate Algebra) with a grade of C or better is required. "
                "There is no placement-test alternative for this course.",
            ]),
        ]),
    "eng110-college-writing.pdf": dict(
        title="ENG 110: College Writing",
        subtitle="Larkspur Community College - English - Instructor: Prof. Imani Brightwater",
        sections=[
            ("1. Grading", [
                "Grades are weighted as follows: four essays at 15% each (60% in total), peer "
                "review participation 10%, and the end-of-term portfolio 30%.",
            ]),
            ("2. Late Work", [
                "Each student has one 72-hour grace extension per semester on any essay, with "
                "no penalty and no need to ask. After the grace extension is used, late essays "
                "lose 5% per day for up to 5 days, then receive a zero.",
            ]),
            ("3. Office Hours", [
                "Prof. Brightwater holds office hours on Fridays from 1:00 pm to 3:00 pm, "
                "online by video call only. The link is posted on the course page.",
            ]),
            ("4. Prerequisites", [
                "Placement into college-level writing, or completion of ENG 090 (Writing "
                "Foundations) with a C or better.",
            ]),
        ]),
}


def generate_syllabi(out_dir: pathlib.Path = SYLLABI_DIR, force: bool = False) -> list[pathlib.Path]:
    """Write the PDFs (skipping ones that already exist unless force=True)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for filename, spec in COURSES.items():
        path = out_dir / filename
        paths.append(path)
        if path.exists() and not force:
            continue
        doc = SimpleDocTemplate(
            str(path), pagesize=LETTER, leftMargin=inch, rightMargin=inch,
            topMargin=inch, bottomMargin=inch, title=spec["title"],
            author="Larkspur Community College (fictional)",
        )
        story = [Paragraph(spec["title"], TITLE), Paragraph(spec["subtitle"], SUB)]
        for heading, paras in spec["sections"]:
            story.append(Paragraph(heading, HEAD))
            story += [Paragraph(p, BODY) for p in paras]
        story.append(Spacer(1, 20))
        story.append(Paragraph("Fictional document generated for demonstration purposes.", SUB))
        doc.build(story)
    return paths
