from expense_triage import data


def test_report_text_never_leaks_the_expected_label():
    for r in data.reports():
        assert r["expected"] in data.DECISIONS
        assert "expected" not in data.format_report(r).lower()


def test_every_report_has_a_city_and_employee_in_the_data():
    for r in data.reports():
        assert r["city"] in data.per_diems()
        assert r["employee_id"] in data.prior_claims()
        assert r["category"] in data.policy()["categories"]
