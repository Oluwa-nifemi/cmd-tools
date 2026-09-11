---
name: codex-scheduling
description: Create, update, inspect, pause, resume, or delete Codex reminders and recurring automations. Use whenever the user asks to schedule, remind, monitor, follow up, run later, or verify that a Codex automation exists or ran.
---

# Codex Scheduling

Use the Codex automation tool. Never emulate scheduling with shell processes, calendar files, or hand-written automation configuration.

## Choose the automation kind

- Use a heartbeat for reminders, monitors, and follow-ups in the current task.
- Use a cron automation only when the user explicitly wants a standalone project job or a new task for each run.
- For a cron automation, list projects first and use the exact project ID. Confirm whether the project is a Git repository before selecting its execution environment.

Keep notification preferences out of the prompt. Set them through `notificationPolicy`.

## Resolve time before creation

1. Resolve relative dates against the current date and the user's timezone.
2. State the exact local date, time, and timezone before creating the automation.
3. If the requested date has already passed, stop and ask for a new time.
4. For ambiguous times, ask one concise question. Do not silently select a timezone or interpretation.

## One-time exact reminders

A one-time reminder needs an anchored schedule that preserves the requested timezone.

- Use a timezone-aware `DTSTART` with one occurrence.
- Do not use an unanchored `COUNT=1` rule. It can bind to the wrong occurrence.
- If immediate creation rejects `DTSTART` and requires `suggested_create`, use `suggested_create`. Tell the user that the card still needs acceptance.
- A rendered suggestion card is not a scheduled automation. Do not claim success until the accepted automation returns an ID and persists.

## Recurring schedules

Use the simplest recurrence that matches the request. Preserve the user's timezone and requested weekdays. Do not add extra runs, status updates, or notifications.

For monitors, make the prompt quiet while nothing changes. Notify only on a meaningful change, completion, failure, or required user action unless the user requests periodic reports.

## Existing automations

Before creating a likely duplicate, inspect `$CODEX_HOME/automations/*/automation.toml` for a matching name or prompt. Update the existing automation when it represents the same task.

For updates:

1. Resolve the automation ID from the saved file or automation listing.
2. View the current automation.
3. Preserve fields the user did not ask to change.
4. Send the full updated configuration.

Treat “mute” or “do not notify me” as `notificationPolicy=failed_runs_only`. Set it to `null` when the user asks to unmute.

## Required verification

Never treat a card, successful tool invocation, or `ACTIVE` alone as proof. After creation or update, require an automation ID and verify all of these:

1. The automation exists under that ID.
2. Its status is `ACTIVE`, unless the user requested `PAUSED`.
3. Its prompt matches the requested work.
4. Its target is correct. For a heartbeat, verify the exact task ID. For project work, verify the exact project and worktree.
5. Its saved recurrence matches the requested local time and timezone.
6. It has a future occurrence after its creation or update time.

Use the automation view operation first. Also inspect the persisted `automation.toml` when local access is available. For a one-time schedule, calculate the next occurrence from the saved anchor and timezone. Do not infer it from the prompt text.

If any check fails, say the automation is not scheduled. Fix it when possible. Otherwise state the exact blocker and the smallest user action needed.

## Confirming execution

Saved configuration proves scheduling only. When the user asks whether an automation ran, inspect its run state or result. Do not use the configuration timestamp as execution evidence.

## Final response

After verified creation, report only:

- the exact next run time with timezone;
- whether it is one-time or recurring;
- the target task or project;
- the automation ID.

If user acceptance is pending, say clearly that it is not scheduled yet.
