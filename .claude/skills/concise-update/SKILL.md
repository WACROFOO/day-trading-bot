---
name: concise-update
description: Reply format for this project. Every answer, progress report or research summary is short and structured as key findings, analysis, open points and next steps. Use it for every reply in this repository.
---

# Concise update

The owner wants short replies: the main findings, what they mean, what's
open, and what's next. Details belong in the repo docs, not in chat.

## Structure

Start with the answer or result in one or two sentences. Then use only the
sections that apply, in this order:

1. **Key findings:** at most 5 bullets, one line each.
2. **Analysis:** at most 3 bullets on what it means for the plan or the
   decision.
3. **Open points:** decisions needed from the owner, unverified items, risks.
4. **Next steps:** who does what, in at most 3 bullets.
5. **Files:** links to where the details live, at most 3.

## Rules

- **Length:** aim for 200 words or fewer; up to 350 for a major milestone.
- **One line per bullet.** Use sub-bullets only if they are essential.
- **Numbers** only when they change a decision.
- **Leave out:**
  - process narration (which agents ran, tool calls, commit messages);
  - restating context the owner already has;
  - long tables (link the file instead);
  - repeated caveats.
- **At most one question,** at the end, and only if work is blocked on it.
- **Never drop, however short the reply:**
  - failures and errors;
  - anything not verified;
  - risks to money, tax or privacy (one short line is enough).
