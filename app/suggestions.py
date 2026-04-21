from dataclasses import dataclass
from typing import List, Optional

@dataclass
class RuleSuggestion:
    """
    Represents a suggested alert rule for a user.
    """
    type: str  # "related_category", "related_arrondissement", "related_person"
    current_value: str
    suggested_value: str
    reason: str
    confidence: float  # 0.0-1.0

def suggest_alert_rules(
    user_id: int,
    existing_keywords: List[str],
    existing_categories: List[str],
    existing_arrondissements: List[int],
) -> List[RuleSuggestion]:
    """
    Suggest new alert rules based on existing ones.
    
    Rules:
    1. If user watches "subvention sport" → suggest "subvention culture"
    2. If user watches "subvention" → suggest other categories: "appointment", "contract", "urbanism"
    3. If user watches arrondissement X → suggest adjacent arrondissements (X-1, X+1)
    4. If user watches a person's name → suggest searching that person's name across ALL categories
    5. If user watches "marché public" → suggest "subvention" (and vice versa)
    
    Only suggest if confidence > 0.3.
    Never suggest duplicates (check against existing).
    """
    suggestions: List[RuleSuggestion] = []
    
    # Helper to check for duplicates
    def is_duplicate(suggestion: RuleSuggestion) -> bool:
        for existing in suggestions:
            if (existing.type == suggestion.type and 
                existing.current_value == suggestion.current_value and 
                existing.suggested_value == suggestion.suggested_value):
                return True
        return False

    # --- Rule 1: Subvention Sport -> Subvention Culture ---
    if "subvention sport" in existing_keywords:
        suggestion = RuleSuggestion(
            type="related_category",
            current_value="subvention sport",
            suggested_value="subvention culture",
            reason="Related funding type.",
            confidence=0.9
        )
        if not is_duplicate(suggestion):
            suggestions.append(suggestion)

    # --- Rule 2: Subvention -> Other Categories ---
    if "subvention" in existing_keywords:
        other_categories = ["appointment", "contract", "urbanism"]
        for cat in other_categories:
            suggestion = RuleSuggestion(
                type="related_category",
                current_value="subvention",
                suggested_value=cat,
                reason=f"Related to general funding type: {cat}.",
                confidence=0.8
            )
            if not is_duplicate(suggestion):
                suggestions.append(suggestion)

    # --- Rule 3: Arrondissement Adjacency ---
    for arr in existing_arrondissements:
        # Suggest X-1
        adj_minus = arr - 1
        if adj_minus >= 1 and adj_minus <= 20: # Assuming 1-20 range
            suggestion = RuleSuggestion(
                type="related_arrondissement",
                current_value=str(arr),
                suggested_value=str(adj_minus),
                reason=f"Adjacent arrondissement (X-1).",
                confidence=0.75
            )
            if not is_duplicate(suggestion):
                suggestions.append(suggestion)
        
        # Suggest X+1
        adj_plus = arr + 1
        if adj_plus >= 1 and adj_plus <= 20:
            suggestion = RuleSuggestion(
                type="related_arrondissement",
                current_value=str(arr),
                suggested_value=str(adj_plus),
                reason=f"Adjacent arrondissement (X+1).",
                confidence=0.75
            )
            if not is_duplicate(suggestion):
                suggestions.append(suggestion)

    # --- Rule 4: Person Name Search ---
    # Assuming any keyword that looks like a name (e.g., capitalized, not a common noun)
    # For simplicity, we'll check if any existing keyword is a single word and capitalized.
    potential_names = [k for k in existing_keywords if k and k[0].isupper() and len(k.split()) == 1]
    for name in potential_names:
        suggestion = RuleSuggestion(
            type="related_person",
            current_value=name,
            suggested_value=f"Search {name} across all categories",
            reason=f"Expand search scope for {name}.",
            confidence=0.95
        )
        if not is_duplicate(suggestion):
            suggestions.append(suggestion)

    # --- Rule 5: Marché Public <-> Subvention ---
    if "marché public" in existing_keywords:
        # Suggest Subvention
        suggestion_to_sub = RuleSuggestion(
            type="related_category",
            current_value="marché public",
            suggested_value="subvention",
            reason="Often linked to public funding.",
            confidence=0.85
        )
        if not is_duplicate(suggestion_to_sub):
            suggestions.append(suggestion_to_sub)
        
        # Suggest Marché Public (if subvention is already watched, but we check this here for completeness)
        suggestion_from_sub = RuleSuggestion(
            type="related_category",
            current_value="subvention",
            suggested_value="marché public",
            reason="Often linked to public funding.",
            confidence=0.85
        )
        if not is_duplicate(suggestion_from_sub):
            suggestions.append(suggestion_from_sub)

    # Final filter: Ensure confidence > 0.3 (already handled in individual rules, but good practice)
    return [s for s in suggestions if s.confidence > 0.3]

# Example usage (optional, but helpful for quick testing)
if __name__ == '__main__':
    test_keywords = ["subvention sport", "marché public", "Mme Dupont", "arrondissement 5"]
    test_categories = ["urbanism", "culture"]
    test_arrondissements = [5]
    
    suggestions = suggest_alert_rules(123, test_keywords, test_categories, test_arrondissements)
    
    print("--- Suggested Rules ---")
    for s in suggestions:
        print(f"[{s.type}] {s.current_value} -> {s.suggested_value} (Conf: {s.confidence:.2f}) - Reason: {s.reason}")
    print(f"Total suggestions: {len(suggestions)}")