from src.main import greet


def test_greet():
    assert greet("x") == "hi x"
