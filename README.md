# AI Performance and Profitability Optimizer

A beginner-friendly Streamlit prototype for comparing AI configurations. It explores the trade-off between request cost, latency, quality, and business profit using simulated data or an optional OpenAI-compatible API.

Simulated mode is fully offline. Optional AI API mode asks a language model to suggest hypothetical configurations; it does not connect to billing or monitoring systems, and the local optimizer still performs the recommendation math.

## Run it

From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL printed by Streamlit.

## Enable AI API mode

The app supports OpenAI and other OpenAI-compatible providers. Set the key before starting Streamlit:

```powershell
$env:OPENAI_API_KEY = "your-key-here"
$env:OPENAI_MODEL = "gpt-4o-mini"
# Optional for a compatible provider:
# $env:OPENAI_BASE_URL = "https://example.com/v1"
streamlit run app.py
```

In the sidebar, choose **AI API**, review the model and optional base URL, then click **Generate configurations with AI**. The key is used only for the request and is not written to project files. Never commit API keys to source control.

## How the code is organized

- `optimizer.py` contains the calculations. Keeping this separate from the screen makes the business logic easier to test and reuse.
- `app.py` builds the Streamlit controls, passes the user's inputs into the optimizer, and displays the results.
- `ai_api.py` makes the optional API call and validates the model's JSON into candidate configurations.
- `monitoring.py` contains simulated GPU, CPU, RAM, cloud-cost, GPU-sizing, and autoscaling calculations.
- `requirements.txt` lists the two small dependencies.

## The calculation

For each configuration, the prototype estimates:

```text
monthly revenue = revenue per request * monthly requests
monthly total cost = (candidate cost per request * monthly requests) + infrastructure cost
monthly profit = monthly revenue - monthly total cost
profit margin = monthly profit / monthly revenue
```

A candidate is eligible only if all three conditions are true:

- quality score >= minimum acceptable quality
- latency <= maximum latency
- profit margin >= target profit margin

The recommendation is the eligible candidate with the highest estimated profit margin. If no candidate passes, the dashboard asks you to relax a requirement rather than silently recommending an unacceptable option.

The comparison table also shows each option's monthly and annual savings versus the current configuration, latency and quality changes, and profit-margin improvement. Eligible options are ranked by profit margin first, then savings and quality score as tie-breakers.

## API tracking and model switching

When AI API mode generates alternatives, the dashboard records each request's:

- response latency
- prompt, completion, and total tokens
- estimated API cost
- model used for the generation request

Each candidate also has a model ID. The recommendation identifies the model configuration to switch to, but only after the local optimizer confirms that it meets quality, latency, and profit-margin requirements. Token prices are approximate values in `ai_api.py`; update them for your provider and model.

## Infrastructure monitoring

The sidebar includes simulated infrastructure inputs. The dashboard estimates monthly cloud cost with:

```text
GPU hourly cost * active replicas * 24 hours * 30 days
```

It also gives simple recommendations:

- low GPU utilization suggests downsizing
- high GPU, CPU, or RAM utilization suggests adding capacity
- large peak traffic suggests metric-based or scheduled autoscaling

These readings are simulated. A production version would replace them with metrics from a cloud monitoring API.

## Beginner exercises

1. Add a new `CandidateConfiguration` in `simulated_candidates()`.
2. Add an estimated monthly cost or profit chart to the dashboard.
3. Add tests for `evaluate_configuration()` using small, hand-calculated numbers.
4. Replace the simulated candidates with data loaded from a CSV file.
5. Add a second API provider by passing its OpenAI-compatible base URL.

## Important limitation

The results are estimates, not production forecasts. Real systems may have variable traffic, cache hits, batch processing, tiered pricing, quality evaluation error, and other infrastructure costs.
