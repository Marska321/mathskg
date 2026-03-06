from typing import Optional
from templates.grade_4.place_value import Template_M4_N_014
from templates.grade_4.fractions import Template_M4_F_001

class LumenEngine:
    def __init__(self):
        self.registry = {
            "M4-N-014": Template_M4_N_014,
            "M4-F-001": Template_M4_F_001,
        }

    def generate_practice(self, skill_id: str, seed: Optional[str] = None):
        if skill_id not in self.registry:
            raise ValueError(f"Generator for {skill_id} is not yet built.")
        
        # Instantiate the correct template
        generator = self.registry[skill_id](seed=seed)
        return generator.generate()
