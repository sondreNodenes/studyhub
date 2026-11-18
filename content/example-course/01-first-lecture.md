# Lecture 1 - Example lecture
code: L1

## Highlights
- **One file per lecture.** Notes, flashcards and the quiz live in the same Markdown file.
- **Highlights** (this list) are the key ideas; each can link to the notes section it is about.

## Summary
## How a lecture file is built

**In plain words.** A lecture file has the sections Highlights, Summary (the notes, one `##` heading per topic), Explained, Flashcards and Quiz. `python3 build.py` turns every file into the app.

> **Key idea:** write the notes so that you could explain every heading out loud without looking.

- Put figures in `content/<course>/img/` and refer to them with `![caption](img/name.svg)`.
- Slides are optional: add a line `pdf: slides/Lec 01.pdf` under the title and put the PDF in `slides/`.

## Flashcards
Q: Where does a lecture's quiz live?
A: In the same Markdown file as the notes, under `## Quiz`.

Q: Which command rebuilds the app after you edit a file?
A: `python3 build.py`

## Quiz
? [mcq] Which heading starts the quiz of a lecture file?
- `## Flashcards`
* `## Quiz`
- `## Highlights`
- `## Summary`
> The quiz is everything after `## Quiz`.
