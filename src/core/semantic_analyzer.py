#!/usr/bin/env python3
"""
Semantic Analyzer for BrowserControL01
======================================

Provides heuristic-based analysis to identify the semantic role of 
ExtractedElement objects.
"""

import re # Import re for regular expressions
from typing import List, Optional, Dict, Any
from .structures import ExtractedElement, ElementProperties
# Assuming logger is available or will be passed in. For now, direct import for type hinting.
from utils.logger import StealthLogger 


class SemanticAnalyzer:
    """
    Analyzes ExtractedElement objects to determine their semantic role
    and assign confidence scores.
    """
    def __init__(self, logger: Optional[StealthLogger] = None):
        """
        Initializes the SemanticAnalyzer.

        Args:
            logger: An optional logger instance.
        """
        self.log = logger or StealthLogger(name="SemanticAnalyzer")
        # Define common regex patterns
        self.patterns = {
            "price": re.compile(r"""^\$?     # Optional leading dollar sign
                \d{1,3} # 1 to 3 digits for whole part
                (?:[,.]\d{3})* # Optional thousands separators (comma or period)
                (?:[.]\d{2})?  # Optional decimal part (period followed by 2 digits)
                \$?$          # Optional trailing dollar sign
            """, re.VERBOSE),
            "add_to_cart": re.compile(r"add to (cart|bag)|buy now|add to basket", re.IGNORECASE),
            "rating": re.compile(r"(\d(?:[.,]\d+)?)\s*(?:out of|of)\s*5(?:\s*stars)?", re.IGNORECASE), # e.g., "4.5 out of 5 stars"
            "review_count": re.compile(r"\(?(\d{1,3}(?:[,.]\d{3})*|\d+)\)?(?:\s*reviews|\s*ratings)?", re.IGNORECASE) # e.g., "(1,234) reviews"
        }
        self.log.info("SemanticAnalyzer initialized with regex patterns.")

    def _set_semantic_role(self, element: ExtractedElement, role: str, confidence: float, reason: str, overwrite_lower_confidence: bool = True):
        """Helper to set semantic role if confidence is high enough or overwriting is allowed."""
        if overwrite_lower_confidence and element.semantic_role is not None:
            if element.role_confidence is not None and confidence <= element.role_confidence:
                self.log.debug(f"Skipping role '{role}' for '{element.name}'; existing role '{element.semantic_role}' has confidence {element.role_confidence:.2f} >= new {confidence:.2f}.")
                return # Don't overwrite with lower or equal confidence

        element.semantic_role = role
        element.role_confidence = confidence
        note = f"Semantic role '{role}' (Confidence: {confidence:.2f}) inferred from: {reason}."
        if note not in element.notes: # Avoid duplicate notes if re-analyzed
            element.notes.append(note)
        self.log.debug(f"Assigned role '{role}' to '{element.name}' with confidence {confidence:.2f} ({reason}).")


    def analyze_element(self, element: ExtractedElement) -> ExtractedElement:
        """
        Analyzes a single ExtractedElement to determine its semantic role.
        Applies a series of heuristic checks, prioritizing more specific ones.

        Args:
            element: The ExtractedElement to analyze.

        Returns:
            The same ExtractedElement, potentially updated with semantic_role and role_confidence.
        """
        self.log.debug(f"Analyzing element: {element.name} (Value: {str(element.value)[:50]}...)")

        # Heuristic checks - order can matter. More specific/reliable checks first.

        # 1. Check text content using regex (high confidence if matched)
        if isinstance(element.value, str) and element.value.strip():
            text_value = element.value.strip()
            if self.patterns["add_to_cart"].search(text_value):
                self._set_semantic_role(element, "add_to_cart_button", 0.85, "text content matching 'add to cart' pattern")
            elif self.patterns["price"].fullmatch(text_value.replace(',', '')): # Fullmatch for price, remove comma for robustness
                 self._set_semantic_role(element, "product_price", 0.80, "text content matching price pattern")
            elif self.patterns["rating"].search(text_value):
                self._set_semantic_role(element, "product_rating_text", 0.75, "text content matching rating pattern")
            elif self.patterns["review_count"].search(text_value):
                self._set_semantic_role(element, "product_review_count", 0.75, "text content matching review count pattern")
        
        # 2. Check ARIA roles and specific attributes (medium-high confidence)
        if element.properties and element.properties.attributes:
            attributes = element.properties.attributes
            aria_role = attributes.get('role')
            if aria_role:
                if "button" in aria_role.lower():
                    self._set_semantic_role(element, "button_aria", 0.70, f"ARIA role '{aria_role}'")
                elif "link" in aria_role.lower():
                    self._set_semantic_role(element, "link_aria", 0.65, f"ARIA role '{aria_role}'")
                elif "heading" in aria_role.lower():
                     self._set_semantic_role(element, "heading_aria", 0.65, f"ARIA role '{aria_role}'")
                # Add more ARIA role checks as needed

            # Check common identifying attributes
            for attr_key in ['data-testid', 'data-cy', 'name', 'id']:
                attr_val = attributes.get(attr_key)
                if attr_val:
                    attr_val_lower = attr_val.lower()
                    if "price" in attr_val_lower:
                        self._set_semantic_role(element, "product_price_attr", 0.78, f"attribute '{attr_key}=\"{attr_val}\"' containing 'price'")
                    elif any(kw in attr_val_lower for kw in ["cart", "basket", "buy", "purchase"]):
                        self._set_semantic_role(element, "action_button_attr", 0.76, f"attribute '{attr_key}=\"{attr_val}\"' suggesting cart/buy action")
                    elif "title" in attr_val_lower or "heading" in attr_val_lower or "name" in attr_val_lower and "product" in attr_val_lower : # be more specific for title
                         self._set_semantic_role(element, "product_title_attr", 0.72, f"attribute '{attr_key}=\"{attr_val}\"' suggesting title/name")
                    # Add more attribute keyword checks

        # 3. Check element tag name (medium-low confidence, more generic)
        if element.properties and element.properties.tag_name:
            tag_name = element.properties.tag_name.lower()
            if tag_name == "button":
                self._set_semantic_role(element, "generic_button_tag", 0.60, "tag name 'button'")
            elif tag_name in ["h1", "h2", "h3", "h4"]:
                self._set_semantic_role(element, "heading_tag", 0.55, f"tag name '{tag_name}'")
            elif tag_name == "img":
                 self._set_semantic_role(element, "image_tag", 0.50, "tag name 'img'")
            elif tag_name == "a":
                 self._set_semantic_role(element, "link_tag", 0.50, "tag name 'a'")


        # 4. Check element name provided by extractor (lower confidence, often generic)
        # This was the original primary heuristic, now it's a fallback.
        # Let's make it less likely to overwrite more specific findings.
        if "price" in element.name.lower():
            self._set_semantic_role(element, "product_price_name", 0.45, f"element name '{element.name}' containing 'price'")
        elif "title" in element.name.lower() or "heading" in element.name.lower() or "name" in element.name.lower():
            self._set_semantic_role(element, "title_name_heuristic", 0.40, f"element name '{element.name}' suggesting title/name")


        if not element.semantic_role:
            self.log.debug(f"No specific semantic role identified for element: {element.name}")
        
        return element

    def analyze_elements(self, elements: List[ExtractedElement]) -> List[ExtractedElement]:
        """
        Analyzes a list of ExtractedElement objects.

        Args:
            elements: A list of ExtractedElement objects.

        Returns:
            The list of ExtractedElement objects, with semantic information potentially added.
        """
        self.log.info(f"Analyzing {len(elements)} elements for semantic roles.")
        return [self.analyze_element(element) for element in elements]

    def analyze_extracted_item_details(self, item_details_map: Dict[str, ExtractedElement]) -> Dict[str, ExtractedElement]:
        """
        Analyzes a dictionary of ExtractedElement objects, typically representing
        the details extracted for a single item (e.g., a product listing).

        Args:
            item_details_map: A dictionary where keys are logical names (e.g., 'title', 'price')
                              and values are ExtractedElement objects.
        
        Returns:
            The input dictionary, with its ExtractedElement values potentially updated.
        """
        self.log.debug(f"Analyzing item details map with {len(item_details_map)} entries.")
        for key, element in item_details_map.items():
            item_details_map[key] = self.analyze_element(element)
        return item_details_map

