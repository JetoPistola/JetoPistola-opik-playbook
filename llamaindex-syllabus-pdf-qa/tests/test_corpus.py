from syllabus_qa import corpus
from syllabus_qa.config import SYLLABI_DIR


def test_committed_pdfs_match_the_course_table():
    assert sorted(p.name for p in SYLLABI_DIR.glob("*.pdf")) == sorted(corpus.COURSES)


def test_generate_writes_valid_pdfs_and_skips_existing(tmp_path):
    paths = corpus.generate_syllabi(out_dir=tmp_path)
    assert len(paths) == 3
    assert all(p.read_bytes().startswith(b"%PDF") for p in paths)
    first = paths[0].stat().st_mtime_ns
    corpus.generate_syllabi(out_dir=tmp_path)  # force=False keeps the existing file
    assert paths[0].stat().st_mtime_ns == first


def test_every_course_states_the_four_policies():
    for spec in corpus.COURSES.values():
        headings = [h for h, _ in spec["sections"]]
        assert [h.split(". ")[1] for h in headings] == [
            "Grading", "Late Work", "Office Hours", "Prerequisites"]
