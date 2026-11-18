---
name: lecture-notes
description: Turn a lecture's slides (PDF or Jupyter notebook) into a complete StudyHub lecture - notes that explain the meaning, SVG figures, an Explained section, broad flashcards, an exam-style quiz and generated calculation problems - in the exact format and quality the user expects. Use when the user adds a new lecture, asks to (re)write notes/flashcards/quiz for a lecture, or says "same structure as the other lectures".
---

# StudyHub lecture notes

**Layout (engine vs. content).** The engine is the `studyhub` repo (build.py, serve.py, index.html, engine/). Courses live in a separate *content folder* (`content/<course-id>/`, `slides/`, `materials/`, `tools/`); its `build.py` / `serve.py` are thin wrappers that run the engine on that folder. Run every command below from the content folder. `.claude/skills/lecture-notes` there is a symlink to this skill.

StudyHub lives in `StudyHub/` (a git repo). Each lecture is one Markdown file at `content/<course-id>/NN-slug.md`.
`python3 build.py` turns them into `data.js` and `StudyHub-standalone.html`, and it also links each note block to its slide page.
The slides themselves live outside the repo in the course folders, for example `Data mining/Forelesning/link.pdf`. The `pdf:` paths are relative to the folder above `StudyHub`.
In a **shared single-course copy** (e.g. the Data analytics repo) the PDFs go in `slides/` next to `index.html` and the paths start with `slides/` (the PDFs themselves are not committed).

The course ids are `data-analytics`, `data-mining`, `distributed-ml`, `ml-in-practice` and `supply-chain`. Each course has a `course.md` with a **"How the professor tests"** section. Read it first: the quiz must imitate that style.

## What the user wants (quality bar, from their feedback)
- **Capture the meaning, not just the facts.** Explain *why* each idea works and what problem it solves. Explain hard concepts step by step, and add a picture when a mechanism is easier to see than to read.
- **Notes must teach, not just list.** The user could not learn from terse bullet lists. Every topic section starts with an **"In plain words."** paragraph (2-4 sentences, everyday language, often an analogy: what problem, what idea), and mechanisms get a **walk-through** with tiny concrete numbers (e.g. a min-hash computed on two 3-element sets, a DGIM bucket merge, a KDE value at one point). Verify these numbers in Python too.
- **Breadth over trivia.** The flashcards and quiz must cover **every section** of the lecture, not a few niche details or rewordings of one slide.
- **Test ideas you can reuse, not the lecture's demos.** A card may use an example to illustrate, but it must ask about the concept or method ("How do you handle codes like -99.99 in a measurement column?"), never about the demo itself ("What do the Mauna Loa columns mean?", "What did the X example show?", the dates of a case or its exact figures). Exception: worked numbers the exam may ask you to compute.
- **Every question and flashcard stands alone.** Quizzes and reviews shuffle items, so never write "Same jobs with…", "For that same document…", "as above" or "(instead of wholesale 5)". Repeat the numbers and the situation in each item, and say what each symbol means ("annual demand D = 12,000, order cost S = 4,000 USD …", not "D = 12,000, S = 4,000. EOQ?").
- **Readable flashcards.** One clear question, and an answer that stands on its own in 1-3 sentences. **Never leave an acronym or symbol unexplained in an answer.** Spell it out in the card itself (the user complained about "COGS" with no explanation). No duplicate cards or questions.
- **Fair MCQs.** The correct option must **not** be the longest one. The user noticed that pattern and learned to exploit it. Make the distractors equally long, specific and plausible, usually the "flipped" version of the true statement.
- **Correct numbers.** Recompute every worked example, iteration table and answer in Python before writing it. Slides often show formulas as images that `pdftotext` drops, so look at the rendered page.
- **Language:** English, plain words, short sentences. Use the course's own terms and notation (match the slides).

## Workflow
1. **Context:**
   - read `content/<course>/course.md` and one or two recent lectures of the same course, to match the tone, depth and notation;
   - pick the next number `NN` and code `L<n>`; the slide title page usually says "Lecture n".
2. **Read the slides completely:**
   - get the text with `pdftotext -layout file.pdf out.txt`;
   - list the page titles: `for i in $(seq 1 N); do pdftotext -f $i -l $i file.pdf - | grep -v '^\s*$' | head -1; done`;
   - render every page whose formula, graph, table or example matters with `pdftoppm -f P -l P -r 50-90 -png file.pdf out/p` and **look at it**. Iteration tables, graphs and equations are often images.
   - Notebook slides: first convert them with `python3 <engine>/engine/nb2pdf.py OUT.pdf NB.ipynb[:first:last]` (see README).
3. **Verify the numbers:**
   - re-derive the worked examples in a short Python script: solutions, iterations, limits and the answers to the slides' "Let's work on it" / "Question" exercises;
   - use these numbers in the notes, the figures and the quiz.
