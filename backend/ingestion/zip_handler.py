import tempfile
import zipfile
import os
import uuid
import shutil
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

FILE_READ_TIMEOUT_SECONDS = 2  # PRD §8 — parse timeout per file: 2s


def _read_file(abs_path: str) -> str:
    """Read a single file. Called in a thread so it can be timed out."""
    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_zip(upload_file_path: str) -> str:
    """
    Extracts a ZIP file to a temporary directory.
    Returns the path to the extracted repository folder.

    Raises ValueError (not raw zipfile exceptions) so callers get a clean,
    handleable error instead of a 500 crash.
    """
    extracted_dir = tempfile.mkdtemp(prefix=f"repo_upload_{uuid.uuid4().hex}_")

    try:
        with zipfile.ZipFile(upload_file_path, "r") as zip_ref:
            zip_ref.extractall(extracted_dir)
    except zipfile.BadZipFile:
        shutil.rmtree(extracted_dir, ignore_errors=True)
        raise ValueError("Uploaded file is not a valid ZIP archive.")
    except Exception as e:
        shutil.rmtree(extracted_dir, ignore_errors=True)
        raise ValueError(f"Failed to extract ZIP: {str(e)}")

    return extracted_dir


def read_files_to_dict(repo_path: str, files_to_parse: list[str]) -> dict[str, str]:
    """
    Reads the content of each file in files_to_parse and returns a dict:
        { relative_path: source_code_string }

    This is the exact shape expected by Dev 2's entity_index.build_entity_index().

    PRD §8 compliance:
    - Per-file read timeout: 2 seconds. Files that exceed this are skipped gracefully.
    - Files that are unreadable (OS errors, binary) are silently skipped.

    After reading, the entire extracted repo_path is deleted to prevent disk leaks.
    """
    code_map: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=1) as executor:
        for rel_path in files_to_parse:
            abs_path = os.path.join(repo_path, rel_path)
            try:
                future = executor.submit(_read_file, abs_path)
                content = future.result(timeout=FILE_READ_TIMEOUT_SECONDS)
                code_map[rel_path] = content
            except FutureTimeoutError:
                pass
            except OSError:
                pass

    # Clean up the entire extracted temp directory now that we hold the content
    shutil.rmtree(repo_path, ignore_errors=True)

    return code_map

