import random

def generate_mock_completion(messages: list[dict]) -> dict:
    """Simulates a model response — no real LLM is called. input_tokens is
    derived from actual message length (~4 chars/token, a common rough
    estimate) so it varies meaningfully with real input rather than being
    pure noise. output_tokens is randomized within a plausible range since
    there's nothing real to measure. cached_input_tokens and
    reasoning_tokens are 0 in M2 — CostCalculator already supports both
    for when that changes."""
    total_chars = sum(len(m.get("content", "")) for m in messages)
    input_tokens = max(1, total_chars // 4)
    output_tokens = random.randint(20, 300)
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": 0,
        "output_tokens": output_tokens,
        "reasoning_tokens": 0,
        "content": "This is a simulated NexusBill completion response.",
    }