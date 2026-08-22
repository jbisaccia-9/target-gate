"""CLI:  python -m targetgate run [fixture|corrupted|nppes]
        python -m targetgate brief [scripted|hallucinating|foundry]"""
import sys
from .pipeline import run

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "brief":
        from .agent import run_agent, grounding_gate, get_model, previous_rows
        from .pull import pull_fixture
        rows = pull_fixture()
        brief, transcript = run_agent(get_model(args[1] if len(args) > 1 else "scripted"),
                                      rows, previous_rows())
        print(brief)
        print(f"[agent loop: {sum(1 for t in transcript if t.get('role') == 'tool')} tool calls]")
        sys.exit(grounding_gate(brief, rows, previous_rows()))
    source = args[1] if len(args) > 1 else (args[0] if args and args[0] != "run" else "fixture")
    sys.exit(run(source=source))