if __name__ == '__main__':
    # Example usage for testing
    from datetime import datetime

    class DummyLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def debug(self, msg): print(f"DEBUG: {msg}")

    logger = DummyLogger()
    analyzer = SemanticAnalyzer(logger=logger)

    print("\n--- Test 1: Price by text ---")
    price_text_elem = ExtractedElement( name="price1", value="$29.99", extraction_type="text", source_selector=".p", properties=ElementProperties(tag_name='span', text='$29.99'))
    analyzer.analyze_element(price_text_elem)
    print(f"Role: {price_text_elem.semantic_role}, Conf: {price_text_elem.role_confidence}, Notes: {price_text_elem.notes}")

    print("\n--- Test 2: Add to Cart by text ---")
    add_to_cart_elem = ExtractedElement(name="button1", value="Add to Basket", extraction_type="text", source_selector="button.add", properties=ElementProperties(tag_name='button', text='Add to Basket'))
    analyzer.analyze_element(add_to_cart_elem)
    print(f"Role: {add_to_cart_elem.semantic_role}, Conf: {add_to_cart_elem.role_confidence}, Notes: {add_to_cart_elem.notes}")

    print("\n--- Test 3: ARIA role button ---")
    aria_button_props = ElementProperties(tag_name='div', attributes={'role': 'button', 'aria-label': 'Submit form'})
    aria_button_elem = ExtractedElement(name="submit_btn_aria", value=None, extraction_type="element", source_selector="[role=button]", properties=aria_button_props)
    analyzer.analyze_element(aria_button_elem)
    print(f"Role: {aria_button_elem.semantic_role}, Conf: {aria_button_elem.role_confidence}, Notes: {aria_button_elem.notes}")

    print("\n--- Test 4: Attribute data-testid for price ---")
    attr_price_props = ElementProperties(tag_name='span', attributes={'data-testid': 'product-price-main'}, text='123.00')
    attr_price_elem = ExtractedElement(name="price_data_attr", value="123.00", extraction_type="text", source_selector="[data-testid=product-price-main]", properties=attr_price_props)
    analyzer.analyze_element(attr_price_elem)
    print(f"Role: {attr_price_elem.semantic_role}, Conf: {attr_price_elem.role_confidence}, Notes: {attr_price_elem.notes}")

    print("\n--- Test 5: Generic button by tag ---")
    generic_button_props = ElementProperties(tag_name='button', text='Learn More')
    generic_button_elem = ExtractedElement(name="learn_more_btn", value="Learn More", extraction_type="text", source_selector="button.info", properties=generic_button_props)
    analyzer.analyze_element(generic_button_elem) # Should first match text, then tag if text fails
    print(f"Role: {generic_button_elem.semantic_role}, Conf: {generic_button_elem.role_confidence}, Notes: {generic_button_elem.notes}")
    
    print("\n--- Test 6: Element name heuristic (price) as fallback ---")
    name_price_elem = ExtractedElement(name="item_price_details", value="Contact Us", extraction_type="text", source_selector=".contact", properties=ElementProperties(tag_name='a', text='Contact Us'))
    analyzer.analyze_element(name_price_elem)
    print(f"Role: {name_price_elem.semantic_role}, Conf: {name_price_elem.role_confidence}, Notes: {name_price_elem.notes}")

    print("\n--- Test 7: Rating text ---")
    rating_elem = ExtractedElement(name="rating1", value="4.5 out of 5 stars", extraction_type="text", source_selector=".r", properties=ElementProperties(tag_name='span', text='4.5 out of 5 stars'))
    analyzer.analyze_element(rating_elem)
    print(f"Role: {rating_elem.semantic_role}, Conf: {rating_elem.role_confidence}, Notes: {rating_elem.notes}")

    print("\n--- Test 8: Review count text ---")
    review_elem = ExtractedElement(name="reviews1", value="(1,203 ratings)", extraction_type="text", source_selector=".rev", properties=ElementProperties(tag_name='span', text='(1,203 ratings)'))
    analyzer.analyze_element(review_elem)
    print(f"Role: {review_elem.semantic_role}, Conf: {review_elem.role_confidence}, Notes: {review_elem.notes}")
    
    print("\n--- Test 9: Overwrite logic - Price by attribute vs. name heuristic ---")
    # Setup: First, let it be identified by name (low confidence)
    overwrite_test_elem = ExtractedElement(
        name="final_price_section", 
        value="Some other text", 
        extraction_type="text", 
        source_selector=".final",
        properties=ElementProperties(tag_name='div', attributes={'data-testid': 'checkout-final-price'}, text='Some other text')
    )
    # Simulate it being identified by name first (or some other low-confidence heuristic)
    overwrite_test_elem.semantic_role = "product_price_name"
    overwrite_test_elem.role_confidence = 0.45
    overwrite_test_elem.notes.append("Semantic role 'product_price_name' (Confidence: 0.45) inferred from: element name 'final_price_section' containing 'price'.")
    
    # Now analyze, the attribute check should overwrite because it has higher confidence
    analyzer.analyze_element(overwrite_test_elem)
    print(f"Role: {overwrite_test_elem.semantic_role}, Conf: {overwrite_test_elem.role_confidence}, Notes: {overwrite_test_elem.notes}")
    assert overwrite_test_elem.semantic_role == "product_price_attr" # Should be overwritten
    assert overwrite_test_elem.role_confidence == 0.78

    print("\n--- Test 10: No overwrite - Higher confidence already present ---")
    no_overwrite_elem = ExtractedElement(
        name="some_button_name", 
        value="Click Here Now", 
        extraction_type="text", 
        source_selector=".action",
        properties=ElementProperties(tag_name='button', text='Click Here Now') # Tag name would give 0.60
    )
    # Simulate it being identified by text (high confidence)
    no_overwrite_elem.semantic_role = "add_to_cart_button" # Example, could be any high conf role
    no_overwrite_elem.role_confidence = 0.85
    no_overwrite_elem.notes.append("Semantic role 'add_to_cart_button' (Confidence: 0.85) inferred from: text content.")
    
    analyzer.analyze_element(no_overwrite_elem) # Tag name heuristic (0.60) should not overwrite
    print(f"Role: {no_overwrite_elem.semantic_role}, Conf: {no_overwrite_elem.role_confidence}, Notes: {no_overwrite_elem.notes}")
    assert no_overwrite_elem.semantic_role == "add_to_cart_button"
    assert no_overwrite_elem.role_confidence == 0.85
    
    # Example with analyze_extracted_item_details
    print("\n--- Test with analyze_extracted_item_details ---")
    item_data = {
        "productTitle": ExtractedElement(name="productTitle", value="My Awesome Product", extraction_type="text", source_selector="h1.title", properties=ElementProperties(tag_name='h1')),
        "mainPrice": ExtractedElement(name="mainPrice", value="$99.50", extraction_type="text", source_selector=".price", properties=ElementProperties(tag_name='span', text='$99.50')),
        "addToCartButton": ExtractedElement(name="addToCartButton", value="Add to Cart", extraction_type="element", source_selector="button#buy", properties=ElementProperties(tag_name='button', text='Add to Cart'))
    }
    analyzed_item_data = analyzer.analyze_extracted_item_details(item_data)
    print(f"Item Title Role: {analyzed_item_data['productTitle'].semantic_role}, Conf: {analyzed_item_data['productTitle'].role_confidence}")
    print(f"Item Price Role: {analyzed_item_data['mainPrice'].semantic_role}, Conf: {analyzed_item_data['mainPrice'].role_confidence}")
    print(f"Item Button Role: {analyzed_item_data['addToCartButton'].semantic_role}, Conf: {analyzed_item_data['addToCartButton'].role_confidence}") 