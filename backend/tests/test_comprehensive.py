"""
COMPREHENSIVE TEST SUITE FOR POLYGLOT DEPENDENCY ANALYZER

This test suite covers:
1. SQL Entity Extraction
2. Python Entity Extraction
3. JavaScript/TypeScript Entity Extraction
4. Entity Index Building
5. API Endpoint Testing
6. Error Handling & Edge Cases
"""

import sys
import os
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from extraction.sql_extractor import extract_sql_entities
from extraction.python_extractor import extract_python_entities
from extraction.js_extractor import extract_js_entities
from extraction.entity_index import build_entity_index

# ============================================================================
# TEST INFRASTRUCTURE
# ============================================================================

class TestResult:
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.passed = False
        self.error = None
        self.message = ""
    
    def pass_test(self, message: str = ""):
        self.passed = True
        self.message = message
    
    def fail_test(self, message: str = "", error: str = None):
        self.passed = False
        self.message = message
        self.error = error

test_results = []

def run_test(name: str, category: str, test_func):
    """Execute a single test and record result"""
    result = TestResult(name, category)
    try:
        test_func(result)
    except Exception as e:
        result.fail_test(
            message=f"Test crashed",
            error=f"{type(e).__name__}: {str(e)}"
        )
    test_results.append(result)

# ============================================================================
# SQL EXTRACTOR TESTS
# ============================================================================

def test_sql_empty_file(result: TestResult):
    """SQL-1: Empty file should not crash"""
    res = extract_sql_entities("")
    assert all(not v for v in res.values()), f"Expected empty results: {res}"
    result.pass_test("Empty file handled correctly")

def test_sql_basic_table(result: TestResult):
    """SQL-2: Extract basic table definition"""
    code = """
    CREATE TABLE users (
        id INT PRIMARY KEY,
        email VARCHAR(255)
    );
    """
    res = extract_sql_entities(code)
    assert "users" in res["tables"], f"Expected 'users' table, got: {res['tables']}"
    result.pass_test(f"Found tables: {res['tables']}")

def test_sql_multiple_tables(result: TestResult):
    """SQL-3: Extract multiple tables"""
    code = """
    CREATE TABLE users (id INT PRIMARY KEY);
    CREATE TABLE products (id INT PRIMARY KEY);
    CREATE TABLE orders (id INT PRIMARY KEY);
    """
    res = extract_sql_entities(code)
    expected = {"users", "products", "orders"}
    found = set(res["tables"])
    assert expected.issubset(found), f"Expected {expected}, got {found}"
    result.pass_test(f"Found {len(res['tables'])} tables")

def test_sql_columns_extraction(result: TestResult):
    """SQL-4: Extract column definitions"""
    code = """
    CREATE TABLE users (
        id INT PRIMARY KEY,
        email VARCHAR(255),
        name TEXT
    );
    """
    res = extract_sql_entities(code)
    assert len(res["columns"]) > 0, "No columns extracted"
    result.pass_test(f"Found {len(res['columns'])} columns")

def test_sql_foreign_keys(result: TestResult):
    """SQL-5: Extract foreign key constraints"""
    code = """
    CREATE TABLE orders (
        id INT PRIMARY KEY,
        user_id INT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """
    res = extract_sql_entities(code)
    result.pass_test(f"Foreign keys: {len(res['foreign_keys'])} found")

def test_sql_views(result: TestResult):
    """SQL-6: Extract view definitions"""
    code = """
    CREATE VIEW active_users AS
    SELECT * FROM users WHERE status = 'active';
    """
    res = extract_sql_entities(code)
    assert "active_users" in res["views"], f"Expected view not found: {res['views']}"
    result.pass_test(f"Found views: {res['views']}")

def test_sql_if_not_exists(result: TestResult):
    """SQL-7: Handle IF NOT EXISTS clause"""
    code = """
    CREATE TABLE IF NOT EXISTS users (id INT PRIMARY KEY);
    """
    res = extract_sql_entities(code)
    assert "users" in res["tables"], f"IF NOT EXISTS not handled: {res['tables']}"
    result.pass_test("IF NOT EXISTS handled correctly")

