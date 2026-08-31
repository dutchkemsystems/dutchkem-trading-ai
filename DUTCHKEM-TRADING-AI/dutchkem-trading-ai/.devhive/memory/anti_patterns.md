# Anti-Patterns — Dutchkem Trading AI

## ant-001: No Automated Tests
- Project has test files but no comprehensive test suite
- No pytest configuration, no coverage reports
- Tags: testing, quality

## ant-002: Mock Data in Production Code
- All frontend pages contain hardcoded mock data mixed with component logic
- No separation between data fetching and presentation
- Tags: frontend, architecture

## ant-003: Missing CI/CD Pipeline
- GitHub Actions workflow exists but is incomplete
- No Railway deployment automation
- Tags: devops, ci-cd
