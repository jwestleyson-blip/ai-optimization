"""Optional OpenAI-compatible API integration for candidate generation."""

import json
import time
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from optimizer import CandidateConfiguration, CurrentConfiguration, Requirements


SYSTEM_PROMPT = """You help optimize AI application configurations.
Return only valid JSON with this exact shape:
{
  "candidates": [
    {
      "model_id": "provider/model-name",
      "name": "short name",
      "description": "one sentence",
      "cost_per_request": 0.005,
      "latency_ms": 200,
      "quality_score": 0.92
    }
  ]
}
Return 4 to 6 hypothetical configurations. Keep cost_per_request non-negative,
latency_ms positive, and quality_score between 0 and 1. These are estimates only;
do not claim to access live cloud pricing or monitoring data."""


@dataclass
class APIRequestMetrics:
    """Usage and timing returned by one model-comparison request."""

    model: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float


# Approximate USD per 1M tokens. Update these values when pricing changes.
MODEL_PRICING = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def estimate_token_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate request cost from token usage and a small local price table."""

    input_price, output_price = MODEL_PRICING.get(model, (0.15, 0.60))
    return (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000


def generate_api_candidates(
    current: CurrentConfiguration,
    requirements: Requirements,
    api_key: str,
    model: str,
    base_url: str | None = None,
) -> tuple[list[CandidateConfiguration], APIRequestMetrics]:
    """Ask an OpenAI-compatible model for hypothetical alternatives."""

    client = OpenAI(api_key=api_key, base_url=base_url or None)
    prompt = {
        "current": {
            "cost_per_request": current.cost_per_request,
            "latency_ms": current.latency_ms,
            "quality_score": current.quality_score,
        },
        "requirements": {
            "minimum_quality": requirements.minimum_quality,
            "maximum_latency_ms": requirements.maximum_latency_ms,
            "target_profit_margin": requirements.target_profit_margin,
        },
    }
    started_at = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(prompt)},
        ],
    )
    latency_ms = (time.perf_counter() - started_at) * 1000

    content = response.choices[0].message.content
    if not content:
        raise ValueError("The AI API returned an empty response.")

    payload: Any = json.loads(content)
    raw_candidates = payload.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ValueError("The AI API response did not contain a candidates list.")

    candidates = []
    for item in raw_candidates:
        if not isinstance(item, dict):
            continue
        try:
            candidates.append(
                CandidateConfiguration(
                    name=str(item["name"]),
                    description=str(item["description"]),
                    cost_per_request=max(0.0, float(item["cost_per_request"])),
                    latency_ms=max(1.0, float(item["latency_ms"])),
                    quality_score=min(1.0, max(0.0, float(item["quality_score"]))),
                    model_id=str(item.get("model_id", item["name"])),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue

    if not candidates:
        raise ValueError("The AI API returned no usable configurations.")

    usage = response.usage
    prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
    completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) if usage else 0
    metrics = APIRequestMetrics(
        model=model,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimate_token_cost(model, prompt_tokens, completion_tokens),
    )
    return candidates, metrics
