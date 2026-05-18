---
paths:
  - "**/*.test.ts"
  - "**/*.test.tsx"
  - "**/*.spec.ts"
  - "tests/**"
---

# Testing rules

Loaded only when Claude is editing test files.

## Conventions

- Descriptive names: `should [expected] when [condition]`.
- Mock **external** dependencies only (network, fs, third-party APIs). Never mock internal modules.
- Clean up side effects in `afterEach` / `afterAll`.
- One test per behavior, not per method.
- Tests must be order-independent.

## Structure

```ts
describe('Subject', () => {
  describe('when <context>', () => {
    it('should <outcome>', () => { ... })
  })
})
```

## Never

- No tests that depend on real wall-clock time without freezing it (`vi.useFakeTimers()` / `jest.useFakeTimers()`).
- No snapshots of components with non-deterministic data.
- No `console.log` in tests — use the reporter.
