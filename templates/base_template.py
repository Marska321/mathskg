import random
import uuid
from typing import Optional

class BaseTemplate:
    """The core blueprint for all Lumen question generators."""
    def __init__(self, seed: Optional[str] = None):
        # If no seed is provided, generate a random one
        self.seed = seed if seed else uuid.uuid4().hex[:8]
        self.rng = random.Random(self.seed)

    def generate(self) -> dict:
        raise NotImplementedError("Each skill must implement its own generate() logic.")
