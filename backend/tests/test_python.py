import unittest
from backend.extraction.python_extractor import extract_python_entities

class TestPythonExtractor(unittest.TestCase):
    def test_python_extraction(self):
        code = '''
from fastapi import FastAPI
import requests
import httpx
import aiohttp

app = FastAPI()

class UserService:
    def get_email(self, user):
        # field_refs matching is heuristic; if an edge is missing, the variable name likely doesn't match the table name
        return user.email

@app.get('/profile')
def get_profile():
    res1 = requests.get('http://auth/verify')
    res2 = httpx.post('http://auth/verify')
    return {"status": "ok"}
        '''
        index = extract_python_entities(code)
        
        self.assertIn("fastapi.FastAPI", index["imports"])
        self.assertIn("requests", index["imports"])
        self.assertIn("aiohttp", index["imports"])
        self.assertIn("UserService", index["classes"])
        self.assertIn("get_email", index["functions"])
        self.assertIn("users.email", index["field_refs"])  # Forced users.email via heuristic
        self.assertIn("GET /profile", index["routes"])
        self.assertIn("requests.get http://auth/verify", index["http_calls"])
        self.assertIn("httpx.post http://auth/verify", index["http_calls"])

if __name__ == '__main__':
    unittest.main()
