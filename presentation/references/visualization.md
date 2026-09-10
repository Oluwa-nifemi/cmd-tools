# Interactive visualization rendering

Build a small explanatory instrument: the viewer changes something, sees the
process respond, and understands why. A presentation still needs a narrative;
give each scene one question and an observable takeaway.

## Visual language

Choose a visual concept around the subject: a field of forces, an editable
signal, an attention matrix, a geographic system, or another structure that
makes its relationships visible. The diagram or simulation should dominate.
Colour, typography, spatial hierarchy, and motion should reinforce that
concept. Different examples should explore genuinely different compositions
and interaction models, not reskin the same arrangement of boxes.

The supplied manuscript palette is available when continuity with deck/page
is wanted. It is not mandatory for visualization. A user reference may provide
an interaction pattern without prescribing its colours or subject. Choose a
coherent new palette when asked; use depth, layers, contrast, and meaningful
motion where they clarify the content. Do not make a static card grid the
primary explanation of a dynamic system.

## Authoring

Run `init --format visualization` to establish a self-contained artifact.
Then adapt or replace its composition, styles, and runtime for the topic. The
starter demonstrates one stepped process; its scenes API and inspector are
optional implementation aids, not a mandatory architecture. Preserve the
HTML shell checks and accessible controls, but let the topic dictate whether
the primary view is a canvas, spatial diagram, linked plots, matrix, or other
interactive surface.

If reusing the starter runtime, it accepts a `scenes` array. Each scene has `title`, `description`,
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
Combine guided explanation with direct experimentation when useful. Direct
manipulation should change the visual itself: drag a parameter, edit a signal,
select a token, change a boundary condition, or isolate a component. Couple
views so a change is reflected in the relevant equations, traces, or outputs.
Use real computations with explicit assumptions. Distinguish a toy model from
a measured or trained system. Continuous systems may run until paused, with
a bounded history and stable integration; do not force them into finite
slide steps. Give the reader a discoverable experiment and a visible result. Choose
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
path rather than a collection of tooltip definitions. Opening a component
should reveal another explanatory visual, manipulable object, or computed
breakdown when the subject permits—not only more prose. Choose the hierarchy
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
  Step, Reset, and navigation where applicable. Finite sequences stop at their
  final state; continuous simulations clearly show running/paused state.
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

## Quality review

When the user requests an independent audit, give a separate reviewer the
finished artifacts and the user’s brief. Have them exercise the controls,
verify the model’s essential invariants, inspect the visuals, and report
specific defects with reproduction steps. Repair material defects and recheck
them before delivery. A verifier passing or a screenshot alone does not prove
that the presentation teaches its subject or feels interactive.
