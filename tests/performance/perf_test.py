import time
import os
from backend.agents.resume_parser import ResumeParser

def benchmark_parser():
    parser = ResumeParser()
    file_path = "dummy_resume.pdf"
    
    if not os.path.exists(file_path):
        print("Dummy resume not found, skipping benchmark.")
        return
        
    print("Starting Resume Parser Benchmark...")
    start_time = time.time()
    
    # Run 3 times
    for i in range(3):
        t0 = time.time()
        parser.extract_text(file_path) # Measure text extraction specifically or full parse? 
        # Full parse involves DB which might be noisy. Let's measure text extraction + mock LLM overhead if possible 
        # or just run full parse_and_save if we don't mind DB writes (it's sqlite)
        
        # Let's benchmark extract_text as baseline
        txt = parser.extract_text(file_path)
        dt = time.time() - t0
        print(f"Run {i+1}: Extract Text took {dt:.4f}s")
        
    total_time = time.time() - start_time
    print(f"Total Benchmark Time: {total_time:.4f}s")
    
if __name__ == "__main__":
    benchmark_parser()
