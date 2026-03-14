import unittest
from extraction.js_extractor import extract_js_entities

class TestJSExtractor(unittest.TestCase):
    def test_js_extraction(self):
        code = '''
import React from 'react';

const ProfilePage = () => {
    const fetchProfile = async () => {
        const response = await fetch('/profile');
        const data = await response.json();
        // field_refs matching is heuristic
        console.log(data.user.email);
    };

    return <div>Profile</div>;
};

export default ProfilePage;
        '''
        index = extract_js_entities(code)
        
        self.assertIn("ProfilePage", index["components"])
        self.assertIn("fetch /profile", index["api_calls"])

if __name__ == '__main__':
    unittest.main()
