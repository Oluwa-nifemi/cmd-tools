# Optional deck

Use `$presentation`. Write `presentation-brief.md` first with the numbers, the trace
examples, and the slide order below. Pass absolute paths to the notes and findings.

## Slide order

1. **Cover.** One-line verdict.
2. **Latency.** Raw wall time per group, then the fair version (infra waits removed), with
   one line per bar saying what it removes.
3. **Tokens.** Total, working context, fixed prefix. Say what is cached.
4. **One slide per pattern.** Count, model seconds, one real trace example with code or
   tool calls. Put long code and prompts in popups.
5. **Counterpoints.** Detours that bought correctness; where the baseline really is better.
6. **Fixes.** Ranked table with type, count, and status.
7. **Open questions.**
8. **Appendix.** Per-unit table with a legend for every column header, and the method with
   cross-checks.

## Rules

- Lead with the user's two main questions (usually latency and tokens).
- Every number on a slide traces back to a script output.
- Label ideal-case bars as ideal.
- Use plain column headers, and explain abbreviations in a legend line.
- Run the presentation skill's lint and verify. If verify fails at random on an unchanged
  deck, report that honestly.