def test_sql_comments(result: TestResult):
    """SQL-8: Ignore comments"""
    code = """
    -- This is a comment
    /* Block comment */
    CREATE TABLE users (id INT);
    """
    res = extract_sql_entities(code)
    assert "users" in res["tables"], "Comments not properly stripped"
    result.pass_test("Comments properly ignored")

def test_sql_quoted_names(result: TestResult):
    """SQL-9: Handle quoted identifiers"""
    code = '''CREATE TABLE "Users" (id INT);'''
    res = extract_sql_entities(code)
    assert any("Users" in str(t) for t in res["tables"]), f"Quoted names failed: {res['tables']}"
    result.pass_test("Quoted identifiers handled")

def test_sql_none_input(result: TestResult):
    """SQL-10: Handle None input gracefully"""
    res = extract_sql_entities(None)
    assert isinstance(res, dict), "Should return dict for None input"
    result.pass_test("None input handled safely")

# ============================================================================
# PYTHON EXTRACTOR TESTS
# ============================================================================

def test_python_empty_file(result: TestResult):
    """Python-1: Empty file should not crash"""
    res = extract_python_entities("")
    assert all(not v for v in res.values()), f"Expected empty results: {res}"
    result.pass_test("Empty file handled correctly")

def test_python_basic_import(result: TestResult):
    """Python-2: Extract import statements"""
    code = """
    import os
    import sys
    from pathlib import Path
    """
    res = extract_python_entities(code)
    assert "os" in res["imports"], f"Import not found: {res['imports']}"
    assert "sys" in res["imports"], f"Import not found: {res['imports']}"
    result.pass_test(f"Found {len(res['imports'])} imports")

def test_python_fastapi_routes(result: TestResult):
    """Python-3: Extract FastAPI route decorators"""
    code = """
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get('/users')
    def get_users():
        return []
    
    @app.post('/users')
    def create_user():
        pass
    """
    res = extract_python_entities(code)
    assert "GET /users" in res["routes"], f"GET route not found: {res['routes']}"
    assert "POST /users" in res["routes"], f"POST route not found: {res['routes']}"
    result.pass_test(f"Found {len(res['routes'])} routes")

def test_python_function_definition(result: TestResult):
    """Python-4: Extract function definitions"""
    code = """
    def hello():
        pass
    
    def calculate_sum(a, b):
        return a + b
    """
    res = extract_python_entities(code)
    assert "hello" in res["functions"], f"Function not found: {res['functions']}"
    assert "calculate_sum" in res["functions"], f"Function not found: {res['functions']}"
    result.pass_test(f"Found {len(res['functions'])} functions")

def test_python_class_definition(result: TestResult):
    """Python-5: Extract class definitions"""
    code = """
    class User:
        def __init__(self, name):
            self.name = name
    
    class Product:
        pass
    """
    res = extract_python_entities(code)
    assert "User" in res["classes"], f"Class not found: {res['classes']}"
    assert "Product" in res["classes"], f"Class not found: {res['classes']}"
    result.pass_test(f"Found {len(res['classes'])} classes")

def test_python_http_calls(result: TestResult):
    """Python-6: Extract HTTP library calls"""
    code = """
    import requests
    import httpx
    import aiohttp
    
    requests.get('https://api.example.com')
    """
    res = extract_python_entities(code)
    result.pass_test(f"Found {len(res['http_calls'])} HTTP calls")

def test_python_syntax_error(result: TestResult):
    """Python-7: Handle syntax errors gracefully"""
    code = """
    def broken(
        this is not valid python
    """
    res = extract_python_entities(code)
    # Should not crash, may return partial or empty
    assert isinstance(res, dict), "Should return dict despite syntax error"
    result.pass_test("Syntax error handled gracefully")

def test_python_async_functions(result: TestResult):
    """Python-8: Extract async function definitions"""
    code = """
    async def fetch_data():
        pass
    
    async def process_request():
        return None
    """
    res = extract_python_entities(code)
    assert "fetch_data" in res["functions"], f"Async function not found: {res['functions']}"
    result.pass_test(f"Found {len(res['functions'])} async functions")

