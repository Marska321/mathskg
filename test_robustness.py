import uuid
from lumen_engine import Template_M4_N_014, Template_M4_F_001, QuestionSchema

def run_robustness_test(template_class, iterations=1000):
    print(f"\n🧪 Starting Robustness Test for: {template_class.__name__}")
    print(f"Running {iterations} deterministic simulations...")
    
    passed = 0
    failed = 0
    
    for i in range(iterations):
        # Generate a random seed for this specific test run
        test_seed = f"test-seed-{uuid.uuid4().hex[:8]}"
        generator = template_class(seed=test_seed)
        
        try:
            # 1. Generate the raw dictionary
            raw_question = generator.generate()
            
            # 2. Gate 2 Check: Pass it through Pydantic to ensure the schema is perfect
            validated_question = QuestionSchema(**raw_question)
            
            # 3. Gate 3 Custom Math Constraints
            # Example: For Grade 4 subtraction, ensure the answer is NEVER negative
            if validated_question.correct_answer.lstrip('-').isdigit():
                if int(validated_question.correct_answer) < 0:
                    raise ValueError(f"Math Error: Generated a negative answer ({validated_question.correct_answer}).")
            
            # If we get here without an exception, it passed!
            passed += 1
            
        except Exception as e:
            print(f"❌ FAILED on iteration {i+1}")
            print(f"   🐛 Seed to reproduce: '{test_seed}'")
            print(f"   ⚠️ Error: {e}")
            failed += 1
            break # Stop on the very first failure so you can debug it
            
    if failed == 0:
        print(f"✅ ALL PASSED: {iterations} variations tested successfully. Zero edge cases found.")
    else:
        print(f"🛑 TEST SUITE HALTED. Fix the template and try again.")

if __name__ == "__main__":
    # Run the stress test on the templates we've built so far
    run_robustness_test(Template_M4_N_014, 1000)
    run_robustness_test(Template_M4_F_001, 1000)