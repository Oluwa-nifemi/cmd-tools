# Fetching traces

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

Build it with a short script from the user's sheet. Check the sheet first: look for a
"side by side" or summary tab, missing runs, and which run is the baseline. Ask the user
when run numbers do not line up across groups.

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
