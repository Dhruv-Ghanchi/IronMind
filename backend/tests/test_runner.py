import traceback
import sys
from extraction.sql_extractor import extract_sql_entities
from extraction.python_extractor import extract_python_entities
from extraction.js_extractor import extract_js_entities
from extraction.entity_index import build_entity_index

results = []

def run_test(name, func, args, expected_check):
    try:
        if isinstance(args, tuple):
            res = func(*args)
        else:
            res = func(args)
        
        pass_test, msg = expected_check(res)
        if pass_test:
            results.append((name, "PASS", msg))
        else:
            results.append((name, "FAIL", f"Expected met? False. Output: {res} | Note: {msg}"))
            
    except Exception as e:
        results.append((name, "FAIL", f"Crashed with {type(e).__name__}: {str(e)}"))

print("--- SQL Extractor ---")
def check_empty(res):
    if all(not v for v in res.values()):
        return True, "All empty lists, no crash"
    return False, "Not all empty lists"

# SQL Test 1
run_test("SQL Test 1 — completely empty file", extract_sql_entities, "", check_empty)
# SQL Test 2
run_test("SQL Test 2 — random non-SQL text", extract_sql_entities, "hello world this is not sql at all !!!", check_empty)
# SQL Test 3
def check_sql_3(res):
    return True, "Did not crash, partial or empty ok"
run_test("SQL Test 3 — half-written CREATE TABLE", extract_sql_entities, """
CREATE TABLE users (
    id INT PRIMARY KEY,
    email VARCHAR(255)
""", check_sql_3)
# SQL Test 4
run_test("SQL Test 4 — only comments", extract_sql_entities, """
-- this is a comment
/* another comment */
-- nothing else here
""", check_empty)
# SQL Test 5
run_test("SQL Test 5 — None input", extract_sql_entities, None, check_empty)

print("--- Python Extractor ---")
# Py Test 1
run_test("Python Test 1 — SyntaxError", extract_python_entities, """
def broken_function(
    x = 
    return x
""", check_empty)
# Py Test 2
run_test("Python Test 2 — no entities of interest", extract_python_entities, """
x = 1
y = 2
z = x + y
print(z)
""", check_empty)
# Py Test 3
run_test("Python Test 3 — empty file", extract_python_entities, "", check_empty)
# Py Test 4
run_test("Python Test 4 — binary-looking garbage", extract_python_entities, "\x00\x01\x02\xff\xfe", check_empty)
# Py Test 5
def check_py_5(res):
    expected_imp = ["os"]
    expected_fun = ["get_data"]
    if set(expected_imp).issubset(set(res.get("imports", []))) and set(expected_fun).issubset(set(res.get("functions", []))):
        return True, "Matches nested calls expectation"
    return False, "Did not match imports/functions"
run_test("Python Test 5 — nested calls", extract_python_entities, """
import os
def get_data():
    return os.path.join(os.getcwd(), "data")
""", check_py_5)

print("--- JS/TS Extractor ---")
# JS Test 1
def check_js_1(res):
    if "App" in res.get("components", []):
        return True, "component App found"
    return False, "App not found"
run_test("JS Test 1 — JSX syntax", extract_js_entities, """
const App = () => (
    <div className="app">
        <h1>Hello {name}</h1>
    </div>
)
""", check_js_1)
# JS Test 2
run_test("JS Test 2 — completely empty file", extract_js_entities, "", check_empty)
# JS Test 3
def check_js_3(res):
    return True, "Did not crash"
run_test("JS Test 3 — fetch with no path", extract_js_entities, """
const getData = () => {
    fetch()
    fetch("")
    fetch(variable)
}
""", check_js_3)
# JS Test 4
def check_js_4(res):
    if "A" in res.get("components", []) and "fetch /api/users" in res.get("api_calls", []):
        return True, "A and fetch /api/users found"
    return False, f"Missing A or fetch. api_calls: {res.get('api_calls')}"
run_test("JS Test 4 — minified JS", extract_js_entities, "const A=()=>{fetch('/api/users').then(r=>r.json()).then(d=>setData(d))}", check_js_4)
# JS Test 5
def check_js_5(res):
    if "ProfilePage" in res.get("components", []) and "fetch /profile" in res.get("api_calls", []):
        return True, "ProfilePage and fetch /profile found"
    return False, "Missing component or fetch call"
run_test("JS Test 5 — TypeScript with type annotations", extract_js_entities, """
interface User { email: string; id: number; }
const ProfilePage: React.FC<User> = ({ email }) => {
    const data = fetch('/profile')
    return null
}
""", check_js_5)

print("--- Full pipeline ---")
def check_pipeline(res):
    if "users.email" in res.get("columns", []) and "GET /profile" in res.get("routes", []) and "ProfilePage" in res.get("components", []) and "fetch /profile" in res.get("api_calls", []):
        return True, "Demo chain intact"
    return False, "Demo chain broken"

code_map = {
    "schema.sql": "CREATE TABLE users (id INT, email VARCHAR(255));",
    "broken.py": "def oops(\n    return ???",
    "valid.py": """
import fastapi
@app.get("/profile")
def get_profile():
    return user.email
""",
    "frontend.tsx": "const ProfilePage = () => { fetch('/profile') }"
}
run_test("Pipeline Test 1 — mixed code_map", build_entity_index, code_map, check_pipeline)

# Print Summary Table
print("\n=== SUMMARY TABLE ===")
print(f"{'Test Name'.ljust(45)} | {'Result'.ljust(6)} | {'Notes'}")
print("-" * 100)
for name, status, note in results:
    print(f"{name.ljust(45)} | {status.ljust(6)} | {note}")
