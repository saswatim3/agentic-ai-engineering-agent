import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from tool_calling import run_agent
from observability import calculate_observability_metrics

test = [ {
        "id": "orion_status",
        "input": "What is Orion's status?",
        "expected": {
            "Orion": {
                "status": "Delayed",
                "reason": "Database migration is behind schedule",
                "owner": "Engineering",
            }
        },
    },]


evaluation_cases = [
    {
        "id": "apollo_status",
        "input": "What is Apollo's status?",
        "expected": {
            "Apollo": {
                "status": "Delayed",
                "reason": "Database migration is behind schedule",
                "owner": "Engineering",
            }
        },
    },
    {
        "id": "all_projects",
        "input": "List all projects and their statuses.",
        "expected": {
            "Apollo": {"status": "Delayed"},
            "Mercury": {"status": "On Track"},
        },
    },
    {
        "id": "unknown_project",
        "input": "What is Orion's status?",
        "expected": {
            "Orion": {
                "status": "Unknown",
                "reason": "Project not found",
                "owner": "Unknown",
            }
        },
        "forbidden": {
            "Orion": {
                "status": ["Delayed", "On Track"],
            }
        },
    },
    {
        "id": "mercury_owner",
        "input": "Who owns Mercury?",
        "expected": {
            "Mercury": {"owner": "Engineering"},
        },
    },
]


def calculate_evaluation_metrics(results):
    total_requests = len(results)

    completed = [
        result for result in results
        if result["status"] == "completed"
    ]

    operational_failures = total_requests - len(completed)

    passed = sum(result["passed"] for result in completed)

    # Only count retry metrics when a trace was returned.
    observed_retries = [
        result["retry_count"]
        for result in results
        if result["retry_count"] is not None
    ]

    total_verdicts = 0
    total_rejections = 0
    requests_with_retries = 0

    for result in results:
        trace = result.get("trace")
        if trace is None:
            continue

        metrics = trace.get("metrics", {})
        total_verdicts += metrics.get("judge_verdicts", 0)
        total_rejections += metrics.get("judge_rejections", 0)

        if metrics.get("had_retry", False):
            requests_with_retries += 1

    return {
        "total_requests": total_requests,
        "completed_requests": len(completed),
        "operational_failures": operational_failures,

        "passed_checks": passed,
        "failed_checks": len(completed) - passed,
        "pass_rate": (
            passed / len(completed) if completed else None
        ),

        "judge_verdicts": total_verdicts,
        "judge_rejections": total_rejections,
        "judge_rejection_rate": (
            total_rejections / total_verdicts
            if total_verdicts else None
        ),

        "requests_with_retries": requests_with_retries,
        "retry_rate_among_observed_requests": (
            requests_with_retries / len(observed_retries)
            if observed_retries else None
        ),
        "average_retries_per_observed_request": (
            sum(observed_retries) / len(observed_retries)
            if observed_retries else None
        ),
        "requests_with_known_retry_count": len(observed_retries),
    }


def check_expected_fields(answer, expected, forbidden=None, allowed_projects=None,):
    projects = {
        project["project_name"]: project
        for project in answer.get("projects", [])
    }

    failures = []
    # Check that no unexpected projects are returned.
    if allowed_projects is not None:
        unexpected_projects = (
            set(projects.keys()) - set(allowed_projects)
        )

        for project_name in unexpected_projects:
            failures.append(
                f"Unexpected project returned: {project_name}"
            )

    # Check values that must be present.
    for project_name, expected_fields in expected.items():
        actual = projects.get(project_name)

        if actual is None:
            failures.append(f"Missing project: {project_name}")
            continue

        for field, expected_value in expected_fields.items():
            actual_value = actual.get(field)

            if actual_value != expected_value:
                failures.append(
                    f"{project_name}.{field}: "
                    f"expected {expected_value!r}, "
                    f"got {actual_value!r}"
                )

    # Check values that must NOT appear.
    for project_name, forbidden_fields in (forbidden or {}).items():
        actual = projects.get(project_name)

        if actual is None:
            continue

        for field, forbidden_values in forbidden_fields.items():
            # Allow either one forbidden value or a list of values.
            if not isinstance(forbidden_values, list):
                forbidden_values = [forbidden_values]

            actual_value = actual.get(field)

            if actual_value in forbidden_values:
                failures.append(
                    f"{project_name}.{field}: "
                    f"forbidden value {actual_value!r}"
                )

    return {
        "passed": len(failures) == 0,
        "failures": failures,
    }


def run_evaluation(cases, runs_per_case=3):
    results = []

    for case in cases:
        for run_number in range(1, runs_per_case + 1):
            result = {
                "case_id": case["id"],
                "run_number": run_number,
                "status": "error",
                "passed": False,
                "failures": [],
                "retry_count": None,
                "trace": None,
            }

            try:
                run_result = run_agent(case["input"])

                answer = run_result["answer"]
                trace = run_result["trace"]

                check = check_expected_fields(
                    answer,
                    case["expected"],
                    case.get("forbidden"),
                    case.get("allowed_projects"),
                )

                result.update({
                    "status": "completed",
                    "passed": check["passed"],
                    "failures": check["failures"],
                    "retry_count": trace["metrics"]["retry_count"],
                    "trace": trace,
                })

            except Exception as e:
                result["failures"] = [
                    f"Operational failure: {type(e).__name__}: {e}"
                ]

            results.append(result)

    return {
        "results": results,
        "metrics": calculate_evaluation_metrics(results),
        "observability": calculate_observability_metrics(results),
    }


if __name__ == "__main__":
    evaluation = run_evaluation(
        test,
        runs_per_case=1,
    )
    #print(json.dumps(evaluation, indent=2))
    print(json.dumps(
    calculate_observability_metrics(evaluation["results"]),
    indent=2
))
