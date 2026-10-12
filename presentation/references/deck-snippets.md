# Deck snippets

Use these classes instead of inline styles. Each block is a complete pattern. Copy it and change the text.

## Lead sentence

```html
<p class="lede">State the point in one or two sentences.</p>
```

## Two columns: code beside bullets, or done beside next

```html
<div class="cols">
  <pre class="code-block"><code class="language-python">...</code></pre>
  <ul>
    <li>Point one.</li>
    <li>Point two.</li>
  </ul>
</div>
```

## Cards: independent facts, each with a label

```html
<div class="cards">
  <div class="card"><div class="card-label">Slow streaming</div><div class="card-body">One complete idea.</div></div>
  <div class="card"><div class="card-label">Hard format</div><div class="card-body">One complete idea.</div></div>
</div>
```

## Flow: a sequence of steps with actors

```html
<div class="flow">
  <div class="flow-step"><div class="card-label">1 &middot; Frontend</div>Sends the schema</div>
  <div class="flow-arrow"></div>
  <div class="flow-step"><div class="card-label">2 &middot; Python</div>Checks the input</div>
</div>
```

Keep a flow to six steps or fewer. Split longer sequences across slides.

## Compare: before and after

```html
<div class="compare">
  <div><span class="badge badge-warn">Before</span><pre class="code-block"><code>...</code></pre></div>
  <div><span class="badge badge-decision">After</span><pre class="code-block"><code>...</code></pre></div>
</div>
```

## Code that might be wide

Break long lines in the source. A cut-off code line is a verification failure the checks may miss.

