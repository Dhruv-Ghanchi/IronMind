import os
import sys

def diag():
    print("--- Polyglot Analyzer Diagnostic ---")
    print(f"OS: {sys.platform}")
    print(f"Python: {sys.version}")
    print(f"CWD: {os.getcwd()}")
    
    # Check critical files
    files = [
        "backend/main.py",
        "backend/database.py",
        "backend/graph/node_builder.py",
        "backend/impact/traversal.py"
    ]
    
    for f in files:
        status = "✅" if os.path.exists(f) else "❌"
        print(f"{f}: {status}")

if __name__ == "__main__":
    diag()
