"""Phase 3 test: the actual multi-turn loop, through src/layer2/agent.py
end to end -- not just direct model calls like Phase 1's script.

Three paths, per IMPLEMENTATION.md:
1. Resolved on the first step
2. Still broken after step 1, offered a genuinely different step 2, resolved
3. Still broken after both attempts -> escalates with a real ticket
   containing what was actually tried
4. Safety-flagged from the start -> immediate ticket, no steps offered
"""

from src.layer1.registration import load_registrations
from src.layer2 import agent as agent_mod


def print_conversation(conv) -> None:
    for t in conv.turns:
        print(f"  [attempt {t.attempt_number}] STEP: {t.step}")
        if t.customer_reply:
            print(f"  [attempt {t.attempt_number}] CUSTOMER: {t.customer_reply} -> {t.outcome}")
    if conv.resolved:
        print("  RESULT: resolved, no ticket")
    elif conv.ticket:
        print(f"  RESULT: escalated -> {conv.ticket.ticket_id}")
        print(f"    issue: {conv.ticket.issue_summary}")
        print(f"    attempts tried: {conv.ticket.attempts_tried}")


def main() -> None:
    regs = {r.customer_phone: r for r in load_registrations()}
    a = agent_mod._build_agent()

    print("=" * 60)
    print("PATH 1 -- resolved on first step (washing machine drum noise)")
    print("=" * 60)
    priya = regs["+919876543210"]
    conv = agent_mod.start(priya, "My washing machine drum is banging loudly when it spins", agent=a)
    conv = agent_mod.respond(conv, "I checked and it was rocking, I adjusted the feet and it's quiet now, thank you!", agent=a)
    print_conversation(conv)

    print()
    print("=" * 60)
    print("PATH 2 -- still broken after step 1, step 2 offered and resolves (AC)")
    print("=" * 60)
    ravi = regs["+919812345678"]
    conv = agent_mod.start(ravi, "My AC isn't cooling the room at all anymore", agent=a)
    conv = agent_mod.respond(conv, "I cleaned the filters like you said but it's still not cooling", agent=a)
    print_conversation(conv)
    if not conv.resolved and conv.ticket is None:
        conv = agent_mod.respond(conv, "Okay I checked the outdoor unit, it was actually blocked by some boxes, moved them and it's cooling fine now", agent=a)
        print_conversation(conv)

    print()
    print("=" * 60)
    print("PATH 3 -- still broken after both attempts -> escalates (washing machine)")
    print("=" * 60)
    ananya = regs["+919845098450"]
    conv = agent_mod.start(ananya, "My clothes still smell bad after every wash", agent=a)
    conv = agent_mod.respond(conv, "I cleaned the lint filter but the smell is still there", agent=a)
    print_conversation(conv)
    if not conv.resolved and conv.ticket is None:
        conv = agent_mod.respond(conv, "I ran a descaling cycle too and it's still smelly", agent=a)
        print_conversation(conv)

    print()
    print("=" * 60)
    print("PATH 4 -- safety flag, immediate ticket, no steps")
    print("=" * 60)
    sameer = regs["+919900112233"]
    conv = agent_mod.start(sameer, "There's a burning smell coming from my AC unit", agent=a)
    print_conversation(conv)


if __name__ == "__main__":
    main()
