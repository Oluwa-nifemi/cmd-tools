Do ONLY this task. Do NOT call TaskList/TaskUpdate or claim/start any other task.
Do NOT spawn further sub-agents — do the work yourself. Do NOT delete the
existing/legacy code path. When done, write your full report (files changed,
what you did, actual test output, anything you were unsure about) to your OWN
report file `<build-folder>/reports/<unit>-<role>.md` (e.g.
`reports/unit3-auth-doer.md`) — one file per agent, which you create fresh and
own, so you never overwrite another agent's file or hit the "read before
overwrite" rule on a shared file. Then send a SHORT summary via
SendMessage(to:'main') — verdict, one-line test result, and your report
filename as the pointer. Do not paste the full report into the message. Then
stand down and remain idle.
