from syllabus_qa.suite import GLOBAL_ASSERTIONS, ITEMS, SUITE_NAME


def test_nine_items_each_with_a_clause_assertion():
    assert SUITE_NAME == "syllabus-clauses"
    assert len(ITEMS) == 9
    for question, assertions in ITEMS:
        assert question.endswith("?")
        assert assertions and all(a.startswith("The answer states") for a in assertions)


def test_questions_are_unique_and_every_course_is_covered():
    questions = [q for q, _ in ITEMS]
    assert len(set(questions)) == len(questions)
    text = " ".join(a for _, assertions in ITEMS for a in assertions)
    for course in ("BIO 101", "MAT 120", "ENG 110"):
        assert course in text


def test_global_assertion_is_about_grounding():
    assert len(GLOBAL_ASSERTIONS) == 1 and "retrieved" in GLOBAL_ASSERTIONS[0]
