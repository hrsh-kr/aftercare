"""Phase 4 milestone: a plain view of every escalated ticket, with
full context - the smallest complete version of the brand side of
the story. Run after scripts/test_agent_multiturn.py has created some.
"""

from src.layer3b.tickets import Ticket


def main() -> None:
    tickets = Ticket.load_all()
    if not tickets:
        print("No tickets yet.")
        return

    for t in sorted(tickets, key=lambda t: t.ticket_id):
        print("=" * 60)
        print(f"{t.ticket_id}  [{t.status}]{'  SAFETY' if t.safety_flag else ''}")
        print(f"Customer: {t.customer_name} ({t.customer_phone})")
        print(f"Product:  {t.product_name}  (serial {t.serial_number})")
        print(f"Issue:    {t.issue_summary}")
        if t.attempts_tried:
            print("Already tried:")
            for i, step in enumerate(t.attempts_tried, 1):
                print(f"  {i}. {step}")
        else:
            print("Already tried: nothing -- escalated immediately")
        print(f"Created:  {t.created_at}")
    print("=" * 60)
    print(f"\n{len(tickets)} ticket(s) total.")


if __name__ == "__main__":
    main()
