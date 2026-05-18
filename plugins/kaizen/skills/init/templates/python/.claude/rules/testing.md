---
paths:
  - "tests/**/*.py"
  - "**/test_*.py"
  - "**/*_test.py"
---

# Testing rules (Python / pytest)

Loaded only when Claude edits test files.

## Conventions

- Test names describe behavior: `test_<what>_<when>_<expected>`.
- Use **fixtures** (`@pytest.fixture`) for setup, not bare functions.
- **Parametrize** (`@pytest.mark.parametrize`) over copy-pasted tests.
- Mock **external** dependencies only (network, DB, fs). Don't mock internal modules.
- One assertion per test when practical; otherwise group related assertions.

## Structure

```python
class TestSubject:
    def test_should_do_x_when_y(self, fixture_a):
        ...
```

## Never

- No `time.sleep()` in tests — use `freezegun` or `pytest-freezer`.
- No real network or DB calls — use respx / responses / fakes.
- No `print()` debugging left behind.
- No tests that depend on file system state outside `tmp_path` fixture.
