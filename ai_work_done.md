# AI Work Log and Rubric Estimate

## Purpose

This file explains how the static-analysis assignment was completed, what evidence was used, which commands were run, why the fixes were chosen, and what score I estimate under the supplied 30-mark rubric. The full technical report is [reports/assignment_report.pdf](reports/assignment_report.pdf); the editable source is [reports/assignment_report.md](reports/assignment_report.md).

## How the Work Was Done

### 1. Establish the project and baseline

The project is a FastAPI task API with user authentication, SQLAlchemy models, REST task endpoints, and WebSocket notifications. I first checked the Git working tree and recent history so existing work would not be overwritten. The supplied `pylint_report.txt` was UTF-16, so I decoded it instead of treating its displayed byte dump as readable Pylint output:

```powershell
Get-Content -Encoding Unicode pylint_report.txt
```

That showed the original report's score of 0.00/10 and 104 reported messages: 48 convention, 3 refactor, 5 warning, and 48 error findings. Many errors were not application defects: Pylint did not infer the package root correctly, and it could not infer Alembic's runtime-provided migration API. I copied the original report unchanged to `reports/pylint_original_report.txt` so the evidence remains available.

I then checked the existing tests before modifying the application:

```powershell
.\venv312\Scripts\python.exe -m pytest -q --tb=short
```

The original result was 8 passed and 3 failed. The failures showed persistent PostgreSQL test data causing duplicate records and model tests using an unbound SQLAlchemy `Session()`.

### 2. Check the Pylint package-root hypothesis

The initial report contained `relative-beyond-top-level` errors on valid package-relative imports. My hypothesis was that these errors came from Pylint treating `app` as a top-level directory. I tried the smallest discriminating check:

```powershell
.\venv312\Scripts\python.exe -m pylint --source-roots=. app
```

That removed the relative-import errors, confirming a Pylint invocation/configuration problem rather than broken runtime imports. I generated a project config as the starting point:

```powershell
.\venv312\Scripts\python.exe -m pylint --generate-rcfile | Set-Content -Encoding utf8 .pylintrc
```

The `.pylintrc` sets `source-roots=.` and excludes the generated/dynamic Alembic scaffold from the application score. It also disables `too-few-public-methods`, which is low-signal for this project's declarative ORM and settings data classes. The report explains why the 100-character line limit, five-argument threshold, and 12-branch threshold were retained.

Before changing code, I ran and saved the configured comparison baseline:

```powershell
.\venv312\Scripts\python.exe -m pylint --rcfile=.pylintrc app
```

This baseline was 7.69/10 with 43 findings: 40 conventions and 3 warnings. That is the fair before-score because the after-run uses the same Pylint version, package scope, and config. The supplied original 0.00 score is preserved as a separate result, not substituted for the controlled baseline.

### 3. Interpret the findings, then review behavior manually

I grouped diagnostics by the actual quality concern rather than repeating Pylint's C/W/R/E labels. The report analyzes ten examples and labels each A (fix), B (context dependent), or C (acceptable exception), including missing docs, long lines, logging interpolation, exception chaining, naming, unused migration imports, dynamic Alembic members, and package-root errors.

I then read the request paths and database/test setup independently of the diagnostics. That exposed consequential issues Pylint had not reported:

- Task list/read/update/delete queries did not consistently check `owner_id`, allowing cross-user task access.
- WebSocket `send_text()` calls were made without `await`, so notifications were not actually delivered.
- Tests shared persistent DB state and an unbound session, making runs fragile and non-isolated.
- Router-wide HTTP OAuth dependencies also applied to a WebSocket route and prevented its handshake.
- Importing middleware created a file handler as a global side effect.

The first four were addressed and covered by tests. The logging-handler lifecycle is documented with an improvement recommendation but was left outside the targeted changes.

### 4. Improve code and verify behavior

The structural changes added a shared authenticated-user dependency and ownership-checked task lookup, introduced a connection manager that awaits sends and discards stale sockets, and created disposable in-memory SQLite fixtures for endpoint/model tests. Additional focused quality work added useful docstrings, wrapped long signatures, used lazy logging parameters, preserved JWT exception causes, renamed the session factory for clarity, and switched to Pydantic v2's `model_dump()` API.

