# Reviewer brief

Only the reviewer reads this file. The coordinator passes its path and does not load it, to keep coordinator context small.

One reviewer assesses naming, simplicity, quality, correctness, and security together. Read and reason about the changed paths. Do not rerun the test suite.

Return separate naming, simplicity, quality, and correctness/security sections, ranked actionable findings, and a clear `clean` or `changes needed` verdict.

## Naming (mandatory)

Review every changed file name, directory name, function, method, type, interface, variable, configuration field, and new abstraction. Ask whether the name directly describes the current behavior and responsibility in the repository's existing vocabulary. Flag names that are vague, generic, misleading, unnecessarily indirect, or that imply a new architectural pattern the codebase does not use. Also flag helper names that hide a simple value transformation or expose an implementation detail instead of the domain action. For each material finding, propose a simpler concrete name and explain why it matches the behavior better. Do not accept a name merely because it is technically accurate or tests pass. Return `changes needed` when poor naming materially increases parsing effort or suggests the wrong ownership or pattern.

## Simplicity (mandatory)

Compare the implementation with the required behavior and the repository's existing primitives. Identify anything that can be removed, collapsed, or expressed directly without losing required behavior. Review at least these risks:

- abstractions, wrappers, indirection, or state that serve only one current use;
- speculative flexibility for unrequested future cases;
- defensive normalization, retries, fallbacks, or compatibility behavior without a stated requirement;
- duplicated responsibilities or logic that an existing primitive already owns;
- interfaces, configuration, dependencies, or helper types that expose more than the current contract needs.

For each material complexity finding, give the simpler concrete design. Do not accept vague advice such as "simplify this." Passing tests does not justify unnecessary complexity. Return `changes needed` when the code is correct but materially more complex than the requirements demand.
