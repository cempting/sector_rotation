# Copilot Instructions For Sector Rotation

## Scope

These instructions apply to all changes in this repository.

## Change policy

- Any behavior change must include corresponding test updates or new tests.
- Any user-visible change must include documentation updates in at least one of:
  - `README.md`
  - `docs/app-design.md`
  - feature-level docs if added later
- If code structure or architecture changes, update `docs/app-design.md` in the same change.

## Testing policy

- Run full `pytest` for every code change.
- Minimum expectation:
  - changed feature code -> run related tests in `tests/features/`
  - dashboard/routing changes -> run `tests/test_feature_routing.py`
  - core data/analytics changes -> run related tests in `tests/core/`
- Do not mark work complete without reporting what tests were run.

## Documentation policy

- Keep usage instructions in `README.md` aligned with actual commands and app flow.
- Keep architecture and extension guidance in `docs/app-design.md` aligned with current implementation.
- When adding a new feature route, document:
  - route name
  - user workflow
  - test coverage location

## Pull request checklist

- [ ] Tests added or updated for the change
- [ ] Relevant tests executed and results reported
- [ ] `README.md` updated if user behavior/setup/commands changed
- [ ] `docs/app-design.md` updated if architecture/flow changed