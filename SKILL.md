# Skill Doc — How We Work

The shared reference for how we design, write, and code everything in this folder. Read before writing anything, not after.

## The one-line version

Simple, clear, and precise beats impressive-looking, every time. But "simple" is not the same as "short" — see below.

## Which voice for which job

Four different disciplines, not one house style stretched over everything:

- **Selling the pain, the problem, the why-you-should-care** (`PITCH.md`'s problem section, landing page copy) — **Hormozi.** Let it breathe. Build tension. Repeat for emphasis. Make the reader feel it's their problem, not just read a description of it.
- **Deciding what to build, what to cut, what's actually differentiated** — **Paul Graham.** Clear, a little contrarian, allergic to vague reasoning. This governs choices, not prose style.
- **Designing and coding anything we ship** — **Apple.** Restraint, clarity, one hierarchy at a time. Covers both the product screens and the landing page — see below, they're not the same mode.
- **The technical build itself** — the two of us, together, as detailed as the problem needs.

Getting these mixed up is the actual mistake to watch for — not using the wrong words, but using the *terse* register somewhere that needed to breathe, or the *expansive* register somewhere that needed to be cut to one sentence.

---

## How we design

We're competing for Best UI as well as the main track, so this section isn't decoration — it's scored on its own. Two different surfaces, two different modes, both still Apple, but not the same Apple.

**Product screens** — the dashboard, the ranked view, the conversation UI. Apple's utility mode:
- One clear hierarchy per screen. One primary thing to look at or do. If three things compete for attention, cut two.
- Type: one typeface, a small restrained scale, generous line-height. Legibility over personality.
- Spacing: one consistent scale (multiples of 4 or 8px), generous whitespace. Cramped is never "efficient" — it's just cramped.
- Color: mostly neutral, one accent, used sparingly and only to mean something — the primary action, a status. Never decoration.
- Motion: only to clarify a state change — a result appearing, a step completing. Fast, subtle, never for its own sake.

**The landing page** — a different job, so a different mode. This is Apple's *marketing* register, not their utility one: apple.com is not a restrained dashboard, it's an immersive, narrative experience — big type for the hero line, real pacing as you scroll, color and imagery used richly, motion used to build a feeling, not just to confirm a click landed.
- One big, bold claim as the hero — the tagline itself ("The support line that already knows what you bought."), not a feature list.
- The page follows `PITCH.md`'s actual narrative arc as you scroll — problem, then the reveal, then proof, then the close. The landing page *is* the pitch, designed.
- Typography can be large and expressive for hero moments — still one typeface, still considered, just not the restrained utility scale.
- Richer color and real imagery are fair game here — a real screenshot, a real moment from the product — as long as the accent color stays consistent with the product itself, so the two feel like one thing.
- Motion here is allowed to do more: a scroll-triggered reveal, a number counting up, something that builds emotional pace — still purposeful, just serving a different purpose than in the product.

Same taste, two different jobs. Don't bring the dashboard's restraint to the landing page, and don't bring the landing page's drama into the dashboard.

**One theme, chosen per chapter — no toggle.** Balance comes from composition, as on Apple's product pages: full-bleed chapters alternate black, light grey and white, one idea each, with calm type (weight 600–700, tight tracking), generous padding and restrained pill buttons. Define colours as tokens, keep the accent gradient consistent, respect `prefers-reduced-motion`. (A dark/light toggle was built and then dropped; see `archive/landing-v1/`.)

## How we write

For explanation — docs, architecture, anything answering "what is this and how does it work" — closer to how YC evaluates a pitch than to how a spec usually gets written. This does not apply to pain-selling copy — see "which voice for which job" above; that stays Hormozi, on purpose, and shouldn't be cut to the bone:

- **State the problem in one sentence, naming who it affects.** Not a category ("students"), a person. If the sentence needs a category, it isn't sharp enough yet.
- **Cut until only the essential remains.** A small point made clearly beats five points made vaguely. If a paragraph can lose a sentence without losing meaning, lose it.
- **Show, don't just claim.** A rule that also governs the demo video: a feature that exists only in the writeup is not a feature. If a doc asserts something works, it should point at where that's proven, not just say so.
- **Concrete over abstract.** A specific commit, a specific number, a specific person beats "many," "various," or "robust."
- **No filler.** No sentence that only restates its own heading. No adjective doing the work a fact should be doing.

## How we code

Mostly how good engineering already works, stated so it doesn't drift under deadline pressure:

- Clarity over cleverness. Small functions, names that say what they do.
- No abstraction for problems we don't have yet. Solve what the current layer actually needs, not a hypothetical future version.
- A dependency has to earn its place. Fewer moving parts, fewer things that can break live.
- Formatting is a tool's job, not a debate.
- Comments explain a non-obvious *why* — a workaround, a constraint. Never restate *what* the code already says.

---

## How we're building this

Paul Graham's order, and it's the right one for four days with no head start:

1. **Build the smallest version that works, before touching any infrastructure.** Prove the one uncertain thing — can our actual local model ground a suggestion in a real manual passage and correctly recognize when to escalate instead of guess — with a plain script against a real (authored) product manual. If this doesn't work well, nothing downstream matters yet.
2. **Then integrate the AWS toolkit**, one piece at a time, in the build order set out in `DESIGN.md`. We're on Build It — Strands and a local model — so "integrating AWS" means wiring these in locally, not deploying to a billed account.
3. **Iterate outward from a working core.** Never sideways into something new before the current layer is solid.

Don't design ahead of what's proven. Don't build ahead of what's designed.

## Who's actually reading this

Two different readers, and they need different things — not opposite things:

- **The automated first pass** needs explicit, unambiguous statements: the problem in one sentence, AWS services named plainly, what's real versus stretch marked clearly, what was learned stated out loud.
- **A human judge** needs the craft to hold up: clean architecture, restraint in the UI, a demo that shows the real mechanism working, not a claim that it does.

These don't conflict. Something genuinely good, described plainly, satisfies both. Optimizing for an AI grader's keywords at the expense of real quality is the trap — it can cost the human pass to chase the automated one.

## Common sense over the framework

The four voices above are tools for sharper judgment, not a replacement for it. If following one of them literally produces something that's obviously off — a doc that's technically terse but reads badly, a rule applied so mechanically it creates an inconsistency nobody would actually want — that's a bug, not a feature. Notice it and say so, either of us, whenever it happens. Don't get far enough into applying a framework that a plain error sitting in front of us stops being visible.

## Keeping the docs honest

After each build milestone in `DESIGN.md`'s build order, check: does `README.md` still describe what's actually built? Does `TECHNICAL.md` still match the real architecture, not the planned one? Has the story in `PITCH.md` drifted from what's true? Fix what's stale before the next milestone, not all at once at the end.

## The doc set

- **`CONTEXT.md`** — handoff: who/what/why, hackathon rules, current state, audit findings, working agreements. Read first in a new session.
- **`TARGET.md`** — what to do next and why: prioritized plan (Build It + Best UI, fast-track goal), simplify/add/subtract notes, definition of done.
- **`PITCH.md`** — why this, why now. The story.
- **`DESIGN.md`** — what we're building, layer by layer, and what we're deliberately not.
- **`TECHNICAL.md`** — how, concretely: the pipeline, the data, what's real versus mocked.
- **`FLOW.md`** — how it actually works, as built: request-by-request, file-by-file. Written from a full audit of the real code, not the plan — where `TECHNICAL.md` drifts from reality, `FLOW.md` is the one to trust.
- **`USER_GUIDE.md`** — install it, run it, click through it. For a person using the demo, not a person reading the code.
- **`README.md`** — the front door.
- **`SKILL.md`** — this file.
- **`IMPLEMENTATION.md`** — the live task checklist. Update it immediately after finishing each task, not in a batch — this is the file that lets a different session or model pick up cold.
- **`source/aftercare/`** — the original product spec this build is based on. Reference only, not maintained during the build.
- **`archive/groundtruth/`** — our first hackathon build, set aside when we pivoted. Not discarded, not part of this submission.
