# Inventory DSS implementation checklist

## Phase 1 — One SKU from forecast to review

- [x] Add `/decisions` for admins and reuse the policy, simulation, history, and review components.
- [x] Load an explicit saved weekly forecast and collect the stock and receipt inputs.
- [x] Explain the first projected shortage, maximum deficit, and whether the shortage falls within lead time.
- [x] Persist diagnostics in new recommendation snapshots and support older snapshots on read.
- [x] Verify generation, snapshot evidence, and final review in the backend fixture.

## Phase 2 — Multi-SKU exception workspace

- [x] Add versioned excess-stock diagnostics and keep shortage and excess flags independent.
- [x] Add a run- and mode-scoped exception API and table with priorities, status filters, and pagination.
- [x] Show missing recommendations, insufficient forecast evidence, and unsupported historical snapshots.

## Phase 3 — Verification and handoff

- [x] Verify calculation fixture values, review conflicts, authorization, and advisory-only behavior.
- [x] Run backend tests, frontend lint and build, and verify the one-SKU browser flow and 390 px table layout.
- [x] Verify duplicate generation, concurrent review, and the exception query on disposable PostgreSQL 15.
- [x] Document the API examples, demonstration, and known limits.
- [ ] Run the shared handoff scenario with Member 3's separate import implementation once it is integrated.

See [DSS code flow](DSS_CODE_FLOW.md) for the paths, API examples, verification, and demonstration.
