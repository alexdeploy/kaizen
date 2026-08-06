---
paths:
  - "tests/**/*.py"
  - "**/test_*.py"
  - "**/*_test.py"
---

# Testing rules (Python / pytest)

Loaded only when Claude edits test files.

## Conventions

<!-- KAIZEN_STANDARDS:rules_testing.conventions -->

## Structure

```python
class TestSubject:
    def test_should_do_x_when_y(self, fixture_a):
        ...
```

## Never

<!-- KAIZEN_STANDARDS:rules_testing.never -->

