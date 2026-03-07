from templates.engine import LumenEngine, TemplateValidationError


def test_engine_registry():
    engine = LumenEngine()
    assert "M4-N-014" in engine.registry
    assert "M4-F-001" in engine.registry


def test_generate_practice_is_deterministic_for_same_seed():
    engine = LumenEngine()

    payload_a = engine.generate_practice("M4-N-014", seed="fixed-seed")
    payload_b = engine.generate_practice("M4-N-014", seed="fixed-seed")

    assert payload_a == payload_b


def test_generate_practice_raises_validation_error_for_invalid_template(monkeypatch):
    class InvalidTemplate:
        def __init__(self, seed=None):
            self.seed = seed

        def generate(self):
            return {
                "skill_id": "BAD-000",
                "seed": self.seed or "x",
                "evidence_type": "multiple_choice",
                "question_text": "bad payload",
                "options": ["1"],
                "correct_answer": "1",
                "hints": [],
                "error_mapping": {},
            }

    engine = LumenEngine()
    monkeypatch.setitem(engine.registry, "BAD-000", InvalidTemplate)

    try:
        engine.generate_practice("BAD-000", seed="s")
        assert False, "Expected TemplateValidationError"
    except TemplateValidationError:
        assert True
