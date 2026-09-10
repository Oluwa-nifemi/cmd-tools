# Interactive visualization rendering

Build a small explanatory instrument: the viewer changes something, sees the
process respond, and understands why. A presentation still needs a narrative;
give each scene one question and an observable takeaway.

## Visual language

The initialized shell uses the deck/page tokens unchanged: paper `#f5f3ee`,
secondary paper `#efece4`, ink `#1c1b18`, rule `#d8d2c6`, green `#3a6b3a`,
green wash `#eaf0ea`, amber `#9a6a2f`, amber wash `#f3ebdd`. Retain Palatino
headings, Georgia body, and Menlo labels. Use quiet rules and whitespace;
let the process occupy most of the screen. Give green to active/confirmed
states and amber to waits/caveats. If a failure color is needed, a restrained
rust can supplement the palette; label the state as well as coloring it.

Avoid dashboard-like card grids, ornamental particles, fake browser chrome,
or continuous movement that explains nothing. A before/after comparison is
useful when it holds the same inputs constant. Do not copy technical details
from an example into unrelated topics.

## Authoring

Run `init --format visualization`. Replace the title/subtitle, the topic style
region, and the topic script region. Do not read the source template before
initializing; edit the output. The starter contains a working example of a
stepped process, not the required diagram for every subject.

The shell accepts a `scenes` array. Each scene has `title`, `description`,
`steps` (number of transitions), `reset()` and `render(step)`; optional
`narration(step)` returns a short explanation. Render into `#viz-stage` and
return an explanation or use `narration`. Scene navigation resets the chosen
scene and pauses playback. `presentation.refresh()` redraws the current step;
`presentation.pause()`, `.reset()`, and `.go(index)` support topic controls.
The starter also provides `presentation.inspect(path)` and
`presentation.closeInspection()`. A scene may implement `inspect(path, step)`
returning `{title, html, bind?}` for each hierarchy level. Buttons with
`data-inspect="component/operation"` open that path; the shell supplies a
breadcrumb, Back, Close, Escape, and focus return. The inspector refreshes with
simulation state. You may adapt the inspector to the subject while retaining
those behaviours. The shell owns one playback timer. Keep topic state explicit and derive
visible values from it. Prefer synchronous, deterministic state transitions;
if topic logic needs timers, cancel them on reset, scene change, and disposal.
Avoid replacing focused controls on every refresh; restore focus/selection
when rebuilding is necessary, or update persistent DOM elements in place.

Keep essential controls and at least one useful result in the first viewport.
A few scenes may combine guided playback with direct experimentation. Choose
controls suited to the mechanism: step through a request, inject a failure,
adjust capacity, switch policies, or inspect a stage. All controls must have
real consequences in the model. Label synthetic numbers and timing. Explain
what a reset clears. Keep long source material in a secondary appendix only
when needed; essential explanations belong next to their visual evidence.

## Explore inside the process

Support nested exploration when the audience needs the mechanism behind a
component. Keep the overview understandable, then let the viewer open an
actor or stage and explore its internal steps, state, or data. For technical
processes, aim for a useful overview → component → specific operation/data
path rather than a collection of tooltip definitions. Choose the hierarchy
from the actual subject; do not invent internals just to add depth.

Use a labelled inspector or in-place drill-down with a breadcrumb and Back /
Close controls. Keep the parent context visible or easy to recover. Tie the
inspector to live simulation state so its entries, counts, or gates agree with
the overview. Opening details should pause playback if continued movement
would disrupt reading; closing details should preserve the simulation step
and settings. Scene changes should reset the inspection path to a valid root.
Use native buttons for inspectable nodes or provide adjacent keyboard-accessible
Inspect controls. Essential outcomes remain visible outside the inspector.
A mobile inspector must fit and scroll without covering its own navigation.
Do not reuse deck/page appendix-only folding restrictions for this format:
nested mechanism exploration is a primary interaction, not hidden appendix text.

## Interaction and accessibility

- Start paused with an understandable initial state. Preserve Play/Pause,
  Step, Reset, and scene navigation. Stop at the final step; do not loop.
- Make reset repeatable and replay deterministic for the same inputs. Keep
  controls truthful at boundaries and when settings change during playback.
- Prefer native buttons and labelled inputs. Clickable diagram nodes need
  keyboard equivalents. Do not use hover as the only explanation.
- Preserve focus-visible styles. Arrow-key scene shortcuts must ignore
  focused inputs, buttons, editable content, and modifier shortcuts.
- Reduced motion removes travel/tween effects, not state changes or controls.
- On mobile, reflow diagrams or give a labelled, contained pan region; never
  shrink important labels into illegibility. Permit vertical scrolling.
- Use inline SVG/HTML for exact diagrams and vanilla JS by default. Deliver
  a self-contained HTML file without remote fonts, scripts, or fetches.
- Preserve print styling and the labelled current-scene snapshot. A PDF
  cannot retain the interactive behaviour; HTML is the primary artifact.

Read [verification.md](verification.md) before reporting completion.
