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

<!-- KAIZEN_STANDARDS:rules_testing.conventions -->

## Structure

```ts
describe('Subject', () => {
  describe('when <context>', () => {
    it('should <outcome>', () => { ... })
  })
})
```

## Never

<!-- KAIZEN_STANDARDS:rules_testing.never -->

