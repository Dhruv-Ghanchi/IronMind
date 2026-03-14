import os
import zipfile
import tempfile
import shutil
from backend.ingestion.zip_handler import extract_zip
from backend.ingestion.file_scanner import scan_directory

def test_ingestion():
    # 1. Create a temporary directory structure
    test_dir = tempfile.mkdtemp()
    
    # 2. Add some dummy files
    os.makedirs(os.path.join(test_dir, "src", "components"))
    os.makedirs(os.path.join(test_dir, "node_modules", "react"))
    os.makedirs(os.path.join(test_dir, ".git"))
    
    with open(os.path.join(test_dir, "src", "main.py"), "w") as f:
        f.write("print('hello backend')")
        
    with open(os.path.join(test_dir, "src", "components", "App.tsx"), "w") as f:
        f.write("console.log('hello frontend')")
        
    with open(os.path.join(test_dir, "node_modules", "react", "index.js"), "w") as f:
        f.write("console.log('ignored')")
        
    with open(os.path.join(test_dir, ".git", "config"), "w") as f:
        f.write("ignored")
        
    with open(os.path.join(test_dir, "README.md"), "w") as f:
        f.write("# skip me")
        
    # 3. Create a test zip file
    zip_path = os.path.join(tempfile.gettempdir(), "test_repo.zip")
    with zipfile.ZipFile(zip_path, 'w') as map_zip:
        for root, _, files in os.walk(test_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, test_dir)
                map_zip.write(abs_path, rel_path)
                
    # 4. Test extraction
    extracted_path = extract_zip(zip_path)
    assert os.path.exists(extracted_path)
    
    # 5. Test scanning
    results = scan_directory(extracted_path)
    print("Scan Results:", results)
    
    # Assertions
    # Supported: src/main.py, src/components/App.tsx (2)
    # Skipped: README.md (1)
    # node_modules and .git should be filtered out entirely without adding to scanned or skipped file count
    assert results['supported'] == 2
    
    # Files array should contain the two supported files
    assert len(results['files_to_parse']) == 2
    assert any('main.py' in p for p in results['files_to_parse'])
    assert any('App.tsx' in p for p in results['files_to_parse'])

    print("Ingestion test passed!")
    
    # Cleanup
    shutil.rmtree(test_dir)
    os.remove(zip_path)
    shutil.rmtree(extracted_path)

if __name__ == "__main__":
    test_ingestion()