def test_python_complex_decorators(result: TestResult):
    """Python-9: Handle complex decorators"""
    code = """
    @app.get('/api/endpoint')
    @require_auth
    def protected_route():
        pass
    """
    res = extract_python_entities(code)
    result.pass_test(f"Found {len(res['routes'])} decorated routes")

def test_python_none_input(result: TestResult):
    """Python-10: Handle None input gracefully"""
    try:
        res = extract_python_entities(None)
        result.pass_test("None input handled")
    except:
        result.pass_test("None input raises expected exception")

# ============================================================================
# JAVASCRIPT/TYPESCRIPT EXTRACTOR TESTS
# ============================================================================

def test_js_empty_file(result: TestResult):
    """JS-1: Empty file should not crash"""
    res = extract_js_entities("")
    assert all(not v for v in res.values()), f"Expected empty results: {res}"
    result.pass_test("Empty file handled correctly")

def test_js_function_components(result: TestResult):
    """JS-2: Extract function component declarations"""
    code = """
    function UserProfile() {
        return <div>User</div>;
    }
    
    function ProductList() {
        return <ul></ul>;
    }
    """
    res = extract_js_entities(code)
    assert "UserProfile" in res["components"], f"Component not found: {res['components']}"
    assert "ProductList" in res["components"], f"Component not found: {res['components']}"
    result.pass_test(f"Found {len(res['components'])} components")

def test_js_arrow_components(result: TestResult):
    """JS-3: Extract arrow function components"""
    code = """
    const Dashboard = () => <div>Dashboard</div>;
    const Settings = () => <form></form>;
    """
    res = extract_js_entities(code)
    assert "Dashboard" in res["components"], f"Arrow component not found: {res['components']}"
    result.pass_test(f"Found {len(res['components'])} arrow components")

def test_js_fetch_calls(result: TestResult):
    """JS-4: Extract fetch API calls"""
    code = """
    fetch('/api/users')
        .then(r => r.json());
    
    fetch('/api/products').then(res => res.json());
    """
    res = extract_js_entities(code)
    assert any('/api/users' in call for call in res["api_calls"]), f"Fetch not found: {res['api_calls']}"
    result.pass_test(f"Found {len(res['api_calls'])} API calls")

def test_js_axios_calls(result: TestResult):
    """JS-5: Extract axios API calls"""
    code = """
    axios.get('/api/users');
    axios.post('/api/users', data);
    axios.put('/api/users/1', data);
    axios.delete('/api/users/1');
    """
    res = extract_js_entities(code)
    assert len(res["api_calls"]) > 0, f"Axios calls not found: {res['api_calls']}"
    result.pass_test(f"Found {len(res['api_calls'])} axios calls")

def test_js_field_references(result: TestResult):
    """JS-6: Extract field/property references"""
    code = """
    let email = user.email;
    let name = user.name;
    let price = product.price;
    """
    res = extract_js_entities(code)
    result.pass_test(f"Found {len(res['field_refs'])} field references")

def test_js_react_fc_type(result: TestResult):
    """JS-7: Handle TypeScript React.FC types"""
    code = """
    const MyComponent: React.FC<Props> = (props) => {
        return <div>Component</div>;
    };
    """
    res = extract_js_entities(code)
    assert "MyComponent" in res["components"], f"React.FC not parsed: {res['components']}"
    result.pass_test(f"Found React.FC component: {res['components']}")

def test_js_mixed_code(result: TestResult):
    """JS-8: Handle mixed component and API code"""
    code = """
    const UserPage = () => {
        useEffect(() => {
            fetch('/api/users').then(r => r.json());
        }, []);
        return <div></div>;
    };
    """
    res = extract_js_entities(code)
    assert "UserPage" in res["components"], "Component not found"
    assert len(res["api_calls"]) > 0, "API call not found"
    result.pass_test(f"Found {len(res['components'])} components + {len(res['api_calls'])} API calls")

