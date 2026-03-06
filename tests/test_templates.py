from templates.engine import LumenEngine

def test_engine_registry():
    engine = LumenEngine()
    assert "M4-N-014" in engine.registry
    assert "M4-F-001" in engine.registry
