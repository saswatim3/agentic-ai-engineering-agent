"""
Observability helpers for analyzing agent traces and evaluation results.

These functions consume the trace dicts produced by run_agent and the
results list produced by run_evaluation. They never call the model.
"""

from datetime import datetime


def summarize_trace(trace):
    events = trace.get("events", [])

    model_calls = [
        event for event in events
        if event.get("event_type") == "model_call"
    ]
    tool_calls = [
        event for event in events
        if event.get("event_type") == "tool_execution"
    ]
    judge_verdicts = [
        event for event in events
        if event.get("event_type") == "judge_verdict"
    ]
    retries = [
        event for event in events
        if event.get("event_type") == "retry"
    ]

    # Sum token usage across all model calls (agent + judge).
    input_tokens = 0
    output_tokens = 0
    calls_with_usage = 0

    for event in model_calls:
        usage = event.get("usage")
        if not usage:
            continue
        calls_with_usage += 1
        input_tokens += usage.get("input_tokens") or 0
        output_tokens += usage.get("output_tokens") or 0

    # Find the slowest model call or tool execution.
    operations = model_calls + tool_calls
    slowest_operation = max(
        operations,
        key=lambda event: event.get("duration_ms") or 0,
        default=None,
    )

    # End-to-end duration from trace timestamps.
    duration_ms = None
    finished_at = trace.get("finished_at")
    if trace.get("started_at") and finished_at:
        start = datetime.fromisoformat(trace["started_at"])
        end = datetime.fromisoformat(finished_at)
        duration_ms = round(
            (end - start).total_seconds() * 1000, 2
        )

    return {
        "trace_id": trace.get("trace_id"),
        "status": trace.get("status"),
        "duration_ms": duration_ms,
        "model_calls": len(model_calls),
        "tool_executions": len(tool_calls),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "calls_with_usage": calls_with_usage,
        "judge_verdicts": len(judge_verdicts),
        "judge_rejections": sum(
            event.get("correct") is False
            for event in judge_verdicts
        ),
        "retry_count": len(retries),
        "slowest_operation": (
            {
                "event_type": slowest_operation.get("event_type"),
                "stage": slowest_operation.get("stage"),
                "tool_name": slowest_operation.get("tool_name"),
                "duration_ms": slowest_operation.get("duration_ms"),
            }
            if slowest_operation else None
        ),
    }


def latency_by_stage(trace):
    summary = {}

    for event in trace.get("events", []):
        if event.get("event_type") != "model_call":
            continue

        stage = event.get("stage", "unknown")
        duration = event.get("duration_ms") or 0

        if stage not in summary:
            summary[stage] = {
                "calls": 0,
                "total_duration_ms": 0,
            }

        summary[stage]["calls"] += 1
        summary[stage]["total_duration_ms"] += duration

    for stats in summary.values():
        stats["total_duration_ms"] = round(
            stats["total_duration_ms"], 2
        )

    return summary


def calculate_observability_metrics(results):
    # Use only successfully completed requests with traces.
    completed = [
        item for item in results
        if item.get("status") == "completed"
        and item.get("trace")
    ]

    if not completed:
        return {"completed_requests": 0}

    traces = [item["trace"] for item in completed]

    def percentile(values, p):
        values = sorted(values)
        index = max(0, int((p / 100) * len(values) + 0.999999) - 1)
        return values[min(index, len(values) - 1)]

    latencies = [
        trace["metrics"]["duration_ms"]
        if trace.get("metrics", {}).get("duration_ms") is not None
        else next(
            (
                event["duration_ms"]
                for event in trace.get("events", [])
                if event.get("event_type") == "run_summary"
                and event.get("duration_ms") is not None
            ),
            None,
        )
        for trace in traces
    ]

    latencies = [value for value in latencies if value is not None]

    total_tokens = []
    model_call_counts = []
    retry_counts = []

    for trace in traces:
        events = trace.get("events", [])

        tokens = 0
        for event in events:
            if event.get("event_type") == "model_call":
                usage = event.get("usage") or {}
                tokens += usage.get("total_tokens") or 0

        total_tokens.append(tokens)

        model_call_counts.append(
            sum(
                event.get("event_type") == "model_call"
                for event in events
            )
        )

        retry_counts.append(
            trace.get("metrics", {}).get(
                "retry_count",
                sum(
                    event.get("event_type") == "retry"
                    for event in events
                ),
            )
        )

    return {
        "completed_requests": len(completed),
        "requests_with_recorded_latency": len(latencies),
        "average_latency_ms": (
            round(sum(latencies) / len(latencies), 2)
            if latencies else None
        ),
        "p95_latency_ms": (
            percentile(latencies, 95)
            if latencies else None
        ),
        "average_tokens_per_request": round(
            sum(total_tokens) / len(total_tokens), 2
        ),
        "average_model_calls_per_request": round(
            sum(model_call_counts) / len(model_call_counts), 2
        ),
        "average_retries_per_request": round(
            sum(retry_counts) / len(retry_counts), 2
        ),
        "retry_rate": round(
            sum(count > 0 for count in retry_counts)
            / len(retry_counts),
            4,
        ),
    }
