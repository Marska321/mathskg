from templates.base_template import BaseTemplate

class Template_M4_F_001(BaseTemplate):
    """Skill: Distinguish between equal and unequal parts of a whole shape"""
    def generate(self):
        shapes = ["circle", "square", "rectangle", "pizza"]
        shape = self.rng.choice(shapes)
        
        correct_answer = f"A {shape} cut perfectly down the middle."
        options = [
            correct_answer,
            f"A {shape} with a tiny piece cut off the edge.",
            f"A {shape} cut into one large piece and one small piece.",
            f"A {shape} where one side is much wider than the other."
        ]
        self.rng.shuffle(options)
        
        hints = [
            "Equal parts mean every single piece is exactly the same size.",
            "Look for the description where the pieces match perfectly."
        ]
        
        return {
            "skill_id": "M4-F-001",
            "seed": self.seed,
            "evidence_type": "multiple_choice",
            "question_text": f"Which {shape} is divided into equal parts?",
            "options": options,
            "correct_answer": correct_answer,
            "hints": hints
        }
