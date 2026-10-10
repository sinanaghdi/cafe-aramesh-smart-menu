# Contributing

## Workflow
1. Read PLAN.md and the product boundaries before making a change.
2. Open or update an issue with acceptance criteria. Use backend, frontend, ai, infra, and docs labels where available.
3. Work on a feature branch; never push directly to main.
4. Keep each PR focused on one phase or coherent subtask. Use Conventional Commit messages such as feat(api): add menu query or docs: clarify deployment.
5. Include purpose, implementation notes, test output, screenshots for UI changes, security implications, and a checklist in every PR.
6. Do not start the next phase until the current phase is reviewed and explicitly approved.

## Local setup
- Optionally copy .env.example to .env for convenience; defaults are development-only.
- Run docker compose up --build from the repository root.
- Open http://localhost:8080. Check http://localhost:8000/health and /ready.
- Backend: from backend, run pip install -e ".[dev]", then ruff check ., mypy app, and pytest.
- Frontend: from frontend, run npm install, npm run lint, npm run typecheck, npm run build, and npm run format:check.

## Product and security rules
- Keep the UI Persian-first and genuinely RTL; verify mobile layouts and keyboard focus.
- Never expose merchant analytics or revenue fields to staff at the API layer.
- No payment processing, POS, inventory, accounting, or full CRM.
- Never log OTPs or order confirmation secrets. Do not send personal customer data to AI providers.
- Customer orders are requests until a staff member validates the customer's code in person.
- AI suggestions are drafts until a merchant approves them.
- Avoid invented sales figures and mark seeded/demo data clearly.
