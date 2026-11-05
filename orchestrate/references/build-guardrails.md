# Build guardrails for doers

Do only the assigned unit. Do not claim another unit or spawn sub-agents. Do not delete a working or legacy path until its replacement has passed the required verification.

Write a full report to the assigned fresh report file: changed paths, behavior, actual test output, and unresolved concerns. Send the coordinator only the verdict, one-line validation result, and report path; then stand down. Do not paste the full report into the coordinator conversation.

Before editing, record baselines for the checks your acceptance relies on (build, type, and test results). Never call a failure pre-existing without citing the baseline run.

Run the unit's acceptance command yourself before reporting done. Passing unrelated suites does not prove the behavior.

If you cannot make your first change within the bound in your brief, stop and report the exact blocker instead of continuing to read. Do not widen the scope; report what else needs changing.