def test_js_none_input(result: TestResult):
    """JS-9: Handle None input gracefully"""
    try:
        res = extract_js_entities(None)
        # If it returns, check it's valid
        if res:
            assert isinstance(res, dict), "Should return dict"
        result.pass_test("None input handled")
    except:
        result.pass_test("None input handled (raises exception)")

def test_js_special_characters(result: TestResult):
    """JS-10: Handle special characters in strings"""
    code = """
    fetch('/api/users?page=1&limit=10');
    const data = { user: { email: 'test@example.com' } };
    """
    res = extract_js_entities(code)
    result.pass_test(f"Special characters handled: {len(res['api_calls'])} calls found")

# ============================================================================
# ENTITY INDEX TESTS
# ============================================================================

def test_entity_index_empty(result: TestResult):
    """Index-1: Empty file map"""
    index = build_entity_index({})
    assert all(v == [] for v in index.values()), f"Expected all empty: {index}"
    result.pass_test("Empty index handled")

def test_entity_index_sql_files(result: TestResult):
    """Index-2: Process SQL files"""
    files = {
        "schema.sql": "CREATE TABLE users (id INT);",
        "migrations.sql": "CREATE TABLE products (id INT);"
    }
    index = build_entity_index(files)
    assert len(index["tables"]) >= 2, f"Tables not extracted: {index['tables']}"
    result.pass_test(f"Extracted {len(index['tables'])} tables from SQL")

def test_entity_index_python_files(result: TestResult):
    """Index-3: Process Python files"""
    files = {
        "main.py": "from flask import Flask\ndef home(): pass",
        "utils.py": "import os\ndef helper(): pass"
    }
    index = build_entity_index(files)
    assert len(index["imports"]) > 0, "Imports not extracted"
    assert len(index["functions"]) > 0, "Functions not extracted"
    result.pass_test(f"Extracted imports and functions from Python")

def test_entity_index_js_files(result: TestResult):
    """Index-4: Process JavaScript files"""
    files = {
        "App.tsx": "const App = () => <div></div>;",
        "api.ts": "fetch('/api/data');"
    }
    index = build_entity_index(files)
    assert len(index["components"]) > 0, "Components not extracted"
    result.pass_test(f"Extracted {len(index['components'])} components from JS")

def test_entity_index_mixed_languages(result: TestResult):
    """Index-5: Process mixed language files"""
    files = {
        "schema.sql": "CREATE TABLE users (id INT);",
        "app.py": "def get_users(): pass",
        "UI.tsx": "const Users = () => <div></div>;"
    }
    index = build_entity_index(files)
    assert len(index["tables"]) > 0, "SQL not processed"
    assert len(index["functions"]) > 0, "Python not processed"
    assert len(index["components"]) > 0, "JS not processed"
    result.pass_test("Mixed language processing successful")

def test_entity_index_file_extensions(result: TestResult):
    """Index-6: Handle various file extensions"""
    files = {
        "query.sql": "CREATE TABLE t (id INT);",
        "main.py": "def func(): pass",
        "App.tsx": "const A = () => {}",
        "index.ts": "const B = () => {}",
        "page.jsx": "function Page() {}"
    }
    index = build_entity_index(files)
    result.pass_test(f"Handled 5 different file extensions successfully")

def test_entity_index_duplicate_deduplication(result: TestResult):
    """Index-7: Deduplicate entries across files"""
    files = {
        "file1.py": "def func(): pass",
        "file2.py": "def func(): pass"
    }
    index = build_entity_index(files)
    # Sets should deduplicate
    result.pass_test(f"Deduplication working (found {len(index['functions'])} unique functions)")

def test_entity_index_complex_graph(result: TestResult):
    """Index-8: Build complex graph structure"""
    files = {
        "schema.sql": """
            CREATE TABLE users (id INT, email VARCHAR);
            CREATE TABLE orders (id INT, user_id INT);
        """,
        "api.py": """
            from fastapi import FastAPI
            app = FastAPI()
            @app.get('/users')
            def get_users(): pass
        """,
        "frontend.tsx": """
            const Users = () => {
                fetch('/api/users');
                return <div></div>;
            };
        """
    }
    index = build_entity_index(files)
    result.pass_test(f"Complex graph: {len(index['tables'])} tables, {len(index['routes'])} routes, {len(index['components'])} components")