4. **Write the lecture file** in the structure below.
5. **Figures:**
   - write a script `tools/figures/<course-short><NN>.py` that uses `svgkit.py` (in this skill folder; its docstring shows the usage and house style) and writes SVGs to `content/<course>/img/`. Example in the main repo: `tools/figures/dm05.py`;
   - render each SVG to PNG with `svgkit.shot()` and **look at it**. Check for overlapping labels, clipped text and arrows pointing the wrong way, then fix and re-render.
   - 4-7 figures per lecture: the core mechanism, the worked example, comparisons and failure cases.
5b. **Slideshows for algorithms:** every step-by-step algorithm (an iteration, an update rule, a decision procedure) gets a ```steps slideshow in its notes section - the user learns algorithms best this way.
   - Write `tools/figures/<course>NN_steps.py` using `tools/figures/stepkit.py` (`title`, `cell`, `notebox`, `gnode`, `lab`, `save`, and `insert_blocks(md, [(anchor, title, [(frame, caption)])])` - use anchors `before:## Next heading`; re-running replaces the block).
   - One small concrete example, computed in the script (never typed by hand); 4-8 frames of the same 800 x 260 layout so only the highlighted parts change between frames; a one-line bold-led caption per frame.
   - Render all frames to PNG and look at them (overlaps, clipped text, labels on lines) before committing.
5c. **Trace drills:** where a drill kind exists in `TRK` in index.html (minhash, dgim, bloom, fm, ams, pagerank, hits, girvan, conductance, modularity, gd, autodiff, allreduce, las, aimd, maui), put a ```trace block with the kind name at the end of that notes section (after its slideshow). A new algorithm can get a new kind: `gen()` random instance, `view()` with `tin()` inputs, `answer()`, `solution()`; `trSelfTest()` must return [].
6. **Check:** run `python3 .claude/skills/lecture-notes/lint.py content/<course>/NN-slug.md`. Fix every ERROR, and fix the warnings unless they are clearly false positives.
7. **Build and verify:**
   - run `python3 build.py`. It must print the new lecture count and "(… with slide links)";
   - optionally open the lecture in headless Chrome and check that the parser reports 0 warnings, that the images load and that the generated questions evaluate.
8. **Course tagline:** if the lecture adds a new topic, extend the `tagline:` in `course.md`.
9. **Commit and push:**
   - commit the .md, the SVGs, the figure script, `data.js`, `StudyHub-standalone.html` and `course.md`;
   - end the message with the attribution line the session specifies;
   - **never** commit `local-config.js` (it holds the API key), `sync/`, `.slidecache.json` or `__pycache__`.

## File structure (exact)
```
# Lecture 5 - Link analysis (PageRank, HITS)
code: L5
pdf: Data mining/Forelesning/link.pdf


## Highlights
- 5-7 bullets: the key ideas of the whole lecture, each with the core formula or rule in **bold**.

## Summary
## <Topic 1 heading>
> **Key idea:** one or two sentences of intuition for this topic.

**In plain words.** 2-4 sentences in everyday language: the problem and the idea, before any formula.

- **Term:** explanation ... (nested bullets for steps, examples, proofs)
  - Walk-through: the mechanism on a tiny example with real numbers.

![Short alt text](img/figure-name.svg)

## <Topic 2 heading>
...

## Explained
**The big idea.** A paragraph on what ties the lecture together.

**<Hard concept> in words.** Plain-language explanations, analogies and a fully worked hand solution of the slides' exercise.

**Common mistakes**
- 4-6 typical errors (sign or direction flips, wrong formula variant, a misread definition).

## Flashcards
Q: ...
A: ...

## Quiz
? [mcq] ...
...
<!--broad-qs-->
...scenario / "which method fits" / multi / short questions...
<!--/broad-qs-->

<!--gen-->
...[gen] randomised calculation problems...
<!--/gen-->
```

### Homework and quiz files (code HW<n> or Q<n>)
- These get their own page in the app (a worksheet of questions, Key points, Flashcards) instead of the 4-step flow. Use `code: HW3` and add `covers: L4` (the lecture codes it tests) so wrong answers link to the right notes.
- Use the **real question text and options in their original order** from the course site. If only the answers are available, write plausible distractors, keep the correct option no longer than the longest distractor, and say in the Highlights that the options were reconstructed.
- Check every answer key against the slides; when a key looks wrong, keep it but explain the conflict in the question's `>` line and in Explained.
- File names `00a-hwNN-slug.md` keep homeworks sorted before the lectures.

### Rewording an existing question or flashcard
Progress is stored per item under an ID made from its exact wording. When you change the text of a `?` question or a `Q:` card the user may already have answered, put the old wording on the line right after it, so the app moves the progress over:
```
? [calc] Two jobs of length 20 and 15 are queued at the same time. What is the average job completion time (JCT) with Shortest-Job-First?
<!-- was: Same jobs with Shortest-Job-First: average JCT? -->
= 25 ±0.01
```
Changing answers, explanations or options needs nothing. Changing a `##` notes heading resets that section's Hide & explain history.

