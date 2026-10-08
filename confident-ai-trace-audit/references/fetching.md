# Fetching traces

## Discovering traces from a description

`scripts/discover.py` lists the project and keeps traces inside a UTC window that match
`--name`, each `--meta key=value`, and `--user-id`. Useful fields on list results:
`startTime`, `latency`, `name`, `status`, `userId`, `threadId`, and `metadata`
(for ardoq_assistant: `org_label`, `model`, `agent_type`, `user_id`, `trace_id`).
The list has no input text, so `--with-question` downloads each candidate to read its
first user message. Those files go to `raw/`, and fetch.py reuses them.

- Runs started together form one time cluster (`--gap-min`, default 10 minutes). One
  eval run usually shows as one cluster with one trace per question.
- Labels such as "code exec" vs "direct" are often not in the metadata. Infer them from
  the description and cluster order, then confirm with the person.
- Pass the same `--meta` filters you would use to describe the run in words. Check
  "varying metadata" in the summary: a key that varies where it should not means the
  filter caught other runs.

## Manifest

`manifest.csv` columns:

| Column | Required | Meaning |
|---|---|---|
| trace_id | yes | Confident uuid or OTel trace id |
| unit | no | Analysis unit, e.g. question id `q07`. Default: the trace id |
| group | no | Comparison group, e.g. `code_exec` / `direct`. Default: `all` |
| run | no | Run number inside the group |
| score | no | Eval score for the run |
| label | no | Question text or short description |

Build it with a short script from the sheet. Check the sheet first: look for a
"side by side" or summary tab, missing runs, and which run is the baseline. When run
numbers do not line up across groups, compare the runs that exist and note it under
Assumptions.

## Running fetch.py

```
python3 <skill>/scripts/fetch.py --audit <dir> --agent-name ardoq_assistant --since 2026-10-01
```

- Needs network. Run with sandbox escalation.
- Re-runs skip traces already in `raw/`.
- `--agent-name` narrows the metadata.trace_id join when one OTel trace holds several agent
  traces. `--since` stops paging the list once traces are older than the eval.

## Known quirks

- **Ids in sheets are often OTel ids.** Fetching them as uuids returns 404. The script then
  lists the project and joins on `metadata.trace_id`.
- **Keys.** `CONFIDENT_API_DEV_KEY` first, then `CONFIDENT_API_KEY`. A 404 with one key can mean
  the other project. The eval key is a separate project and is not used.
- **Host.** `https://eu.api.confident-ai.com/v1`. `api.eu.confident-ai.com` does not resolve.
- **Header.** Raw key in `CONFIDENT_API_KEY`. `Bearer` returns 401.
- **Size.** Full traces are often 1-2 MB. 250 traces is about 400 MB. Keep them in `/tmp` or
  `local/`.
- **No span filter in the list API.** To find all traces that call one tool, filter by span
  name in the Confident UI, copy the trace ids, and fetch those. Random sampling of the
  project under-samples rare tools badly.
- **Truncated prompts.** Stored LLM inputs can stop at about 100k characters. Do not use
  traces to prove what the system prompt contains; render it locally instead.
