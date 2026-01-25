
import pandas as pd
import io
import os
try:
    import openpyxl
    print("✅ Openpyxl is installed")
except ImportError:
    print("❌ Openpyxl is MISSING")
    exit(1)

def test_export():
    print("Testing Excel generation...")
    buffer = io.BytesIO()
    try:
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df1 = pd.DataFrame({'Data': [1, 2, 3]})
            df1.to_excel(writer, sheet_name='Sheet1')
        
        val = buffer.getvalue()
        if len(val) > 0:
            print(f"✅ Export successful. Bytes: {len(val)}")
        else:
            print("❌ Export produced 0 bytes")
    except Exception as e:
        print(f"❌ Export failed: {e}")

if __name__ == "__main__":
    test_export()
