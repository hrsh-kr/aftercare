"""How well does the model do the two jobs it is left with: (1) phrase one manual step, (2) read the
customer's reply. Everything else in Aftercare is code, so these two are the whole model surface.

    .venv/bin/python scripts/eval_model.py [model ...]      # default: the configured model

Prints accuracy and latency per model. A "phrasing" case passes if the message (a) contains the key
idea of the raw step, (b) is one short message with no emoji/quotes/greeting, (c) does not smuggle in
another step. A "reply" case passes if the RESOLVED / STILL_BROKEN read matches a human label.
"""
import re
import sys
import time

from src.agent import agent as A

# (raw step from a manual, words at least one of which must survive in the message)
PHRASING = [
    ("Check the machine is level. Rock it gently from each corner — if it rocks, adjust the feet until it doesn't.", ["level", "rock", "feet"]),
    ("Check the load is evenly spread. Pause the machine, open the door, and spread the clothes around the drum by hand so they're not bunched on one side", ["spread", "clothes", "bunched", "evenly"]),
    ("Clean the lint filter (Section 3) — remove it, rinse thoroughly under running water, and reinsert firmly.", ["filter", "rinse", "clean"]),
    ("Run a descaling cycle (Section 3) if the filter was already clean or the smell persists", ["descal"]),
    ("Turn off the AC. Remove and check both filters (Section 3). If visibly dusty, clean them per Section 3 and let them dry fully before reinstalling.", ["filter"]),
    ("Check the outdoor unit isn't blocked or enclosed.", ["outdoor", "blocked", "enclosed"]),
    ("Restart and give it 15-20 minutes at a normal set temperature (24-26°C) before judging cooling performance.", ["15", "minutes", "20"]),
    ("Check the drain pipe (the thin pipe running from the indoor to outdoor unit) isn't blocked", ["drain", "pipe"]),
]
COMPLAINTS = ["My washing machine bangs loudly when it spins", "AC not cooling the room", "clothes smell bad after washing", "water is dripping from my AC"]

# (step the customer was asked, their reply, expected)
REPLIES = [
    ("Level the machine", "That fixed it, thank you!", "RESOLVED"),
    ("Level the machine", "It worked, no more noise", "RESOLVED"),
    ("Clean the filter", "yes all good now", "RESOLVED"),
    ("Clean the filter", "smell is gone, thanks a lot", "RESOLVED"),
    ("Check the outdoor unit", "cooling properly now", "RESOLVED"),
    ("Restart the AC", "perfect, working fine", "RESOLVED"),
    ("Level the machine", "Still banging", "STILL_BROKEN"),
    ("Level the machine", "no change, same noise", "STILL_BROKEN"),
    ("Clean the filter", "did that, smell is still there", "STILL_BROKEN"),
    ("Check the outdoor unit", "still blowing warm air", "STILL_BROKEN"),
    ("Restart the AC", "nope", "STILL_BROKEN"),
    ("Restart the AC", "it didn't help", "STILL_BROKEN"),
    ("Level the machine", "it's a bit better but still shakes", "STILL_BROKEN"),
    ("Clean the filter", "ok I'll try now", "STILL_BROKEN"),
    ("Clean the filter", "how do I remove the filter?", "STILL_BROKEN"),
    ("Level the machine", "worked for a day and then it came back", "STILL_BROKEN"),
    ("Restart the AC", "Not working. Please send someone", "STILL_BROKEN"),
    ("Level the machine", "fixed! but the door squeaks now", "RESOLVED"),
]

EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿]")


def phrasing_ok(msg: str, keys: list[str]) -> tuple[bool, str]:
    low = msg.lower()
    if not any(k in low for k in keys):
        return False, "lost the key idea"
    if len(msg.split()) > 55:
        return False, "too long"
    if EMOJI.search(msg):
        return False, "emoji"
    if msg.startswith(('"', "'")):
        return False, "quoted"
    if re.match(r"^(hi|hello|hey|dear)\b", low):
        return False, "greeting"
    if msg.count("\n") > 1:
        return False, "multi-paragraph"
    return True, ""


def run(model: str) -> None:
    agent = A.StatelessAgent(model)
    ph_pass, ph_ms, fails = 0, [], []
    for raw, keys in PHRASING:
        complaint = COMPLAINTS[PHRASING.index((raw, keys)) % len(COMPLAINTS)]
        t = time.perf_counter()
        msg = A._tidy(str(agent(A.PHRASE_STEP_PROMPT.format(complaint=complaint, raw_step=raw))))
        ph_ms.append((time.perf_counter() - t) * 1000)
        ok, why = phrasing_ok(msg, keys)
        ph_pass += ok
        if not ok:
            fails.append(f"    phrasing [{why}]: {msg[:110]}")
    rp_pass, rp_ms = 0, []
    for step, reply, want in REPLIES:
        t = time.perf_counter()
        got = A.classify_reply(step, reply, agent)
        rp_ms.append((time.perf_counter() - t) * 1000)
        ok = got == want
        rp_pass += ok
        if not ok:
            fails.append(f"    reply {reply!r}: expected {want}, got {got}")
    print(f"{model:22} phrasing {ph_pass}/{len(PHRASING)} ({sum(ph_ms)/len(ph_ms):.0f} ms)   reply-reading {rp_pass}/{len(REPLIES)} ({sum(rp_ms)/len(rp_ms):.0f} ms)")
    for f in fails:
        print(f)


if __name__ == "__main__":
    for m in (sys.argv[1:] or [A.DEFAULT_MODEL]):
        run(m)
