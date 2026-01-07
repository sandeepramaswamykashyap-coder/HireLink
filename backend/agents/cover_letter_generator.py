import random

class CoverLetterGenerator:
    def __init__(self):
        # We can implement a simple template engine first. 
        # For actual GPT-2, we would use transformers, but that is heavy (500MB+ download).
        # We will provide a template fallback and an option to use GPT-2 if installed.
        pass

    def generate(self, job_title, company_name, candidate_name, skills):
        templates = [
            f"Dear Hiring Manager,\n\nI am writing to express my strong interest in the {job_title} position at {company_name}. With my experience in {', '.join(skills[:3])}, I believe I can contribute significantly to your team.\n\nSincerely,\n{candidate_name}",
            f"To the Recruitment Team at {company_name},\n\nI am excited to apply for the {job_title} role. My background in {', '.join(skills[:3])} aligns perfectly with your requirements.\n\nBest regards,\n{candidate_name}"
        ]
        return random.choice(templates)

    # Optional: Neural generation
    def generate_neural(self, prompt):
        # Placeholder for transformers implementation
        pass
