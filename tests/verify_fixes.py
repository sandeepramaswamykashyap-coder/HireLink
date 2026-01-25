import sys
import os
import re

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

def test_security_utils():
    print("Testing Security Utils...")
    try:
        from backend.utils.security import encrypt_value, decrypt_value
        val = "secret_password"
        enc = encrypt_value(val)
        dec = decrypt_value(enc)
        
        assert val != enc, "Encryption failed (value equal to encrypted)"
        assert val == dec, "Decryption failed (value mismatch)"
        print("✅ Security Utils: PASSED")
    except ImportError:
        print("❌ Security Utils: FAILED (ImportError)")
    except AssertionError as e:
        print(f"❌ Security Utils: FAILED ({e})")
    except Exception as e:
        print(f"❌ Security Utils: FAILED ({e})")

def test_log_redaction():
    print("Testing Log Redaction Logic...")
    sample_log = """
    2023-10-27 10:00:00 - INFO - DB Init
    2023-10-27 10:00:01 - DEBUG - User created password='SuperSecretPassword123'
    2023-10-27 10:00:02 - INFO - Environment GEMINI_API_KEY=AIzaSyD-FakeKey12345
    """
    
    # Logic copied from app.py patch
    log_content = sample_log
    log_content = re.sub(r"password=['\"](.*?)['\"]", "password='***'", log_content)
    log_content = re.sub(r"GEMINI_API_KEY=(.*)", "GEMINI_API_KEY=***", log_content)
    
    if "SuperSecretPassword123" in log_content:
        print("❌ Log Redaction: FAILED (Password visible)")
    elif "AIzaSyD-FakeKey12345" in log_content:
        print("❌ Log Redaction: FAILED (API Key visible)")
    else:
        print("✅ Log Redaction: PASSED")

def test_email_validation():
    print("Testing Email Validation Logic...")
    valid = "test@example.com"
    invalid = "testexample.com"
    
    # Logic copied from app.py patch
    is_valid_pass = bool(re.match(r"[^@]+@[^@]+\.[^@]+", valid))
    is_invalid_pass = bool(re.match(r"[^@]+@[^@]+\.[^@]+", invalid))
    
    if is_valid_pass and not is_invalid_pass:
        print("✅ Email Validation: PASSED")
    else:
        print(f"❌ Email Validation: FAILED (Valid={is_valid_pass}, Invalid={is_invalid_pass})")

if __name__ == "__main__":
    test_security_utils()
    test_log_redaction()
    test_email_validation()