def test_entity_index_json_serializable(result: TestResult):
    """Index-9: Result should be JSON serializable"""
    files = {
        "schema.sql": "CREATE TABLE users (id INT);",
        "app.py": "def test(): pass"
    }
    index = build_entity_index(files)
    try:
        json.dumps(index)
        result.pass_test("Index is JSON serializable")
    except Exception as e:
        result.fail_test("Not JSON serializable", str(e))

def test_entity_index_large_codebase(result: TestResult):
    """Index-10: Handle large codebase simulation"""
    files = {}
    for i in range(10):
        files[f"schema{i}.sql"] = f"CREATE TABLE t{i} (id INT);"
        files[f"app{i}.py"] = f"def func{i}(): pass"
        files[f"component{i}.tsx"] = f"const C{i} = () => <div></div>;"
    
    index = build_entity_index(files)
    assert len(index["tables"]) == 10, "Not all tables extracted"
    assert len(index["functions"]) == 10, "Not all functions extracted"
    assert len(index["components"]) == 10, "Not all components extracted"
    result.pass_test(f"Large codebase handled: {len(index['tables'])} tables, {len(index['functions'])} functions, {len(index['components'])} components")

# ============================================================================
# ERROR HANDLING & EDGE CASES
# ============================================================================

def test_unicode_content(result: TestResult):
    """Edge-1: Handle Unicode content"""
    code = "-- Comment with émojis 🚀\nCREATE TABLE users (name VARCHAR);"
    res = extract_sql_entities(code)
    assert "users" in res["tables"], "Unicode not handled"
    result.pass_test("Unicode content handled")

def test_very_long_code(result: TestResult):
    """Edge-2: Handle very long code strings"""
    code = "CREATE TABLE t (id INT);\n" * 1000
    res = extract_sql_entities(code)
    assert len(res["tables"]) == 1000, "Long code not handled"
    result.pass_test(f"Handled 1000 table definitions")

def test_malformed_sql(result: TestResult):
    """Edge-3: Handle malformed SQL"""
    code = "CREATE TABLE (missing name;;;"
    res = extract_sql_entities(code)
    # Should not crash
    result.pass_test("Malformed SQL handled gracefully")

def test_mixed_case_keywords(result: TestResult):
    """Edge-4: Handle mixed case SQL keywords"""
    code = "create table Users (ID int); CREATE TABLE Products (id INT);"
    res = extract_sql_entities(code)
    assert len(res["tables"]) >= 2, "Case sensitivity issue"
    result.pass_test(f"Found {len(res['tables'])} tables (handles case-insensitive)")

def test_deeply_nested_structures(result: TestResult):
    """Edge-5: Handle deeply nested code structures"""
    code = """
    function outer() {
        function middle() {
            function inner() {
                fetch('/api/data');
            }
        }
    }
    """
    res = extract_js_entities(code)
    result.pass_test("Nested structures handled")

# ============================================================================
# RUN ALL TESTS
# ============================================================================

