"""Streamlit dashboard for the AI Performance and Profitability Optimizer."""

import os

import pandas as pd
import streamlit as st

from ai_api import generate_api_candidates
from monitoring import InfrastructureSnapshot, infrastructure_health, recommend_autoscaling, recommend_gpu_model
from optimizer import CurrentConfiguration, Requirements, optimize, simulated_candidates


st.set_page_config(
    page_title="AI Optimizer",
    page_icon="AI",
    layout="wide",
)

st.title("AI Performance and Profitability Optimizer")
st.caption("Compare AI configurations using simulated data or an OpenAI-compatible API.")

with st.sidebar:
    st.header("Your current system")
    cost_per_request = st.number_input("Cost per request ($)", min_value=0.0, value=0.008, step=0.001, format="%.4f")
    revenue_per_request = st.number_input("Revenue per request ($)", min_value=0.0001, value=0.025, step=0.001, format="%.4f")
    latency_ms = st.number_input("Latency (milliseconds)", min_value=1.0, value=320.0, step=10.0)
    quality_score = st.slider("Quality score", min_value=0.0, max_value=1.0, value=0.92, step=0.01)
    monthly_requests = st.number_input("Monthly requests", min_value=1, value=100000, step=10000)
    infrastructure_cost = st.number_input("Monthly infrastructure cost ($)", min_value=0.0, value=850.0, step=50.0)

    st.header("Simulated infrastructure monitoring")
    gpu_utilization = st.slider("GPU utilization", min_value=0, max_value=100, value=62, format="%d%%")
    cpu_utilization = st.slider("CPU utilization", min_value=0, max_value=100, value=48, format="%d%%")
    ram_utilization = st.slider("RAM utilization", min_value=0, max_value=100, value=58, format="%d%%")
    gpu_hourly_cost = st.number_input("GPU cost per hour ($)", min_value=0.0, value=1.20, step=0.05)
    active_replicas = st.number_input("Active replicas", min_value=1, value=2, step=1)
    requests_per_minute = st.number_input("Current requests per minute", min_value=1, value=70, step=10)
    peak_requests_per_minute = st.number_input("Peak requests per minute", min_value=1, value=140, step=10)

    st.header("Your requirements")
    minimum_quality = st.slider("Minimum acceptable quality", min_value=0.0, max_value=1.0, value=0.88, step=0.01)
    maximum_latency_ms = st.number_input("Maximum latency (milliseconds)", min_value=1.0, value=300.0, step=10.0)
    target_profit_margin = st.slider("Target profit margin", min_value=0.0, max_value=1.0, value=0.55, step=0.01)

    st.header("Candidate source")
    candidate_source = st.radio("How should alternatives be created?", ["Simulated data", "AI API"])
    api_candidates = None
    if candidate_source == "AI API":
        st.caption("The API creates estimates. Local code still calculates profit and filters requirements.")
        api_key = st.text_input(
            "API key",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password",
            help="Prefer setting OPENAI_API_KEY in your environment instead of entering it here.",
        )
        api_model = st.text_input("Model", value=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        api_base_url = st.text_input(
            "Base URL (optional)",
            value=os.getenv("OPENAI_BASE_URL", ""),
            help="Leave blank for OpenAI. Use this for another OpenAI-compatible provider.",
        )
        generate_clicked = st.button("Generate configurations with AI")
    else:
        api_key = ""
        api_model = ""
        api_base_url = ""
        generate_clicked = False

current = CurrentConfiguration(
    cost_per_request=cost_per_request,
    revenue_per_request=revenue_per_request,
    latency_ms=latency_ms,
    quality_score=quality_score,
    monthly_requests=monthly_requests,
    infrastructure_cost=infrastructure_cost,
)
requirements = Requirements(
    minimum_quality=minimum_quality,
    maximum_latency_ms=maximum_latency_ms,
    target_profit_margin=target_profit_margin,
)
infrastructure = InfrastructureSnapshot(
    gpu_utilization=gpu_utilization,
    cpu_utilization=cpu_utilization,
    ram_utilization=ram_utilization,
    gpu_hourly_cost=gpu_hourly_cost,
    active_replicas=active_replicas,
    requests_per_minute=requests_per_minute,
    peak_requests_per_minute=peak_requests_per_minute,
)
gpu_recommendation, gpu_explanation = recommend_gpu_model(infrastructure)
scaling_recommendation, scaling_explanation = recommend_autoscaling(infrastructure)

if candidate_source == "AI API":
    if generate_clicked:
        if not api_key:
            st.error("Enter an API key or set OPENAI_API_KEY before generating configurations.")
        else:
            try:
                api_candidates, api_metrics = generate_api_candidates(
                    current,
                    requirements,
                    api_key,
                    api_model,
                    api_base_url or None,
                )
                st.session_state["api_candidates"] = api_candidates
                st.session_state.setdefault("api_metrics_history", []).append(api_metrics)
                st.session_state["api_candidate_error"] = ""
            except Exception as error:
                st.session_state["api_candidate_error"] = str(error)
    api_candidates = st.session_state.get("api_candidates")
    api_error = st.session_state.get("api_candidate_error", "")
    if api_error:
        st.error(f"AI API error: {api_error}")
    if not api_candidates:
        st.info("Click 'Generate configurations with AI' to create candidate options. Showing simulated data until then.")
        candidates = simulated_candidates()
    else:
        candidates = api_candidates
else:
    candidates = simulated_candidates()

current_result, evaluations, recommendation = optimize(current, requirements, candidates)

api_metrics_history = st.session_state.get("api_metrics_history", [])

if recommendation is None:
    st.warning("No simulated configuration meets all three requirements. Try relaxing a threshold.")
else:
    st.success(f"Recommended configuration: {recommendation.name}")

st.subheader("At a glance")
metric_columns = st.columns(4)
metric_columns[0].metric("Current margin", f"{current_result.profit_margin:.1%}")
metric_columns[1].metric(
    "Recommended margin",
    f"{recommendation.profit_margin:.1%}" if recommendation else "-",
    f"{recommendation.profit_margin - current_result.profit_margin:+.1%}" if recommendation else None,
)
metric_columns[2].metric(
    "Estimated monthly savings",
    f"${current_result.monthly_total_cost - recommendation.monthly_total_cost:,.0f}" if recommendation else "-",
)
metric_columns[3].metric(
    "Latency change",
    f"{recommendation.latency_ms - current_result.latency_ms:+.0f} ms" if recommendation else "-",
)

if api_metrics_history:
    st.subheader("API usage")
    total_requests = len(api_metrics_history)
    total_tokens = sum(metrics.total_tokens for metrics in api_metrics_history)
    total_cost = sum(metrics.estimated_cost for metrics in api_metrics_history)
    average_latency = sum(metrics.latency_ms for metrics in api_metrics_history) / total_requests
    usage_columns = st.columns(4)
    usage_columns[0].metric("API requests", f"{total_requests:,}")
    usage_columns[1].metric("Tokens used", f"{total_tokens:,}")
    usage_columns[2].metric("Estimated API cost", f"${total_cost:.4f}")
    usage_columns[3].metric("Average response latency", f"{average_latency:,.0f} ms")

    usage_rows = [
        {
            "Request": index,
            "Model": metrics.model,
            "Latency": f"{metrics.latency_ms:,.0f} ms",
            "Prompt tokens": metrics.prompt_tokens,
            "Completion tokens": metrics.completion_tokens,
            "Total tokens": metrics.total_tokens,
            "Estimated cost": f"${metrics.estimated_cost:.4f}",
        }
        for index, metrics in enumerate(api_metrics_history, start=1)
    ]
    st.dataframe(pd.DataFrame(usage_rows), hide_index=True, width="stretch")

st.subheader("Infrastructure monitoring")
monitor_columns = st.columns(5)
monitor_columns[0].metric("Infrastructure health", infrastructure_health(infrastructure))
monitor_columns[1].metric("GPU utilization", f"{infrastructure.gpu_utilization:.0f}%")
monitor_columns[2].metric("CPU utilization", f"{infrastructure.cpu_utilization:.0f}%")
monitor_columns[3].metric("RAM utilization", f"{infrastructure.ram_utilization:.0f}%")
monitor_columns[4].metric("Estimated cloud cost", f"${infrastructure.monthly_cloud_cost:,.0f}/mo")

gpu_column, scaling_column = st.columns(2)
with gpu_column:
    st.subheader("GPU model recommendation")
    st.write(f"**{gpu_recommendation}**")
    st.caption(gpu_explanation)
    st.write(f"Current rate: **${infrastructure.gpu_hourly_cost:.2f}/GPU hour**")

with scaling_column:
    st.subheader("Autoscaling recommendation")
    st.write(f"**{scaling_recommendation}**")
    st.caption(scaling_explanation)
    st.write(
        f"Traffic: **{infrastructure.requests_per_minute:,} rpm now** / "
        f"**{infrastructure.peak_requests_per_minute:,} rpm peak**"
    )

left_column, right_column = st.columns(2)
with left_column:
    st.subheader("Current configuration")
    st.write(f"**Quality:** {current_result.quality_score:.0%}")
    st.write(f"**Latency:** {current_result.latency_ms:,.0f} ms")
    st.write(f"**Monthly revenue:** ${current_result.monthly_revenue:,.0f}")
    st.write(f"**Monthly total cost:** ${current_result.monthly_total_cost:,.0f}")
    st.write(f"**Monthly profit:** ${current_result.monthly_profit:,.0f}")

with right_column:
    st.subheader("Recommended configuration")
    if recommendation:
        st.write(f"**{recommendation.name}** - {recommendation.description}")
        st.write(f"**Recommended model switch:** `{recommendation.model_id}`")
        st.write(f"**Quality:** {recommendation.quality_score:.0%}")
        st.write(f"**Latency:** {recommendation.latency_ms:,.0f} ms")
        st.write(f"**Monthly profit:** ${recommendation.monthly_profit:,.0f}")
        st.write(f"**Profit-margin improvement:** {recommendation.profit_margin - current_result.profit_margin:+.1%}")
    else:
        st.write("No recommendation is available under the current requirements.")

st.subheader(f"{candidate_source} configurations")
st.caption("Eligible options are ranked by profit margin, then monthly savings and quality.")
rows = []
for evaluation in evaluations:
    rows.append(
        {
            "Configuration": evaluation.name,
            "Model ID": evaluation.model_id,
            "Rank": evaluations.index(evaluation) + 1,
            "Cost / request": f"${evaluation.cost_per_request:.4f}",
            "Monthly cost": f"${evaluation.monthly_total_cost:,.0f}",
            "Monthly savings": f"${evaluation.monthly_savings:,.0f}",
            "Annual savings": f"${evaluation.annual_savings:,.0f}",
            "Latency": f"{evaluation.latency_ms:,.0f} ms",
            "Latency change": f"{evaluation.latency_change_ms:+,.0f} ms",
            "Quality": f"{evaluation.quality_score:.0%}",
            "Quality change": f"{evaluation.quality_change:+.0%}",
            "Profit margin": f"{evaluation.profit_margin:.1%}",
            "Margin change": f"{evaluation.margin_change:+.1%}",
            "Meets requirements": "Yes" if evaluation.meets_requirements else "No",
        }
    )
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

with st.expander("How the recommendation works"):
    st.markdown(
        """
        1. **Revenue** = revenue per request x monthly requests.
        2. **Total cost** = (candidate cost per request x monthly requests) + infrastructure cost.
        3. **Profit margin** = (revenue - total cost) / revenue.
        4. A candidate is eligible only when its quality is high enough, latency is low enough, and margin reaches the target.
        5. Eligible candidates are ranked by profit margin, then monthly savings and quality score.
        6. The recommendation is the eligible model configuration with the highest estimated profit margin.

        Simulated mode uses fixed values in `optimizer.py`. AI API mode asks an OpenAI-compatible model for hypothetical alternatives, but the API does not calculate the recommendation: the local optimizer validates every candidate and performs all financial calculations.

        API usage is tracked per generation request: response latency, prompt tokens, completion tokens, total tokens, and an estimated request cost. The cost estimate uses the small pricing table in `ai_api.py` and should be updated when provider pricing changes.
        """
    )
