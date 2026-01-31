import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

def test_crash():
    print("Testing Resume Parser Crash...")
    
    # 1. Create Dummy PDF
    pdf_path = "data/resumes/test_crash.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    
    # Create valid PDF using reportlab or fpdf if available? 
    # Or just a text file renamed to pdf might confuse fitz.
    # Let's try to make a minimal valid PDF structure or just use a text file
    # Fitz will raise an error if invalid format, we want to see if that CRASHES or returns error.
    
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/MediaBox [0 0 612 792]\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 100 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000079 00000 n\n0000000173 00000 n\n0000000301 00000 n\n0000000380 00000 n\ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n492\n%%EOF")

    try:
        from backend.agents.resume_parser import ResumeParserV2
        parser = ResumeParserV2()
        print("Parser initialized.")
        
        result = parser.parse_and_save(pdf_path)
        print(f"Result: {result}")
        if result:
            print(f"Parsed Name: {result.parsed_data.get('name')}")
            
    except ImportError as e:
        print(f"ImportError: {e}")
    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_crash()
