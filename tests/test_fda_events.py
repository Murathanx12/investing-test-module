import json

from aegis_brain.events.fda import FdaEvent, parse_applications

SAMPLE = {
    "meta": {"results": {"total": 2}},
    "results": [
        {
            "application_number": "NDA212345",
            "sponsor_name": "EXAMPLE THERAPEUTICS",
            "products": [{"brand_name": "EXAMPLIA"}],
            "openfda": {"generic_name": ["examplinib"]},
            "submissions": [
                {"submission_type": "SUPPL", "submission_status": "AP",
                 "submission_status_date": "20240110"},
                {"submission_type": "ORIG", "submission_status": "AP",
                 "submission_status_date": "20230415", "review_priority": "PRIORITY"},
            ],
        },
        {
            # no ORIG approval -> excluded
            "application_number": "NDA299999",
            "sponsor_name": "NOPE INC",
            "submissions": [
                {"submission_type": "SUPPL", "submission_status": "AP",
                 "submission_status_date": "20230601"},
            ],
        },
    ],
}


def test_parse_extracts_orig_approval_only():
    events = parse_applications(SAMPLE)
    assert len(events) == 1
    e = events[0]
    assert e.application_number == "NDA212345"
    assert e.approval_date == "2023-04-15"
    assert e.brand_name == "EXAMPLIA"
    assert e.generic_name == "examplinib"
    assert e.review_priority == "PRIORITY"


def test_earliest_orig_wins():
    doc = json.loads(json.dumps(SAMPLE))
    doc["results"][0]["submissions"].append(
        {"submission_type": "ORIG", "submission_status": "AP",
         "submission_status_date": "20220101", "review_priority": "STANDARD"}
    )
    events = parse_applications(doc)
    assert events[0].approval_date == "2022-01-01"
    assert events[0].review_priority == "STANDARD"


def test_handles_missing_fields():
    doc = {"results": [{"application_number": "X", "submissions": [
        {"submission_type": "ORIG", "submission_status": "AP",
         "submission_status_date": "20210505"}]}]}
    events = parse_applications(doc)
    assert isinstance(events[0], FdaEvent)
    assert events[0].brand_name == "" and events[0].sponsor_name == ""
