from evaluate import aggregate_results


def test_aggregate_results_reports_pass_rate_and_statuses():
    metrics = aggregate_results([
        {"passed": True, "reward": 1.0, "status": "passed"},
        {"passed": False, "reward": 0.0, "status": "failed"},
    ])
    assert metrics["examples"] == 2
    assert metrics["pass_at_1"] == 0.5
    assert metrics["status_counts"] == {"passed": 1, "failed": 1}
