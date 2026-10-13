from library_chat.catalog import CATALOG, format_books, search_catalog


def test_catalog_has_the_invented_books():
    assert len(CATALOG) == 14


def test_search_finds_the_coastal_mystery_first():
    # search_catalog is an @opik.track(type="tool") function; with tracking disabled it is a plain call.
    books = search_catalog("a cozy mystery somewhere coastal")
    assert books[0]["title"] == "The Lantern Keeper's Daughter"
    assert len(books) <= 3


def test_search_returns_nothing_for_an_absent_topic():
    assert search_catalog("anything on dragons") == []


def test_format_books_reports_availability():
    text = format_books(search_catalog("mystery codes puzzles"))
    assert "Salt and Cipher" in text
    assert "all copies checked out" in text
    assert format_books([]) == "(no matching books found in the catalog)"
