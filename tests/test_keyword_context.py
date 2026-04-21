import unittest
from app.advanced_alerts import extract_keyword_context

class TestKeywordContext(unittest.TestCase):

    def setUp(self):
        # Standard text with clear sentence boundaries
        self.standard_text = (
            "Le maire a annoncé hier une grande nouvelle. Les associations culturelles sont en fête ! "
            "Ce week-end, nous célébrerons la ville. La subvention pour le sport est importante. "
            "Nous attendons des milliers de visiteurs. Le budget est serré, mais l'ambiance est au rendez-vous. "
            "Il faut que les citoyens participent. C'est une opportunité unique. Quel est le thème principal ? "
            "C'est la culture, bien sûr."
        )
        self.keyword = "culture"

    def test_standard_extraction(self):
        """Test extraction when keyword is in the middle and context is full."""
        results = extract_keyword_context(self.standard_text, self.keyword)
        
        self.assertEqual(len(results), 1, "Should find exactly one occurrence.")
        result = results[0]
        
        self.assertEqual(result['keyword'], self.keyword)
        self.assertIn(self.keyword, result['match'])
        self.assertIsInstance(result['match'], str)
        self.assertIn("<mark>culture</mark>", result['match'])
        
        # Check context length (should be 2 before, 2 after)
        self.assertIn("Les associations culturelles sont en fête !", result['before'])
        self.assertIn("La subvention pour le sport est importante.", result['after'])
        
        # Check position
        self.assertTrue(result['position'] > 50 and result['position'] < 150)

    def test_edge_case_start(self):
        """Test extraction when keyword is in the first sentence (fewer than 2 before)."""
        text = "Culture est le mot clé. Les citoyens sont heureux ! Le maire est fier. C'est génial."
        keyword = "Culture"
        results = extract_keyword_context(text, keyword)
        
        self.assertEqual(len(results), 1)
        result = results[0]
        
        # Should only have 0 before
        self.assertNotIn("...", result['before'])
        self.assertIn("Culture est le mot clé.", result['match'])
        
        # Should have 2 after
        self.assertIn("Les citoyens sont heureux !", result['after'])
        self.assertIn("Le maire est fier.", result['after'])

    def test_edge_case_end(self):
        """Test extraction when keyword is in the last sentence (fewer than 2 after)."""
        text = "Le sport est vital. Les associations sont là. C'est la culture. Quel est le thème ?"
        keyword = "culture"
        results = extract_keyword_context(text, keyword)
        
        self.assertEqual(len(results), 1)
        result = results[0]
        
        # Should have 2 before
        self.assertIn("Le sport est vital.", result['before'])
        self.assertIn("Les associations sont là.", result['before'])
        
        # Should only have 1 after
        self.assertIn("Quel est le thème ?", result['after'])
        self.assertNotIn("...", result['after'])

    def test_multiple_occurrences(self):
        """Test that only the first 3 occurrences are returned."""
        text = (
            "La culture est riche. C'est une grande culture. J'aime la culture. "
            "Mais la culture du sport est aussi importante. Une autre culture. "
            "Enfin, la culture locale est unique. Une septième culture."
        )
        keyword = "culture"
        results = extract_keyword_context(text, keyword, max_occurrences=3)
        
        self.assertEqual(len(results), 3)
        
        # Check that the 3rd result is indeed the third occurrence
        self.assertIn("J'aime la culture.", results[2]['match'])
        
    def test_french_punctuation_and_case(self):
        """Test sentence splitting and matching with French characters and mixed case."""
        text = "L'art est beau. La culture française est magnifique! Le maire a dit : 'C'est génial?'"
        keyword = "culture"
        results = extract_keyword_context(text, keyword)
        
        self.assertEqual(len(results), 1)
        result = results[0]
        
        # Check match highlighting (should handle case)
        self.assertIn("<mark>culture</mark>", result['match'])
        
        # Check sentence splitting (should handle '!' and '?')
        self.assertIn("L'art est beau.", result['before'])
        self.assertIn("La culture française est magnifique!", result['match'])
        self.assertIn("Le maire a dit : 'C'est génial?'", result['after'])

if __name__ == '__main__':
    unittest.main()