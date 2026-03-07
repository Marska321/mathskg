from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import Optional

from models.submission import QuestionSchema


class TemplateRegistrationError(RuntimeError):
    """Raised when template discovery/registration fails."""


class TemplateValidationError(ValueError):
    """Raised when a generated template payload is invalid."""


def _class_name_to_skill_id(class_name: str) -> str | None:
    # Example: Template_M4_N_014 -> M4-N-014
    if not class_name.startswith("Template_"):
        return None

    parts = class_name[len("Template_") :].split("_")
    if len(parts) != 3:
        return None

    grade, domain, ordinal = parts
    if not (grade and domain and ordinal):
        return None

    return f"{grade}-{domain}-{ordinal}"


def _discover_template_modules() -> list[str]:
    templates_dir = Path(__file__).resolve().parent
    module_names: list[str] = []

    for file_path in sorted(templates_dir.rglob("*.py")):
        if file_path.name in {"engine.py", "base_template.py"}:
            continue
        relative_path = file_path.relative_to(templates_dir.parent).with_suffix("")
        module_name = ".".join(relative_path.parts)
        module_names.append(module_name)

    return module_names


def build_template_registry() -> dict[str, type]:
    registry: dict[str, type] = {}

    for module_name in _discover_template_modules():
        module = importlib.import_module(module_name)

        for class_name, class_obj in inspect.getmembers(module, inspect.isclass):
            if class_obj.__module__ != module.__name__:
                continue

            skill_id = _class_name_to_skill_id(class_name)
            if skill_id is None:
                continue

            if skill_id in registry:
                raise TemplateRegistrationError(
                    f"Duplicate template registration detected for {skill_id} in module {module_name}."
                )

            registry[skill_id] = class_obj

    return registry


class LumenEngine:
    def __init__(self):
        self.registry = build_template_registry()

    def generate_practice(self, skill_id: str, seed: Optional[str] = None) -> dict:
        generator_class = self.registry.get(skill_id)
        if generator_class is None:
            raise ValueError(f"Generator for {skill_id} is not yet built.")

        generator = generator_class(seed=seed)
        raw_payload = generator.generate()

        try:
            validated = QuestionSchema.model_validate(raw_payload)
        except Exception as exc:
            raise TemplateValidationError(
                f"Generated payload for {skill_id} failed QuestionSchema validation: {exc}"
            ) from exc

        return validated.model_dump()
