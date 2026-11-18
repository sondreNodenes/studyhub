# StudyHub (engine)

Notes, flashcards and exam-style quizzes with a guided **Highlights -> Study -> Recall -> Test** flow, spaced repetition, weak spots and a timed exam simulation. This repo is only the **engine**; your courses live in a separate folder, so you can keep them private and still share the engine.

## Quick start
```
git clone <this repo> studyhub
cd studyhub
python3 serve.py            # http://localhost:8000 - the bundled example course
```
Double-click `Start StudyHub.command` on macOS. Progress is saved to `iCloud Drive/StudyHub/` (or `~/StudyHub-progress/`) by `serve.py`; set `STUDYHUB_DATA` to use another folder.

## Your own courses
A *content folder* looks like this (everything but `content/` is optional):
```
my-courses/
  content/<course-id>/course.md        course name, id, colour, "how the professor tests"
  content/<course-id>/01-topic.md      one file per lecture: Highlights, Summary, Explained, Flashcards, Quiz
  content/<course-id>/img/             figures (svg/png)
  slides/                              lecture PDFs, referenced as `pdf: slides/Lec 01.pdf`
  materials/                           anything else you want linked/served
```
See `content/example-course/` for the smallest working example. Then, from the engine folder:
```
python3 build.py --content ~/my-courses     # writes data.js + StudyHub-standalone.html into my-courses/
python3 serve.py --content ~/my-courses     # or: export STUDYHUB_CONTENT=~/my-courses
```
Files in the content folder win over the engine's, so `data.js`, `slides/` and `materials/` come from your courses while `index.html` comes from the engine.

`StudyHub-standalone.html` is one self-contained file: send it to a friend and they can open it with a double-click, no Python needed.

### Convenience wrappers
Copy `_engine.py`-style wrappers into the content folder (see the course repo) so `python3 build.py` / `python3 serve.py` work from there; they look for the engine in `../studyhub` or `$STUDYHUB_ENGINE`.

## Optional
- `pdftotext` (`brew install poppler`) adds "slide N" links next to the notes and makes the slides searchable.
- `engine/nb2pdf.py` turns a notebook slideshow into a PDF (needs Google Chrome).
- `.claude/skills/lecture-notes` is a Claude Code skill that turns slides into a complete lecture file.
- The lecture file format: see `content/example-course/01-first-lecture.md`.
