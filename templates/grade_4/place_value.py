from templates.base_template import BaseTemplate

class Template_M4_N_014(BaseTemplate):
    """Skill: Subtract 2-digit numbers without borrowing"""
    def generate(self):
        tens_a = self.rng.randint(2, 9)
        units_a = self.rng.randint(2, 9)
        
        tens_b = self.rng.randint(1, tens_a - 1)
        units_b = self.rng.randint(1, units_a - 1)
        
        num_a = (tens_a * 10) + units_a
        num_b = (tens_b * 10) + units_b
        
        correct_answer = num_a - num_b
        
        # Distractors based on common CAPS failure points
        d1 = num_a + num_b               # Error: Added instead of subtracted
        d2 = correct_answer + 10         # Error: Tens column mistake
        d3 = correct_answer - 1          # Error: Counting off by one
        
        # Create the Diagnostic Key!
        error_map = {
            str(d1): "MC_SUB_01_ADDED_INSTEAD",
            str(d2): "MC_SUB_02_TENS_COLUMN_ERROR",
            str(d3): "MC_SUB_03_COUNTING_ERROR"
        }
        
        raw_options = [correct_answer, d1, d2, d3]
        options = list(dict.fromkeys(raw_options)) 
        
        # Fallback for duplicates to satisfy Pydantic
        while len(options) < 4:
            new_d = correct_answer + self.rng.randint(2, 15)
            if new_d not in options:
                options.append(new_d)
                # Tag generic random errors as UNKNOWN_ERROR
                error_map[str(new_d)] = "UNKNOWN_ERROR" 
        
        self.rng.shuffle(options)
        
        hints = [
            f"Step 1: Subtract the units. {units_a} - {units_b} = {units_a - units_b}",
            f"Step 2: Subtract the tens. {tens_a * 10} - {tens_b * 10} = {(tens_a - tens_b) * 10}",
            f"Step 3: Combine them. {(tens_a - tens_b) * 10} + {units_a - units_b} = {correct_answer}"
        ]
        
        return {
            "skill_id": "M4-N-014",
            "seed": self.seed,
            "evidence_type": "multiple_choice",
            "question_text": f"Calculate: {num_a} - {num_b}",
            "options": [str(opt) for opt in options],
            "correct_answer": str(correct_answer),
            "hints": hints,
            "error_mapping": error_map
        }
