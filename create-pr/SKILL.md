---
name: create-pr
description: Open a GitHub pull request with a lean, why-focused description. Use when the user asks to create/open/raise a PR (draft or ready), to write or rewrite a PR description or body, or to push a branch and open a PR. 
---

# Create PR

Open a PR whose description explains why the change exists and what was built, in plain language. Write for a colleague skimming their review queue who wants to know the situation, the approach, and what the pieces are, without reading the diff first.

## Non-negotiable rules

1. **Why, then what you built.** Start with the situation or problem. Then say what you did about it and name the pieces at a useful level of abstraction. Do not narrate the diff line by line, but do tell the reader what's actually in the PR. A description that only explains motivation without saying what was built is as bad as one that only lists files.
2. **No slop.** No AI vocabulary (crucial, leverage, enhance, foster, utilize, facilitate, streamline, comprehensive, robust). No puffery, no sycophancy, no filler phrases ("in order to", "it is important to note"). No em dashes. Use periods or commas only. No synonym cycling. Prefer plain words. Say "use" not "utilize", "help" not "facilitate", "many" not "numerous".
3. **No verification section.** Never add "Verification", "Testing", "Checks", or any passing-tests/lint/CI report. CI reports itself.
4. **No out-of-scope section unless asked.** Omit "Out of scope", "Deferred", "Future work", "Follow-ups" unless the user explicitly asks, or scope was a genuinely contested decision a reviewer must know about.
5. **Write like a person talking to a colleague.** Short, ordinary sentences. Say "we" and "I". Use the names the team says out loud. No literary constructions, no words picked to sound impressive. If you wouldn't say it at someone's desk, rewrite it.

Also: no generated-by footers, no `Co-Authored-By` trailers, no emoji headers, no self-praise, no bold-label bullet dumps that restate what the heading already said.

## Structure

A good PR description has two parts:

