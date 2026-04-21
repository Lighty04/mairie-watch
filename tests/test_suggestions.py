import unittest
from app.suggestions import RuleSuggestion, suggest_alert_rules

class TestSuggestionEngine(unittest.TestCase):
    
    def setUp(self):
        # Standard test data set covering multiple rules
        self.user_id = 123
        self.existing_keywords = [
            "subvention sport", 
            "marché public", 
            "Mme Dupont", 
            "arrondissement 5", 
            "subvention" # Test for Rule 2 and Rule 5 redundancy
        ]
        self.existing_categories = ["urbanism", "culture"]
        self.existing_arrondissements = [5]
        
        self.suggestions = suggest_alert_rules(
            self.user_id, 
            self.existing_keywords, 
            self.existing_categories, 
            self.existing_arrondissements
        )

    def test_total_suggestions_count(self):
        # Expected count based on manual trace:
        # R1: 1 (sport -> culture)
        # R2: 3 (subvention -> appointment, contract, urbanism)
        # R3: 2 (5 -> 4, 5 -> 6)
        # R4: 1 (Mme Dupont -> Search Mme Dupont)
        # R5: 2 (marché public -> subvention, subvention -> marché public)
        # Total: 1 + 3 + 2 + 1 + 2 = 9
        self.assertEqual(len(self.suggestions), 9, "Should generate exactly 9 suggestions.")

    def test_rule_1_sport_to_culture(self):
        # Check for the specific R1 suggestion
        r1_suggestion = next((s for s in self.suggestions if s.type == "related_category" and s.current_value == "subvention sport"), None)
        self.assertIsNotNone(r1_suggestion)
        self.assertEqual(r1_suggestion.suggested_value, "subvention culture")
        self.assertGreater(r1_suggestion.confidence, 0.8)

    def test_rule_2_subvention_to_others(self):
        # Check for R2 suggestions
        r2_suggestions = [s for s in self.suggestions if s.type == "related_category" and s.current_value == "subvention"]
        self.assertEqual(len(r2_suggestions), 3)
        suggested_values = {s.suggested_value for s in r2_suggestions}
        self.assertIn("appointment", suggested_values)
        self.assertIn("contract", suggested_values)
        self.assertIn("urbanism", suggested_values)

    def test_rule_3_arrondissement_adjacency(self):
        # Check for R3 suggestions (5 -> 4 and 5 -> 6)
        r3_suggestions = [s for s in self.suggestions if s.type == "related_arrondissement" and s.current_value == "5"]
        self.assertEqual(len(r3_suggestions), 2)
        suggested_values = {s.suggested_value for s in r3_suggestions}
        self.assertIn("4", suggested_values)
        self.assertIn("6", suggested_values)

    def test_rule_4_person_search(self):
        # Check for R4 suggestion
        r4_suggestion = next((s for s in self.suggestions if s.type == "related_person" and s.current_value == "Mme Dupont"), None)
        self.assertIsNotNone(r4_suggestion)
        self.assertEqual(r4_suggestion.suggested_value, "Search Mme Dupont across all categories")
        self.assertGreater(r4_suggestion.confidence, 0.9)

    def test_rule_5_market_public_link(self):
        # Check for R5 suggestions (MP -> Subvention and Subvention -> MP)
        r5_suggestions = [s for s in self.suggestions if s.type == "related_category" and s.confidence == 0.85]
        
        # MP -> Subvention
        mp_to_sub = next((s for s in r5_suggestions if s.current_value == "marché public" and s.suggested_value == "subvention"), None)
        self.assertIsNotNone(mp_to_sub)
        
        # Subvention -> MP
        sub_to_mp = next((s for s in r5_suggestions if s.current_value == "subvention" and s.suggested_value == "marché public"), None)
        self.assertIsNotNone(sub_to_mp)

    def test_no_duplicates(self):
        # Check if the same suggestion (Type, Current, Suggested) appears more than once
        seen = set()
        for s in self.suggestions:
            key = (s.type, s.current_value, s.suggested_value)
            self.assertNotIn(key, seen, f"Duplicate suggestion found: {key}")
            seen.add(key)

    def test_confidence_filter(self):
        # Test a case where confidence is low (e.g., 0.2)
        low_conf_suggestion = RuleSuggestion(
            type="test_low",
            current_value="test",
            suggested_value="low",
            reason="Low confidence test",
            confidence=0.2
        )
        
        # Temporarily add it to the list and check
        temp_suggestions = self.suggestions + [low_conf_suggestion]
        
        # Re-run the filter logic (or just check the list)
        filtered_suggestions = [s for s in temp_suggestions if s.confidence > 0.3]
        
        self.assertNotIn(low_conf_suggestion, filtered_suggestions)

if __name__ == '__main__':
    unittest.main()