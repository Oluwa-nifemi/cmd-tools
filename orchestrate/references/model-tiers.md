# Model and effort tiers

Single source for model and reasoning-effort choices. It lives in one file so tiers change in one place when models change.

Pass an explicit `model` and `reasoning_effort` on every dispatch. If you omit them, the sub-agent inherits the coordinator's expensive settings and tiering is lost. State the unit type, tier, and effort in the dispatch message or log entry. After dispatching, check every call carries both arguments.

| Tier | Use for |
|---|---|
| Luna | Mechanically specified work: fixed-format extraction, inventory, lint/syntax checks, status reads against an unambiguous spec |
| Terra (default) | Routine work and review: scoped build units with a written spec, documentation, search-and-summarize, standard code review |
| Sol or Opus | Rare high-consequence judgment: adversarial/security review, ambiguous requirements needing synthesis, irreversible or cross-system decisions. Not "to be safe": it costs more and adds little on routine work |

If a task has one high-risk judgment inside routine work, split it into its own unit. Do not raise the tier for the whole task.

## Respecting the model choice

If the user names a model or tier, use it. Do not move a unit to another tier on your own; split the unit until the chosen model can finish each piece. Raise effort before changing model.

## Lower-cost workhorse models

Lower-cost models (for example DeepSeek at low effort, or Haiku) are reliable implementers when the brief is complete and the unit is sized for them (see Unit sizing in [build.md](build.md)). They do well on implementing a specified unit, mapping and tracing code, building fixtures and prepared environments, mechanical edits, and first-pass review against a checklist.

They struggle when the brief leaves them to discover an interface, wait on another unit, or hold several concerns at once. They then read in loops, announce a patch while still reading, and ignore bounds restated in prose. Fix those with brief shape and sizing, not with reminders.

For work that spans layers, an optional spec step can write the unit briefs first, contracts first. It can run on the same model at higher effort. Use another model only if the user chooses it.

Effort is chosen by the unit, not by the model tier:

| Effort | Use for |
|---|---|
| low (default) | Code reading, tracing, scoped research, implementation, tests, docs, routine debugging, ordinary review. A review label alone does not justify medium |
| medium | A concrete ambiguity or cross-system correctness risk that low is unlikely to resolve. Name the risk in the dispatch message |
| high | Adversarial security review, subtle distributed control flow, irreversible decisions. Name the risk in the dispatch message. Not for ordinary research or code reading |

Never go above `high` (no `xhigh`/`max`/`ultra`) for a delegated unit. Extra effort rarely changes the result on delegated units.
