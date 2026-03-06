import uuid

from models.submission import QuestionSchema
from templates.grade_4.fractions import Template_M4_F_001
from templates.grade_4.place_value import Template_M4_N_014


def run_robustness_test(template_class, iterations: int = 1000) -> None:
    print(f"\nStarting robustness test for: {template_class.__name__}")
    print(f"Running {iterations} deterministic simulations...")

    passed = 0
    failed = 0

    for index in range(iterations):
        test_seed = f"test-seed-{uuid.uuid4().hex[:8]}"
        generator = template_class(seed=test_seed)

        try:
            raw_question = generator.generate()
            validated_question = QuestionSchema(**raw_question)

            if validated_question.correct_answer.lstrip("-").isdigit():
                if int(validated_question.correct_answer) < 0:
                    raise ValueError(
                        f"Math error: generated a negative answer ({validated_question.correct_answer})."
                    )

            passed += 1

        except Exception as exc:
            print(f"FAILED on iteration {index + 1}")
            print(f"Seed to reproduce: '{test_seed}'")
            print(f"Error: {exc}")
            failed += 1
            break

    if failed == 0:
        print(f"ALL PASSED: {iterations} variations tested successfully.")
    else:
        print("TEST HALTED. Fix the template and try again.")


if __name__ == "__main__":
    run_robustness_test(Template_M4_N_014, 1000)
    run_robustness_test(Template_M4_F_001, 1000)
