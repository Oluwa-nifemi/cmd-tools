# Interactive brief

Start with the fields in [common.md](common.md). Add the interactive fields
below.

Use this format only when the user explicitly asks for an interactive
presentation. It fits when the reader needs a mental model of how something
works, and text alone would confuse them. There must be something to show as a
visual. For a list of decisions or a status update with no mechanism, use page.

The reader scrolls story chapters on the right. A sticky visual model, the
stage, sits on the left. Each chapter sets a stage view. Widgets in the chapter
change the stage.

## Interactive fields

~~~markdown
## Reader profile
<who reads this. What they already know. What they do not know. Be concrete.>
Knows: <e.g. uses LLMs daily, writes JavaScript>
Does not know: <e.g. linear algebra, what a layer is, research jargon>

## Terms to explain
<every term the reader will meet, in first-use order, with a one-line plain
meaning. The renderer explains each one before or at first use.>
- <term>: <plain meaning>

## Honesty label
<one or two sentences shown under the stage: what is real data and what is
illustrative>

## Stage
<the persistent visual model: what it shows, its parts, and its views. 2D SVG
or canvas is the default. Ask for 3D only when depth carries meaning.>
Views: <view-id — what the stage shows in this view>
Controls: <state keys the stage accepts, with allowed values>

## Chapter outline
<ordered. One `### Chapter:` block per chapter.>

### Chapter: <title>
View: <stage view id>
Claim: <one plain sentence — the point of the chapter>
Analogy: <an everyday comparison>
Mechanism: <how it works, in plain words, with a concrete example>
Widget: <one control group, the one result it shows, and the stage keys it changes>
Likely questions: <"wait, but…" questions this reader will ask, with answers>
Go deeper: <formulas, symbols, exact numbers, and paper details — optional>
Source: <inline | /path/to/file.md (section)>

## Node tree (optional — for drill-down, e.g. codebases)
<indented list. Each line: id — level — title — source. The first line is the
root. Levels usually go system → component → module → file → function.>
- system — system — Muninn — research-notes.md (Overview)
  - recall — component — Recall — steps/step-2-recall.md
    - recall-query — file — src/muninn/recall.py — src/muninn/recall.py

### Node: <id>
Claim: <one plain sentence>
Mechanism: <how it works, with one concrete input and output>
Talks to: <other nodes it calls or is called by, and what passes between them>
Code: <file:line of the excerpt to show — file and function levels only>
Likely questions: <with answers>
Source: </path/to/step-file.md (section)>
~~~

## Brief rules

- Write the reader profile from what the user said about themselves. Do not
  assume math or research background.
- Every number in Claim, Mechanism, or Widget states what it measures, the
  baseline, and why it matters. Otherwise it moves to Go deeper.
- One widget shows one result. Split a widget that shows two.
- Collect likely questions from the source discussion. A question the reader
  already asked belongs in the chapter where it comes up.
- For a node tree, every node needs a source file with file:line references.
  Never write node content from file names alone.

## Worked example: a model-internals explainer (condensed)

~~~markdown
# Presentation brief

## Format
interactive

## Audience
self

## Purpose
explainer

## Output path
/Users/me/Documents/jspace-lab/outputs/jspace-walkthrough/index.html

## Title
A model thinks words it never says

## Subtitle
A walkthrough of the J-space paper, one idea at a time

## Source files to read
- /Users/me/Documents/jspace-lab/NOTES.md

## Reader profile
Knows: uses LLMs daily as a software engineer; knows a model predicts one token at a time.
Does not know: linear algebra, what a layer or vector is inside a model, research terms like "ablate" or "Jacobian".

## Terms to explain
- layer: one processing step; the model runs the input through dozens in order
- vector: a list of numbers that stands for one word's current meaning
- J-lens: a way to read which words a hidden spot pushes the model toward
- ablate: remove a pattern and see what breaks

## Honesty label
Claims and numbers come from the paper. The per-layer traces on the stage are illustrative.

## Stage
A column of layers, bottom to top. Each prompt word is a lane. Readable words glow where the lens can read them.
Views: layers, bands, swap, snap
Controls: country=France|China, band=sensory|workspace|motor

## Chapter outline

### Chapter: One edit, many readers
View: swap
Claim: Change "France" to "China" inside the model once, and every question about the country follows.
Analogy: One shared note on a whiteboard. Many people read it, so one edit changes all their answers.
Mechanism: The prompt text still says France. Researchers subtract the France pattern in the middle layers and add the China pattern at the same strength. The capital, language, and currency answers all switch to China.
Widget: toggle France/China; the stage shows one entry changing and three answers following. Changes: country.
Likely questions:
- Is the prompt changed? No. Only the internal pattern changes.
- How do they know it knew the currency? They ask for it and read the answer; it says yuan after the swap.
Go deeper: patch strength, layer range, success rates per question type.
Source: /Users/me/Documents/jspace-lab/NOTES.md ("Swap")
~~~
