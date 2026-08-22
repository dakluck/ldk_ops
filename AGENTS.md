# Ldk Ops - Hermes Development Rules

## 1. Project Overview & Tech Stack

- **Primary Tech Stack:** Python
- **Root Path:** `/home/dailey/Development/ldk_ops`

## 2. Mandatory Verification Commands (Pre-Commit / Pre-Push)

Before declaring completion or pushing changes, Hermes MUST run local verification:

- **Lint / Syntax Check:** `python3 -m py_compile *.py` or `pytest`
- **Execution Verification:** Run test scripts locally

## 3. Local Guardrails & Execution Rules

1. **Verify Before Pushing:** Never push to remote without running local build / analyze commands first.
2. **Circuit Breaker:** If local build/lint fails twice, stop speculative edits, inspect errors, and ask for user guidance.
3. **Zero Placeholders:** Deliver complete, functional implementations without TODOs or stub functions.
4. **Documentation:** Keep README and code comments aligned with code changes.
