# Interactive rendering

An interactive artifact teaches how something works. The visuals lead and the
text explains them. The reader should understand each chapter without coming
back with questions.

## Layout

- **Stage** (`#stage`, left, sticky): one persistent visual model. It changes
  view as the reader scrolls. 2D SVG or canvas is the default. Use Three.js
  only when the brief asks for 3D.
- **Story** (`#story`, right): chapters, one `article.chapter` each.
- **Honesty label** (`#honesty`, under the stage): what is real data and what is
  illustrative. Copy it from the brief.
- **Depth toggle**: Overview shows only each chapter's claim. Full shows
  everything except closed Go deeper sections.
- **Explore freely** (`#explore-btn`): free-play controls for the whole stage.
- **Inspector and legend**: hovering a stage part shows what it is. Call
  `window.Shell.inspect(html)` and `window.Shell.legend(items)`.

The shell script already handles chapter sync, depth, explore mode, and
control clicks. Do not rewrite it.

## Template regions

Edit only these regions:

- `STAGE:START..STAGE:END` — the stage code. Replace the sample.
- `CHAPTERS:START..CHAPTERS:END` — the chapters. Delete the example chapter.
- `EXPLORE:START..EXPLORE:END` — free-play controls.
- `NODES:START..NODES:END` — drill-down nodes. Leave empty when the brief has
  no node tree.

Add stage CSS in a `<style>` block inside the stage region or at the end of
`<head>`. Do not change the shell CSS.

## Stage contract

~~~js
window.Stage = {
  show(view, nodeId),// switch view; nodeId is set when a drill-down node opens
  set(key, value),   // change one state value; called by controls
  state()            // plain object with view, node, and every control key
};
~~~

`state().view` must equal the active chapter's `data-view`. Every value a
control can change must appear in `state()`, or verify cannot see the change.
When a node is open, `state().node` must equal its id. Set it to `null` when
`show` is called without a node id.

## Drill-down nodes

Use drill-down when the brief has a node tree, for example a codebase with
system, component, module, file, and function levels. The story chapters are
the guided tour. The nodes are a map the reader can click through at their own
pace, from the whole system down to code.

~~~html
<article class="node" id="node-recall" data-node="recall" data-parent="system"
         data-level="component" data-view="recall">
  <h2>Recall</h2>
  <p class="claim">Finds the memories that match the current prompt.</p>
  <div class="full">
    <p>How it works, in plain words, with one concrete input and output.</p>
    <div class="question"><strong>Wait, but…</strong>Answer.</div>
  </div>
  <p class="source">src/muninn/recall.py:42</p>
  <pre class="code">def recall(query): ...</pre>
  <details class="deeper"><summary>Go deeper</summary>Edge cases, config.</details>
</article>
~~~

Rules:

- Exactly one root node (no `data-parent`). Every other node's parent exists.
- Node ids use lowercase letters, digits, and hyphens.
- Every node has a visible `.claim`. The shell shows it as the one-line gist in
  the parent's "Inside this" list.
- The shell builds the breadcrumb and child list. Do not write them by hand.
- Put `data-open-node="id"` on stage parts so clicking the diagram opens that
  node. The root view must have at least one clickable part.
- Any element can use `data-open-node`, for example a chapter link into the map.
- Levels get more concrete as they go down. Code appears only at file or
  function level, as a short excerpt in `pre.code` with a `.source` path and
  line number above it. Explain what the excerpt does before showing it.
- A node's `data-view` must be a view the stage supports. The stage should
  highlight the open node, or zoom to it, so the reader sees where they are.
- URLs use `#node=<id>`, so every node can be linked directly.

## Chapter structure

Each chapter follows this order. Only the claim is required.

