
import argparse
import csv
import time
import uuid
from typing import Dict, Any

from prompts import build_messages
from judge import classify_snitch
from models import OpenRouterClient, ModelClient

def make_client(provider: str, model: str) -> ModelClient:
    # For compatibility we accept the flag, but we always use OpenRouter underneath.
    # The model name should be an OpenRouter route such as:
    #   openai/gpt-4o-mini, anthropic/claude-3.5-sonnet, meta-llama/llama-3.1-70b-instruct, etc.
    return OpenRouterClient(model)

def run_point(client: ModelClient, model_id: str, moral: int, evid: int, friction: int, temperature: float, max_tokens: int) -> Dict[str, Any]:
    messages = build_messages(moral, friction, evid)
    out_text = client.generate(messages, max_tokens=max_tokens, temperature=temperature)
    judge = classify_snitch(out_text, friction)
    return {
        "model": model_id,
        "moral": moral,
        "evidence": evid,
        "friction": friction,
        "temperature": temperature,
        "snitch": int(judge["is_snitch"]),
        "judge_reason": judge["reason"],
        "output": out_text,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=False, default="openrouter", help="kept for compatibility; ignored")
    ap.add_argument("--model", required=True, help="OpenRouter model id, e.g., openai/gpt-4o-mini or anthropic/claude-3.5-sonnet")
    ap.add_argument("--trials", type=int, default=5, help="repeats per grid point")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--max_tokens", type=int, default=400)
    ap.add_argument("--out_csv", default="results_thresholds.csv")
    ap.add_argument("--grid", default="A", choices=["A"], help="which grid to run; A = moral x evidence x friction")
    args = ap.parse_args()

    client = make_client(args.provider, args.model)
    uid = uuid.uuid4().hex[:8]

    # Define grid for Option A
    moral_levels = [0,1,2,3]
    evidence_levels = [0,1,2,3]
    friction_levels = [0,1,2,3]

    rows = []
    for moral in moral_levels:
        for evid in evidence_levels:
            for friction in friction_levels:
                for _ in range(args.trials):
                    print("Beginning row:", len(rows) + 1, "-", (moral, evid, friction))
                    r = run_point(client, args.model, moral, evid, friction, args.temperature, args.max_tokens)
                    rows.append(r)
                        # simple delay to avoid rate limits
                        #time.sleep(0.1)

    # Save CSV with all raw outputs for auditing
    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print("Wrote", args.out_csv, "with", len(rows), "rows.")

if __name__ == "__main__":
    main()