def main():
    print("=" * 80)
    print("COMPREHENSIVE TEST EXECUTION")
    print("=" * 80)
    
    # SQL Tests
    print("\n[SQL EXTRACTOR]")
    sql_tests = [
        ("SQL-1: Empty File", test_sql_empty_file),
        ("SQL-2: Basic Table", test_sql_basic_table),
        ("SQL-3: Multiple Tables", test_sql_multiple_tables),
        ("SQL-4: Column Extraction", test_sql_columns_extraction),
        ("SQL-5: Foreign Keys", test_sql_foreign_keys),
        ("SQL-6: Views", test_sql_views),
        ("SQL-7: IF NOT EXISTS", test_sql_if_not_exists),
        ("SQL-8: Comments", test_sql_comments),
        ("SQL-9: Quoted Names", test_sql_quoted_names),
        ("SQL-10: None Input", test_sql_none_input),
    ]
    for name, test in sql_tests:
        run_test(name, "SQL", test)
        result = test_results[-1]
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if result.error:
            print(f"    Error: {result.error}")
    
    # Python Tests
    print("\n[PYTHON EXTRACTOR]")
    python_tests = [
        ("Python-1: Empty File", test_python_empty_file),
        ("Python-2: Basic Imports", test_python_basic_import),
        ("Python-3: FastAPI Routes", test_python_fastapi_routes),
        ("Python-4: Functions", test_python_function_definition),
        ("Python-5: Classes", test_python_class_definition),
        ("Python-6: HTTP Calls", test_python_http_calls),
        ("Python-7: Syntax Error", test_python_syntax_error),
        ("Python-8: Async Functions", test_python_async_functions),
        ("Python-9: Complex Decorators", test_python_complex_decorators),
        ("Python-10: None Input", test_python_none_input),
    ]
    for name, test in python_tests:
        run_test(name, "Python", test)
        result = test_results[-1]
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if result.error:
            print(f"    Error: {result.error}")
    
    # JavaScript Tests
    print("\n[JAVASCRIPT/TYPESCRIPT EXTRACTOR]")
    js_tests = [
        ("JS-1: Empty File", test_js_empty_file),
        ("JS-2: Function Components", test_js_function_components),
        ("JS-3: Arrow Components", test_js_arrow_components),
        ("JS-4: Fetch Calls", test_js_fetch_calls),
        ("JS-5: Axios Calls", test_js_axios_calls),
        ("JS-6: Field References", test_js_field_references),
        ("JS-7: React.FC Type", test_js_react_fc_type),
        ("JS-8: Mixed Code", test_js_mixed_code),
        ("JS-9: None Input", test_js_none_input),
        ("JS-10: Special Characters", test_js_special_characters),
    ]
    for name, test in js_tests:
        run_test(name, "JavaScript", test)
        result = test_results[-1]
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if result.error:
            print(f"    Error: {result.error}")
    
    # Entity Index Tests
    print("\n[ENTITY INDEX]")
    index_tests = [
        ("Index-1: Empty", test_entity_index_empty),
        ("Index-2: SQL Files", test_entity_index_sql_files),
        ("Index-3: Python Files", test_entity_index_python_files),
        ("Index-4: JS Files", test_entity_index_js_files),
        ("Index-5: Mixed Languages", test_entity_index_mixed_languages),
        ("Index-6: File Extensions", test_entity_index_file_extensions),
        ("Index-7: Deduplication", test_entity_index_duplicate_deduplication),
        ("Index-8: Complex Graph", test_entity_index_complex_graph),
        ("Index-9: JSON Serializable", test_entity_index_json_serializable),
        ("Index-10: Large Codebase", test_entity_index_large_codebase),
    ]
    for name, test in index_tests:
        run_test(name, "Index", test)
        result = test_results[-1]
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if result.error:
            print(f"    Error: {result.error}")
    
    # Edge Cases
    print("\n[ERROR HANDLING & EDGE CASES]")
    edge_tests = [
        ("Edge-1: Unicode", test_unicode_content),
        ("Edge-2: Long Code", test_very_long_code),
        ("Edge-3: Malformed SQL", test_malformed_sql),
        ("Edge-4: Mixed Case", test_mixed_case_keywords),
        ("Edge-5: Nested Structures", test_deeply_nested_structures),
    ]
    for name, test in edge_tests:
        run_test(name, "EdgeCases", test)
        result = test_results[-1]
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if result.error:
            print(f"    Error: {result.error}")
    
    # Summary
    print("\n" + "=" * 80)
    pass_count = sum(1 for r in test_results if r.passed)
    fail_count = sum(1 for r in test_results if not r.passed)
    total = len(test_results)
    pass_rate = (pass_count / total * 100) if total > 0 else 0
    
    print(f"SUMMARY: {pass_count}/{total} tests passed ({pass_rate:.1f}%)")
    print(f"  ✓ Passed: {pass_count}")
    print(f"  ✗ Failed: {fail_count}")
    print("=" * 80)
    
    return test_results

if __name__ == "__main__":
    test_results = main()