The key verification command was:

```powershell
.\venv312\Scripts\python.exe -m pytest -q --tb=short
```

Final result: **13 passed**. New tests confirm a second user cannot enumerate/read/update/delete another user's task and that an authenticated WebSocket receives the expected task-created notification. The test suite no longer needs a running PostgreSQL service.

Final static analysis:

```powershell
.\venv312\Scripts\python.exe -m pylint --rcfile=.pylintrc app
```

Final result: **10.00/10, no Pylint messages**. The controlled comparison is 7.69/10 (43 findings) to 10.00/10 (0 findings). The tests still report 14 deprecation warnings inside the pinned `python-jose` dependency; these are not Pylint findings and not emitted by the changed project code. A production run against the configured PostgreSQL service was not performed; API behavior was exercised with FastAPI's test client and isolated SQLite.

### 5. Produce the report, PDF, and repository archive

I wrote the detailed report in Markdown and rendered it to PDF using ReportLab. The renderer is `reports/render_report.py`; the report documents the exact baseline/after counts, selected source excerpts, quality impacts, configuration decisions, five improvements, test evidence, and the static-analysis-versus-review discussion.

To preserve commit history in the archive, I generated and verified a Git bundle:

```powershell
git bundle create reports\assignment_history.bundle --all
git bundle verify reports\assignment_history.bundle
```

The ZIP contains application source, tests, config, reports, PDF, and history bundle. It deliberately omits `.env` and the virtual environments. The original user-provided `pylint_report.txt` was left untouched.

## Commit Progression

The assignment was recorded in separate commits, not one final assignment dump:

- `030dd65` Add static analysis baseline and project config
- `e8d5e11` Enforce task ownership and fix socket delivery
- `da4ccc8` Isolate tests and cover task authorization
- `5ea8cad` Complete quality report and verification evidence
- `5defc56` Document workflow and estimated rubric marks

The bundle preserves these refs and earlier repository history.

## Estimated Marks

This is an evidence-based estimate, not a guaranteed instructor grade. The assignment requirements are substantially covered; I estimate **29/30**, with a plausible range of **28–30** depending on how the marker treats scoped Pylint exclusions and the fact that production PostgreSQL was not started.

| Rubric component | Available | Estimated | Evidence / reason |
|---|---:|---:|---|
| Appropriate project selection and baseline | 2 | 2 | Project description, code statistics, original report preserved, configured baseline captured. |
| Correct use of static analysis tool | 3 | 3 | Pylint 4.0.8 run before and after with a committed, reproducible config and package root. |
| Classification and interpretation | 5 | 5 | Meaningful quality categories and ten findings explained with impact and A/B/C decisions. |
| Manual code review | 4 | 4 | Five manual issues, including multiple defects not reported by Pylint, with evidence and recommendations. |
| Tool configuration and justification | 3 | 3 | More than three settings discussed and justified; source roots and Alembic scope addressed. |
| Code improvements/refactoring | 5 | 5 | Ownership enforcement, WebSocket manager, isolated test setup, exception chaining, current Pydantic API, and other targeted changes. |
| Verification/testing | 2 | 2 | 13 tests pass, including new authorization and WebSocket regressions. Production DB not run, but assignment allows tests as verification. |
| Before/after analysis | 2 | 2 | Same configured tool/scope gives 7.69 to 10.00 and 43 to 0; original raw run is also retained. |
| Critical discussion | 2 | 2 | False positives, limitations, and human-review findings are discussed with project evidence. |
| Git history, evidence, report quality | 2 | 1 | Separate commits, PDF/Markdown, logs, ZIP, and complete Git bundle are supplied. A strict marker may discount that the bundle, rather than the `.git` directory, carries history in the ZIP. |
| **Total** | **30** | **29** | **Likely strong submission; final mark is the instructor's decision.** |

The main grading risk is that a marker may prefer the ZIP to contain a directly browsable `.git` directory rather than a verified Git bundle, or may scrutinize the Alembic exclusion. Both choices are explicitly documented, and the original full Pylint report remains included for comparison.
