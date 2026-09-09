"""Core calculations for the simulated AI performance optimizer."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CurrentConfiguration:
    """The user's current production configuration and business inputs."""

    cost_per_request: float
    revenue_per_request: float
    latency_ms: float
    quality_score: float
    monthly_requests: int
    infrastructure_cost: float


@dataclass
class Requirements:
    """Performance and profitability limits a candidate must satisfy."""

    minimum_quality: float
    maximum_latency_ms: float
    target_profit_margin: float


@dataclass
class CandidateConfiguration:
    """A simulated alternative configuration."""

    name: str
    description: str
    cost_per_request: float
    latency_ms: float
    quality_score: float
    model_id: str = ""


@dataclass
class Evaluation:
    """Calculated business metrics for one configuration."""

    name: str
    description: str
    cost_per_request: float
    latency_ms: float
    quality_score: float
    monthly_revenue: float
    monthly_total_cost: float
    monthly_profit: float
    profit_margin: float
    meets_requirements: bool
    cost_savings_per_request: float
    monthly_savings: float
    annual_savings: float
    latency_change_ms: float
    quality_change: float
    margin_change: float
    model_id: str


def evaluate_configuration(
    name: str,
    description: str,
    cost_per_request: float,
    latency_ms: float,
    quality_score: float,
    current: CurrentConfiguration,
    requirements: Requirements,
    model_id: str = "",
) -> Evaluation:
    """Calculate monthly economics and requirement status for one option."""

    monthly_revenue = current.revenue_per_request * current.monthly_requests
    monthly_inference_cost = cost_per_request * current.monthly_requests
    monthly_total_cost = monthly_inference_cost + current.infrastructure_cost
    monthly_profit = monthly_revenue - monthly_total_cost
    profit_margin = monthly_profit / monthly_revenue if monthly_revenue else 0.0
    current_monthly_total_cost = (
        current.cost_per_request * current.monthly_requests + current.infrastructure_cost
    )
    current_profit_margin = (
        monthly_revenue - current_monthly_total_cost
    ) / monthly_revenue if monthly_revenue else 0.0

    meets_requirements = (
        quality_score >= requirements.minimum_quality
        and latency_ms <= requirements.maximum_latency_ms
        and profit_margin >= requirements.target_profit_margin
    )

    return Evaluation(
        name=name,
        description=description,
        cost_per_request=cost_per_request,
        latency_ms=latency_ms,
        quality_score=quality_score,
        monthly_revenue=monthly_revenue,
        monthly_total_cost=monthly_total_cost,
        monthly_profit=monthly_profit,
        profit_margin=profit_margin,
        meets_requirements=meets_requirements,
        cost_savings_per_request=current.cost_per_request - cost_per_request,
        monthly_savings=current_monthly_total_cost - monthly_total_cost,
        annual_savings=(current_monthly_total_cost - monthly_total_cost) * 12,
        latency_change_ms=latency_ms - current.latency_ms,
        quality_change=quality_score - current.quality_score,
        margin_change=profit_margin - current_profit_margin,
        model_id=model_id,
    )


def optimize(
    current: CurrentConfiguration,
    requirements: Requirements,
    candidates: list[CandidateConfiguration],
) -> tuple[Evaluation, list[Evaluation], Optional[Evaluation]]:
    """Evaluate every candidate and select the highest-margin eligible option."""

    current_evaluation = evaluate_configuration(
        name="Current configuration",
        description="Your existing AI system",
        cost_per_request=current.cost_per_request,
        latency_ms=current.latency_ms,
        quality_score=current.quality_score,
        current=current,
        requirements=requirements,
    )

    evaluations = [
        evaluate_configuration(
            name=candidate.name,
            description=candidate.description,
            cost_per_request=candidate.cost_per_request,
            latency_ms=candidate.latency_ms,
            quality_score=candidate.quality_score,
            current=current,
            requirements=requirements,
            model_id=candidate.model_id,
        )
        for candidate in candidates
    ]
    eligible = [evaluation for evaluation in evaluations if evaluation.meets_requirements]
    # Margin is the primary goal; savings and quality break ties between options.
    evaluations.sort(
        key=lambda evaluation: (
            evaluation.meets_requirements,
            evaluation.profit_margin,
            evaluation.monthly_savings,
            evaluation.quality_score,
        ),
        reverse=True,
    )
    recommendation = max(
        eligible,
        key=lambda evaluation: (
            evaluation.profit_margin,
            evaluation.monthly_savings,
            evaluation.quality_score,
        ),
        default=None,
    )

    return current_evaluation, evaluations, recommendation


def simulated_candidates() -> list[CandidateConfiguration]:
    """Return alternatives used by this first, cloud-free prototype."""

    return [
        CandidateConfiguration(
            name="Efficient Small Model",
            description="Lower cost and latency, with a modest quality trade-off",
            cost_per_request=0.0025,
            latency_ms=180,
            quality_score=0.87,
                    model_id="simulated-small-model",
        ),
        CandidateConfiguration(
            name="Balanced Model",
            description="A middle ground for quality, speed, and cost",
            cost_per_request=0.006,
            latency_ms=260,
            quality_score=0.93,
                    model_id="simulated-balanced-model",
        ),
        CandidateConfiguration(
            name="Quality-First Model",
            description="Highest quality, but slower and more expensive",
            cost_per_request=0.012,
            latency_ms=430,
            quality_score=0.98,
                    model_id="simulated-quality-model",
        ),
        CandidateConfiguration(
            name="Fast Specialized Model",
            description="Very responsive for focused tasks",
            cost_per_request=0.0025,
            latency_ms=120,
            quality_score=0.90,
                    model_id="simulated-fast-model",
        ),
    ]
