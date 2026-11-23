import json
from pathlib import Path

PROMPTS = Path(__file__).parent.parent / "evals" / "prompts.json"


def test_eval_prompts_are_well_formed():
    items = json.loads(PROMPTS.read_text())
    assert len(items) >= 8
    assert len({i["id"] for i in items}) == len(items)
    for item in items:
        assert item["prompt"].strip()
        assert item["expect"].strip()
