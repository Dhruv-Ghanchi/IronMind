import unittest
from extraction.sql_extractor import extract_sql_entities

class TestSQLExtractor(unittest.TestCase):
    def test_sql_extraction(self):
        code = '''
            CREATE TABLE IF NOT EXISTS users (
                id INT PRIMARY KEY,
                email VARCHAR(255) UNIQUE,
                profile_id INT,
                FOREIGN KEY (profile_id) REFERENCES profiles(id)
            );
            
            CREATE VIEW active_users AS SELECT * FROM users;
        '''
        index = extract_sql_entities(code)
        
        self.assertIn("users", index["tables"])
        self.assertIn("users.email", index["columns"])
        self.assertIn("profiles.id", index["foreign_keys"])
        self.assertIn("active_users", index["views"])

if __name__ == '__main__':
    unittest.main()
