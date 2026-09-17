# Groundtruth

### Verify the claim. Not the résumé.

---

## The problem

A genuine fresher spends a year building real projects. Actually learning. Actually understanding what they wrote, line by line, the hard way — by getting it wrong first and figuring out why. They apply for a junior role.

So does someone who was an SDE1 at a big tech company eighteen months ago. Laid off. Now applying to roles they'd never have looked at two years ago, because the market's bad and there simply aren't enough SDE1 and SDE2 openings for everyone who got let go this year.

On a resume, the second person almost always wins. More polish. A recognizable company name. A company looking at both sees someone who can ship from day one, and takes the safer bet. That looks like a good outcome. Sit with it for a second, and it isn't:

The genuine fresher — the one this role was actually built for — doesn't get a chance to start their career at all. Not because they weren't good enough. Because nobody could tell.

The company didn't hire a junior. They rented senior output at junior pay, and the role never trained anyone the way a junior role is supposed to. Next year, they'll have the exact same problem, because nothing about this hire grew into anything.

And it's not one company making one understandable call under pressure. Multiply it across the market and you get exactly what's already happening: entry-level job postings up 47% over the last few years, while actual entry-level *hiring* in those same postings is down 73%. The junior pipeline isn't shrinking by accident. It's quietly being replaced by cheap, short-term senior labor, one reasonable-looking hiring decision at a time.

There's a second way this goes wrong, and it's just as expensive. A company hires a fresher who looks great on paper and leans on AI for everything underneath — no real judgment yet, nothing to fall back on. For a while, that's invisible. AI tools are free, handed out by the company itself, and the tickets still close. But they never build the skill to work without it. The day AI gets better at exactly the tasks they were coasting on — and it will — they're the first to go. Not because they were lazy. Because nobody ever made them prove they could do it without help.

Both failures land in the same place: no new senior engineer gets made, either way. That part isn't optional or fixable later — it takes five to nine years to grow one, and there's no shortcut, no matter how good the models get. This isn't a someday problem. Junior hiring at large tech companies has already fallen from roughly a third of all hires to under a tenth, in just a few years.

To be clear, this isn't about keeping experienced people out of junior roles. That's not fair to them, and it's not actually the problem. The real problem, underneath both failures, is simpler and worse: **right now, nobody can tell a genuinely good candidate from one who just looks good on paper** — whether the polish is real experience or a well-prompted AI. Not the résumé. Not the interviewer, most of the time. By the time anyone even gets to an interview, a thousand near-identical applications have already been cut down to twenty, on the strength of a document that stopped meaning anything the day everyone learned to optimize it the same way.

## Why the usual fixes don't reach far enough

Companies have started adding live repo-based debugging rounds, AI-assisted assessments, extra interview stages. Some of this works. Stripe runs five or six live rounds against a real shared repo, with an actual engineer watching — and for Stripe, it works well. But it doesn't scale past a handful of senior engineers' time for a handful of hires a year. Most companies hiring at real volume don't have that luxury, so they fall back to keyword-matching resumes and hoping for the best.

Here's the part that matters: every one of these fixes happens *after* the pile of a thousand applications has already been cut down to twenty. Whatever damage was going to happen — the genuine candidate filtered out, the hollow one let through — already happened before any of these tools ever see the candidate. A better final round doesn't undo a broken first cut.

## What we're building

**Groundtruth checks whether a resume's claims are actually true, before anyone reaches the interview stage.**

Give it a resume and a linked GitHub profile. It doesn't just check that the link works — it reads the real repository: when it was actually created, who really wrote what, how the contribution history looks over time. Then it checks that against the claim. Built a real-time chat app with Redis? It checks the code actually uses Redis. Checks whether this person wrote most of it, or forked someone else's work and barely touched it. Checks whether the commit timeline plausibly matches "built over a semester" or looks more like "uploaded the night before applying."

The output isn't a pass/fail stamp. It's a short, specific, evidence-backed report — what checks out, what doesn't, and pointed questions grounded in that specific candidate's specific commits, ready for whoever runs the next round, instead of the same generic "tell me about yourself" every candidate gets regardless of what they actually built.

It's a verifier, not a gatekeeper. It never scores someone down for a small GitHub — not everyone had the time, or even knew a public portfolio would be scrutinized this closely, and penalizing that would just recreate the exact unfairness this is meant to fix. It only checks whether what's claimed is actually true.

And it doesn't stop at reading. Once the evidence is gathered, Groundtruth has a short, real, written conversation with the candidate about their own repo — a question grounded in one specific part of the code, a follow-up shaped by how they actually answered, drilling deeper wherever the answer was thin. No camera, no timer, just writing, back and forth. Someone who genuinely built the thing can talk about it, in their own words, from any angle you approach it. Someone who didn't, can't — no matter how good the repo looks sitting there on paper.

## Why both sides want this

A genuine candidate finally has something that works *for* them instead of against them: real, specific proof that what they built is really theirs. Instead of quietly losing to a more polished stranger every single time, they get evaluated on the one thing they actually have.

A good company gets a way to see through the pile at the volume they actually operate at — not five interviews a year like Stripe, but thousands — without pretending a keyword match ever meant anything. And every interview that follows starts from real, specific evidence, instead of a recruiter's best guess and a blank "walk me through your resume."

## Where this goes next

A company doesn't just get one candidate's report and move on. It gets a ranked view across every applicant for one role, an evidence-backed briefing for whoever runs the next interview, and — once that interview happens — a single decision record combining our evidence with what was actually said in the room. The whole hiring decision, defensible end to end, instead of a gut call on a document that stopped meaning anything.

We're building the verification and conversation layer first, because it's the piece that doesn't exist anywhere yet — and it's the piece everything downstream, the interview, the hiring decision, a fast-track selection into a company like Amazon, has to be able to trust before any of the rest of it means anything at all.
