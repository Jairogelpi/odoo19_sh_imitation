from tools.check_repository_hygiene import violations


def test_tracked_repository_contains_no_generated_or_oversized_files():
    assert violations() == []