**The situation.** One or two sentences on what exists today (or doesn't) and why that's a problem. Start here, not with the mechanics of the patch.

**What you built.** Name the concrete pieces at a level of abstraction that helps a reviewer orient before reading the diff. Default to a bullet list. Bullets are easier for the human brain to parse than prose paragraphs. Each bullet should say what the piece does, not just that it exists. Use prose only when the change is one cohesive thing that doesn't break into separate pieces.

If a reviewer would trip over something (a tradeoff, a surprising decision, something that looks wrong but isn't, a dependency on other work), mention it. If nothing like that applies, stop after the two parts above.

Match length to the change. A one-line fix gets one or two sentences. A multi-file feature gets a paragraph of context and a list of the pieces. Headings only if the body is long enough to need navigation.

## Calibration examples

### Example 1: feature PR (prose + bullets)

This is what a PR description should look like when there are several distinct pieces worth naming:

> Workers need a real harness that can continue Pi sessions and expose each turn through the shared agent contract. I added the following things
>
> - The config for the Pi harness with all the general config stuff and the run logic
> - A model map from our litellm tags to the pi config so we get accurate cost and token window data
> - A generic interface for tools and a pattern for adding new tools. We have transformers to convert our generic tools to whatever format current and future harnesses need
> - Tests for the harness lifecycle and tool action mapping

Note: it says why (workers need a real harness), then lists what was built at a useful level ("a model map from our litellm tags to the pi config" rather than "added models.ts"). Each bullet tells you what the piece does, not just that it exists.

### Example 2: infrastructure PR (context + bullets)

> The control plane and worker need a real transport for AgentRequest and AgentEvent, not just the in-memory one used for tests. I set up a NATS event stream implementing our existing EventStream interface
>
> - Publish and watch functions for both requests and events over the full session lifecycle. Each session subject gets .request and .event suffixes with their own durable consumers so the two directions don't get mixed
> - The watch function returns an async iterator that validates incoming messages against the shared Zod schemas before yielding them. A message that fails validation is never acked so it stays available for redelivery
> - Consumer names are hashed from the subject so they're valid NATS names and stable across restarts
> - close() handles the race where a watcher is still setting up when shutdown starts

### Example 3: small extraction

> In HTTP we run this guard at the FastAPI middleware layer and we run it against the full history
>
> For durable exec the worker picks up the job off of the queue then fetches the full replay log. That then has to run through this token guard as well to ensure we don't send more than the model can take
>
> Instead of duplicating the logic across http and durable exec I moved it into a shared helper then used across both middlewares.

## Anti-patterns

Rewrite anything that reads like these:

- "Rather than X, this moves Y into Z, so the two cannot drift." Too inverted and abstract. Say "Instead of duplicating it, I moved it into a shared helper."
- "This pulls X out into Y, and wires Z to consume it." Still narrating the diff in friendlier words. Say what you did in one clause: "I moved it into a shared helper."
- "The subtlety worth reviewing is..." / "The load-bearing detail is..." Just state the thing.
- "effectively unbounded", "by construction", "genuinely", "materially", "notably". Pick the ordinary word.
- A closing paragraph that restates the opening one in different words. Say it once.
- Defending a rejected alternative at length. The reviewer needs the decision, not the debate.
- Any sentence you would not say out loud to a colleague at their desk.
- Pure motivation with no concrete detail. "We needed better X so this improves X" tells the reviewer nothing about what they're about to look at.
- Pure mechanics with no context. A bullet list of file names or function names without saying why any of it exists.

## Language checklist

Before finalizing, scan for and fix:

- AI vocabulary: additionally, crucial, delve, enhance, foster, garner, landscape (abstract), leverage, pivotal, robust, showcase, streamline, tapestry, testament, underscore, utilize, comprehensive, facilitate, numerous. Replace with plain words.
- Fancy ways to say "is": "serves as", "stands as", "boasts", "features". Just say "is" or "has".
- Filler phrases: "in order to" becomes "to". "Due to the fact that" becomes "because". "It is important to note that" gets deleted.
- Em dashes. Replace with periods or commas. No parenthetical asides as a substitute.
- Passive voice where the actor matters. "queries are validated" becomes "the compiler validates queries".
- Adverbs propping up weak verbs. "significantly improves" becomes the actual improvement, or cut the adverb.
- Promotional adjectives: groundbreaking, stunning, elegant, clean, robust, comprehensive. Cut them.
- "Not just X, but Y." State the point directly.

## Workflow

1. **Confirm authorization.** Never commit, push, or open a PR without an explicit request. "Create a PR" authorizes the whole chain; "write a PR description" does not authorize pushing.
2. **Read the actual change:** `git diff <base>...HEAD`, `git log <base>..HEAD --oneline`, `git status --short`. Never write a description from memory of the conversation.
3. **Find the why.** Check the linked ticket, commit messages, or ask. If the reason cannot be recovered, ask the user rather than inventing motivation or padding with what-narration.
4. **Verify the base and remote branch.** Confirm the base (usually `main`) and that the branch's upstream is not the base itself. Push explicitly: `git push -u origin HEAD:<branch>`.
5. **Stage deliberately.** Only files belonging to this change. Leave unrelated dirty files and user-added debug logging alone; mention them instead of reverting.
6. **Write the body to a temp file** — `mktemp -t pr-body` or `/tmp/pr-body-<branch>.md` — then pass `--body-file`. Use `/tmp` rather than the repo's `local/`.
7. **Create it:** `gh pr create --draft --base <base> --title "<TICKET-123> <summary>" --body-file <path>`. Use `gh`, never a web/MCP route. Default to `--draft` unless the user says ready. In sandboxed environments request escalation up front.
8. **Verify and report:** `gh pr view <n> --json number,isDraft,state,baseRefName,url`. Report the URL and draft state.

## After creating

Offer, without doing it unprompted: linking the PR on the ticket, moving ticket status, or requesting reviewers.
