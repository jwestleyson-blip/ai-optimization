"""Simulated infrastructure monitoring and scaling recommendations."""

from dataclasses import dataclass


@dataclass
class InfrastructureSnapshot:
    """Current simulated infrastructure measurements."""

    gpu_utilization: float
    cpu_utilization: float
    ram_utilization: float
    gpu_hourly_cost: float
    active_replicas: int
    requests_per_minute: int
    peak_requests_per_minute: int

    @property
    def monthly_cloud_cost(self) -> float:
        """Estimate 30-day GPU cost from the current replica count."""

        return self.gpu_hourly_cost * self.active_replicas * 24 * 30

    @property
    def peak_load_ratio(self) -> float:
        """Compare peak traffic with the current observed traffic."""

        if self.requests_per_minute <= 0:
            return 1.0
        return self.peak_requests_per_minute / self.requests_per_minute


def recommend_gpu_model(snapshot: InfrastructureSnapshot) -> tuple[str, str]:
    """Recommend a simulated GPU direction from utilization and cost pressure."""

    if snapshot.gpu_utilization < 35:
        return (
            "Downsize GPU",
            "GPU utilization is low. A smaller GPU or CPU-only option could reduce idle cost.",
        )
    if snapshot.gpu_utilization > 85:
        return (
            "Upgrade GPU or add replicas",
            "GPU utilization is high. More capacity may reduce queueing and latency risk.",
        )
    return (
        "Keep current GPU",
        "GPU utilization is in a balanced range. Review cost and latency before switching.",
    )


def recommend_autoscaling(snapshot: InfrastructureSnapshot) -> tuple[str, str]:
    """Recommend a simple scaling policy from utilization and traffic headroom."""

    if snapshot.gpu_utilization > 80 or snapshot.cpu_utilization > 80 or snapshot.ram_utilization > 85:
        return (
            "Scale out now",
            "At least one resource is near saturation. Add replicas before capacity becomes a bottleneck.",
        )
    if snapshot.peak_load_ratio >= 1.5:
        return (
            "Use scheduled or metric-based autoscaling",
            "Peak traffic is much higher than current traffic. Scale up for peaks and back down afterward.",
        )
    return (
        "Keep a small autoscaling buffer",
        "Current load has headroom. Keep one warm replica and scale when utilization rises.",
    )


def infrastructure_health(snapshot: InfrastructureSnapshot) -> str:
    """Return a simple status for the simulated resource readings."""

    if max(snapshot.gpu_utilization, snapshot.cpu_utilization, snapshot.ram_utilization) >= 90:
        return "At risk"
    if max(snapshot.gpu_utilization, snapshot.cpu_utilization, snapshot.ram_utilization) >= 75:
        return "Watch closely"
    return "Healthy"
