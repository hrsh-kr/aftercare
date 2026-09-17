"""The de-risking test from DESIGN.md / SKILL.md.

Question: can our actual local model tell a genuine, specific
explanation of a real commit apart from a generic, vague one?
If this doesn't work, nothing built on top of M.1 matters yet.

Uses a real commit already in this repo (24125672), not a synthetic
example — the same commit that added src/layer1/structural_checks.py.
"""

import subprocess

from strands import Agent
from strands.models.ollama import OllamaModel

COMMIT_SHA = "24125672e01374bfd2fb9767b571c8232eb741c5"

GENUINE_ANSWER = (
    "This adds two functions for analyzing a candidate's commit history "
    "before a model ever sees it. authorship_share sums up how many lines "
    "each commit changed and divides the claimed author's share by the "
    "total -- it returns 0.0 instead of raising when there are no commits "
    "at all, since an empty history should read as 'not enough evidence,' "
    "not crash the pipeline. timeline_shape looks at whether commits are "
    "spread out evenly over time, using the standard deviation of the gaps "
    "between commits versus their average, or dominated by one huge commit "
    "-- if the single largest commit accounts for more than 80% of all "
    "changed lines, it's classified as 'bulk' regardless of the gap "
    "pattern, since that's the stronger signal. It needs at least 4 "
    "commits with a fairly even spread to call something 'iterative' -- "
    "fewer than that and there isn't enough history to say anything "
    "meaningful, so it returns 'insufficient' instead of guessing."
)

GENERIC_ANSWER = (
    "This is a utility file with some helper functions for checking "
    "commits. It looks at the commit data and returns some information "
    "about the author and the timing of commits. The functions take in a "
    "list and process it to give useful output that can be used elsewhere "
    "in the system. It handles edge cases appropriately and follows good "
    "coding practices."
)

SCORE_PROMPT = """You are reviewing whether a candidate genuinely understands \
a piece of code they claim to have written, or is giving a generic, vague \
answer that could apply to almost any code change.

Here is the actual commit diff:

{diff}

Here is the candidate's explanation of what they built and why:

{answer}

Score this explanation from 1 to 5 for genuine, specific understanding of \
THIS code (not just plausible-sounding writing). A 5 references specific \
details from the diff -- actual thresholds, actual function names, actual \
decisions and why they were made. A 1 is generic enough that it could \
describe almost any code change without having read this one.

Respond with only the number, nothing else."""


def get_diff(sha: str) -> str:
    return subprocess.run(
        ["git", "show", sha],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def score(agent: Agent, diff: str, answer: str) -> str:
    prompt = SCORE_PROMPT.format(diff=diff, answer=answer)
    result = agent(prompt)
    return str(result).strip()


def main() -> None:
    diff = get_diff(COMMIT_SHA)

    model = OllamaModel(host="http://localhost:11434", model_id="qwen2.5-coder:7b")
    agent = Agent(model=model)

    genuine_score = score(agent, diff, GENUINE_ANSWER)
    generic_score = score(agent, diff, GENERIC_ANSWER)

    print(f"Genuine answer scored: {genuine_score}")
    print(f"Generic answer scored: {generic_score}")

    try:
        passed = float(genuine_score) > float(generic_score)
    except ValueError:
        passed = False
        print("Could not parse one of the scores as a number -- see raw output above.")

    print("PASS -- model tells genuine from generic" if passed else "FAIL -- model did not separate them")


if __name__ == "__main__":
    main()
