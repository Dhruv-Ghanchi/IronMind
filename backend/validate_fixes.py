"""
Quick validation tests for the four critical gap fixes.
Run from the ByteCamp root:  python backend/validate_fixes.py
"""
import zipfile
import shutil
import tempfile
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ingestion.zip_handler import extract_zip, read_files_to_dict
from backend.ingestion.file_scanner import scan_directory

PASS = "\u2713 PASS"
FAIL = "\u2717 FAIL"

# ─────────────────────────────────────────────────────────
# Test 1: BadZipFile → clean ValueError (no raw 500 crash)
# ─────────────────────────────────────────────────────────
bad_zip_path = tempfile.mktemp(suffix=".zip")
with open(bad_zip_path, "w") as f:
    f.write("this is not a zip")
try:
    extract_zip(bad_zip_path)
    print(FAIL, "Test 1: BadZipFile should raise ValueError")
except ValueError as e:
    print(PASS, "Test 1: BadZipFile raised clean ValueError:", e)
except Exception as e:
    print(FAIL, "Test 1: Unexpected exception type:", type(e).__name__, e)
finally:
    if os.path.exists(bad_zip_path):
        os.remove(bad_zip_path)

# ─────────────────────────────────────────────────────────
# Test 2: read_files_to_dict → {path: code} dict + cleanup
# ─────────────────────────────────────────────────────────
test_dir = tempfile.mkdtemp()
os.makedirs(os.path.join(test_dir, "src"))
with open(os.path.join(test_dir, "src", "app.py"), "w") as f:
    f.write('print("hello")')

zip_path = tempfile.mktemp(suffix=".zip")
with zipfile.ZipFile(zip_path, "w") as z:
    z.write(os.path.join(test_dir, "src", "app.py"), "src/app.py")
shutil.rmtree(test_dir)

extracted = extract_zip(zip_path)
os.remove(zip_path)
code_map = read_files_to_dict(extracted, ["src/app.py"])

if isinstance(code_map, dict) and "src/app.py" in code_map and code_map["src/app.py"] == 'print("hello")':
    print(PASS, "Test 2: read_files_to_dict returns correct {path: code} shape")
else:
    print(FAIL, "Test 2: wrong code_map:", code_map)

if not os.path.exists(extracted):
    print(PASS, "Test 2: extracted dir deleted after read_files_to_dict (no storage leak)")
else:
    print(FAIL, "Test 2: extracted dir still exists — storage leak!")

# ─────────────────────────────────────────────────────────
# Test 3: scan_directory returns timed_out + elapsed_seconds
# ─────────────────────────────────────────────────────────
test_dir2 = tempfile.mkdtemp()
with open(os.path.join(test_dir2, "main.py"), "w") as f:
    f.write("x = 1")
result = scan_directory(test_dir2)
shutil.rmtree(test_dir2)

if "timed_out" in result and "elapsed_seconds" in result:
    print(PASS, f"Test 3: scan_directory returns timed_out={result['timed_out']}, elapsed={result['elapsed_seconds']}s")
else:
    print(FAIL, "Test 3: missing timed_out or elapsed_seconds in scan result")

print("\nAll validation tests complete.")
