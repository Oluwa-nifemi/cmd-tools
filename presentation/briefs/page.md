# Page brief

Start with the fields in [common.md](common.md). Add the page fields below.
A page is one scrolling document with an anchor table of contents.

## Page fields

~~~markdown
## Section outline
<ordered list. Each section is a `### Section:` heading with these sub-fields:>
<- Source: inline, or absolute file path(s)>
<- Content: everything the reader needs; pages keep content visible>
<- Visuals (optional): tables, flows, SVGs, or stat grids that fit this section>
<- Notes (optional): rendering hints>

### Section: <section title>
Source: <inline | /path/to/file.md>
Content:
- Point 1
- Point 2
Visuals: <optional>
Notes: <optional>
~~~

## Worked example: scoped plan

~~~markdown
# Presentation brief

## Format
page

## Audience
eng

## Purpose
scoped plan

## Output path
/Users/me/work/api/local/search-latency/page.html

## Title
Cutting /search p99 below 300 ms

## Subtitle
What is slow, the fix, and how we will know it worked

## Source files to read
- /Users/me/work/api/local/search-latency/research-notes.md

## Section outline

### Section: The problem
Source: /Users/me/work/api/local/search-latency/research-notes.md ("Measurements")
Content:
- p99 is 480 ms on /search; the target is 300 ms
- One query per cluster inside `searchClusters` (an N+1 query pattern)
Visuals: a before/after flow of one request, showing the query count

### Section: The fix
Source: /Users/me/work/api/local/search-latency/research-notes.md ("Fix")
Content:
- Batch the cluster lookups into one query
- Input: 40 cluster IDs. Output: 1 query instead of 40

### Section: How we will know
Source: inline
Content:
- Dashboard: /search p99, 7-day window, before and after deploy
- Rollback if p99 rises above 480 ms
~~~