~~~html
<article class="chapter" id="ch-swap" data-view="swap">
  <span class="chapter-num">Chapter 8</span>
  <h2>One edit, many readers</h2>
  <p class="claim">One plain sentence that states the point.</p>
  <div class="full">
    <p class="analogy">An everyday comparison.</p>
    <p>The mechanism in plain words, with a concrete example.</p>
    <div class="widget">
      <span class="widget-label">Try it</span>
      <p>What to click and what to look for.</p>
      <div class="controls" data-control-group>
        <button data-stage-control data-set="country=France" data-changes="country" aria-pressed="true">France</button>
        <button data-stage-control data-set="country=China" data-changes="country">China</button>
      </div>
    </div>
    <div class="question"><strong>Wait, but is the prompt changed?</strong>No. Only the internal pattern changes.</div>
  </div>
  <details class="deeper"><summary>Go deeper</summary><p>Formulas and exact numbers.</p></details>
</article>
~~~

Control attributes:

- `data-stage-control` marks a button the verifier clicks.
- `data-set="key=value;key2=value2"` calls `Stage.set` for each pair.
- `data-changes="key,key2"` lists every state key the click may change. Verify
  fails if a click changes an undeclared key, including `view`.
- `data-control-group` groups buttons so only one is pressed at a time.

Use `<details>` only as `details.deeper`. Lint rejects any other `<details>`.

## Writing rules

Write for the reader profile in the brief, not for an expert.

- Explain every term before or at its first use. Use the brief's term list.
- Use one term for one concept throughout.
- Short sentences. One idea per sentence.
- Formulas, symbols, and variable names go only in Go deeper.
- Every visible number states what it measures, the baseline, and why it
  matters. If you cannot say all three, move the number to Go deeper.
- One widget shows one result. The widget text says what to click and what to
  look for on the stage.
- Answer the brief's likely questions in the chapter where they come up. Add
  any other "wait, but…" question this reader will obviously ask.
- Label stage parts in plain words. No bare numbers or codes on the stage
  without a label or inspector text.
- If the stage shows something that looks like it contradicts the text (for
  example, lights appearing to move backwards), say why in the chapter.

## Build flow

Interactive artifacts are built by two Opus agents, one after the other:

1. **Stage builder**: writes the stage, explore controls, and a spec file
   beside the artifact (`<artifact-stem>.stage-spec.md`). The spec lists every
   view, every state key with allowed values, and what each looks like.
2. **Writer**: reads the spec and the brief, then writes the chapters. The
   writer must only use views and keys from the spec. If a chapter needs a new
   view or key, the writer adds it to the stage and to the spec.

Each agent runs lint and verify before it finishes.

With drill-down, the stage builder also makes every stage part clickable and
lists the node tree in the spec. The writer writes the chapters and every node.
For a large tree, the writer may split the node writing into batches by
branch, but one agent owns the whole artifact.

### What each agent reads

- **Stage builder**: the brief and this skill's renderer files. The brief's
  Stage section and node tree hold everything the map needs. Do not read the
  research or step files. If the brief is missing something the stage needs,
  say so in the report.
- **Writer**: the brief, the stage spec, and, one branch at a time, the source
  files that branch cites. Read a branch's sources just before writing it.

### Build order

Follow the "Write in small pieces" rules in the renderer guide. In addition:

- **Stage builder**: write the spec first. Then build the artifact in this
  order, one or more edits each: stage CSS, stage SVG, state and controls,
  node stubs (one edit per top-level branch), explore controls.
- **Writer**: write the chapters first, one or two per edit. Then write the
  nodes one top-level branch at a time. Run lint after each branch.

## Self-check before reporting

Read the artifact as the reader in the brief's profile. Fix every "yes":

- Is any term used before it is explained?
- Does any visible number lack what it measures, a baseline, or why it matters?
- Does any widget show more than one result?
- Is any likely "wait, but…" question left unanswered?
- Does any stage label or number have no explanation?
- With drill-down: can the reader reach every component from the stage? Does
  every code excerpt say what it does before it is shown?

Report the checklist result with the verify result.

## Dependencies

Keep the artifact self-contained. If you need a library such as Three.js,
vendor it into a file beside the artifact and load it with a relative path.
Do not load from a CDN.