### Parser rules that bite
- A `##` heading starts a new section **if it begins with** `highlight`, `explain`, `example`, `flash`, `quiz` or `question` (case-insensitive). Any other `##` heading stays in the notes as a topic heading.
  - So **never** start a notes heading with those words. Write "Worked case: …" or "Scraping case 1", not "Example: …".
  - An optional `## Examples` section (worked examples) is allowed after Explained.
- `## Summary` is followed immediately by the first topic heading. Each `##` topic becomes one "Hide & explain" block in the app, so write **one heading per topic**. Aim for 8-12 headings, each a coherent chunk of 3-10 bullets.
- **Subscripts:** `x_i` renders as x<sub>i</sub>. This works for a single-letter base and up to 4 characters, or `x_{abc,d}` for longer ones.
  - Avoid chains like `r_old_j` and `r'_new`, which render as raw underscores. Write `r_old(j)` or name the quantity (`s_j`).
  - `^` renders as a superscript; `**bold**` and `*italic*` work as usual.
- **Tables:** pipe tables work. Write a literal `|` inside a cell as `\|`.
- **Images:** `![alt](img/name.svg)`, relative to the course folder. Leave a blank line around them.
- **Comment lines** `<!-- … -->` on their own line are ignored. Use the `broad-qs` and `gen` markers as in the existing files.

### Notes (Summary) content
- Follow the slide order. Cover **every** slide topic, including motivation, applications, examples, the case studies at the end, and the comparison or summary slides.
- Use bold for each term and define it the first time it appears. Give each formula with its meaning ("… = the probability that …"). Write proofs and derivations as numbered or nested steps.
- Spell out every worked example from the slides with its numbers, and say what the numbers show.
- Put 2-4 `> **Key idea:**` callouts in the topics that need intuition the most.
- Add a Markdown table when the slides compare methods or variants (cost, when to use, differences).

### Flashcards (30-40)
- Write at least 2 cards per topic heading. Mix:
  - definitions;
  - "why / what problem does it solve";
  - "how does it work" (steps);
  - comparisons ("A vs B");
  - small calculations with the numbers and the result in the answer;
  - "what goes wrong if …";
  - the slides' case studies.
- Write each question so it makes sense on its own: name the context ("In HITS, …", "Red Tomato: …").
- Keep answers short: 1-3 sentences, about 420 characters at most. Write acronyms out in full in the card (e.g. "DMOZ, the human-edited Open Directory").
- Multi-line answers are allowed, but prefer one line.

### Quiz (25-35 questions)
Mix the types and imitate `course.md`'s "How the professor tests":

| type | syntax | use for |
|---|---|---|
| `[calc]` | `= 0.467 ±0.002` then `> worked solution` | the slides' numeric exercises, iteration steps, sizes and costs |
| `[mcq]` | 4 options, `* ` marks the one correct option, `- ` the others; `>` explanation | concepts, "which statement is correct", definitions |
| `[tf]` | `= true` / `= false`, `>` why | common misconceptions; mix true and false |
| `[multi]` | `* ` every correct option, at least 3 options | "which are TRUE" |
| `[short]` | `= model answer` (2-4 sentences; it is split into a self-grading rubric at `.` and `;`) | explain or compare |
| `[gen]` | `@ var = v1,v2,v3` (or `a..b step s`), `= formula ±tol` or `±1%`, `> … {var} … = {answer}.` | randomised versions of every formula in the lecture |

- **MCQ option lengths:** keep the correct option at most as long as the longest distractor. Distractors flip one word of the truth (increase/decrease, rows/columns, hub/authority, in-links/out-links).
- In the `broad-qs` block, put scenario questions such as "A company wants X - which method?" and questions that connect several topics.
- **`[gen]` formulas** are JavaScript expressions:
  - `^` means "to the power of";
  - available functions: `sqrt`, `log`/`ln`, `exp`, `pow`, `abs`, `min`, `max`, `round`, `floor`, `ceil`, `PI`, `normcdf`, `normpdf`, `norminv`;
  - write `-(x^2)`, never `-x^2`;
  - every combination of values must give a finite number (the lint checks this);
  - `{name}` in the text is replaced by the variable's value, and `{answer}` by the computed answer;
  - write 5-8 gen problems per quantitative lecture.

## Final report to the user
Keep it short and in plain language:
- what was added (the number of topics, figures, flashcards and quiz questions);
- any slide errors or ambiguities you found;
- anything you could not verify.
