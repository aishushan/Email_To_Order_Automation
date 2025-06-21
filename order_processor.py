import json
import re
from datetime import datetime
from dateutil import parser
import spacy
from typing import Dict, List, Optional
from spacy.matcher import PhraseMatcher
from datetime import timedelta

class OrderProcessor:
    def __init__(self, catalog_path: str = "data/product_catalog.json"):
        self.nlp = spacy.load("en_core_web_sm")
        self.catalog = self._load_catalog(catalog_path)
        self.product_matcher = self._create_product_matcher()
        self.address_keywords = ["ship to", "deliver to", "mail to", "address", "send to"]
        self.quantity_phrases = ["quantity", "qty", "x", "of"]
        self.priority_keywords = ["urgent", "immediate", "asap", "time is critical", "rush"]

    def _load_catalog(self, path: str) -> Dict:
        with open(path, 'r') as f:
            return json.load(f)

    def _create_product_matcher(self):
        matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        patterns = [self.nlp(product['name'].lower()) for product in self.catalog['products']]
        patterns += [self.nlp(product['sku'].lower()) for product in self.catalog['products']]
        matcher.add("PRODUCT", patterns)
        return matcher

    def process_email(self, email_text: str) -> Dict:
        doc = self.nlp(email_text)
        text = email_text.lower()
        
        order_data = {
            "customer_name": self._extract_customer_name(doc),
            "products": self._extract_products(email_text),
            "shipping_address": self._extract_shipping_address(email_text),
            "delivery_date": self._extract_delivery_date(email_text),
            "special_instructions": self._extract_special_instructions(email_text),
            "priority": self._detect_priority(text),
            "contact": self._extract_contact_info(email_text),
            "needs_review": False
        }
        
        order_data["needs_review"] = self._needs_review(order_data)
        return order_data

    def _extract_customer_name(self, doc) -> Dict:
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return {"value": ent.text, "confidence": 0.95}
        return {"value": None, "confidence": 0.1}
    
    
    def _extract_products(self, text: str) -> List[Dict]:
        products = []
        product_quantities = {}
        
        # Process each line looking for product patterns
        for line in text.split('\n'):
            line = line.strip()
            
            # Pattern 1: ITEM X: Product (SKU) - Qty: N
            if match := re.match(r'(?i)ITEM\s+\d+:\s*(.+?)\s*\(([^)]+)\)\s*(?:-\s*Qty:\s*(\d+))?', line):
                name, sku, qty = match.groups()
                product = self._find_product_in_catalog(sku.strip())
                if product:
                    quantity = int(qty) if qty else self._extract_quantity_near_product(self.nlp(line), self.nlp(name)).get('value', 1)
                    product_quantities[product['sku']] = quantity
            
            # Pattern 2: N Product (SKU)
            elif match := re.match(r'^\s*(\d+)\s+(.+?)\s*\(([^)]+)\)', line, re.IGNORECASE):
                qty, name, sku = match.groups()
                product = self._find_product_in_catalog(sku.strip())
                if product:
                    product_quantities[product['sku']] = int(qty)
            
            # Pattern 3: Qty: N (standalone quantity mention)
            elif match := re.search(r'(?i)(?:qty|quantity)\s*:\s*(\d+)', line):
                # Try to associate with previous product if no direct match
                if product_quantities and len(product_quantities) == 1:
                    sku = next(iter(product_quantities.keys()))
                    product_quantities[sku] = int(match.group(1))
                    
            # Pattern 4: - N Product (SKU) (bullet points)
            elif match := re.match(r'^-\s*(\d+)\s+(.+?)\s*\(([^)]+)\)', line, re.IGNORECASE):
                qty, name, sku = match.groups()
                product = self._find_product_in_catalog(sku.strip())
                if product:
                    product_quantities[product['sku']] = int(qty)
            
            # Pattern 5: N pairs of Product (SKU)
            elif match := re.match(r'^(\d+)\s+pairs?\s+of\s+(.+?)\s*\(([^)]+)\)', line, re.IGNORECASE):
                qty, name, sku = match.groups()
                product = self._find_product_in_catalog(sku.strip())
                if product:
                    product_quantities[product['sku']] = int(qty)
            
            # Pattern 6: - N pairs of Product (SKU) (bullet points)
            elif match := re.match(r'^-\s*(\d+)\s+pairs?\s+of\s+(.+?)\s*\(([^)]+)\)', line, re.IGNORECASE):
                qty, name, sku = match.groups()
                product = self._find_product_in_catalog(sku.strip())
                if product:
                    product_quantities[product['sku']] = int(qty)
                    
            # Pattern 7: Numbered list (1. N Product (SKU))
            elif match := re.match(r'^\s*\d+\.\s*(\d+)\s*(?:x|\*)?\s*(.+?)\s*\(([^)]+)\)', line, re.IGNORECASE):
                qty, name, sku = match.groups()
                product = self._find_product_in_catalog(sku.strip())
                if product:
                    product_quantities[product['sku']] = int(qty)
        
        # Fallback to NLP extraction if no structured data found
        if not product_quantities:
            doc = self.nlp(text)
            for match_id, start, end in self.product_matcher(doc):
                product_span = doc[start:end]
                product_info = self._find_product_in_catalog(product_span.text)
                if product_info:
                    quantity = self._extract_quantity_near_product(doc, product_span)
                    if product_info['sku'] in product_quantities:
                        product_quantities[product_info['sku']] += quantity['value']
                    else:
                        product_quantities[product_info['sku']] = quantity['value']
        
        # Create final products list
        for sku, quantity in product_quantities.items():
            product = self._find_product_in_catalog(sku)
            if product:
                products.append({
                    "sku": product['sku'],
                    "name": product['name'],
                    "quantity": quantity,
                    "price": float(product['price']),
                    "confidence": 0.95 if quantity > 0 else 0.5
                })
        
        return products
    

    def _extract_shipping_address(self, text: str) -> Dict:
        address = {"value": None, "confidence": 0.0}
        for keyword in self.address_keywords:
            if match := re.search(fr'(?i){keyword}[:\s]*(.*?)(?:\n\n|\Z)', text, re.DOTALL):
                address_text = match.group(1).strip()
                if len(address_text.split('\n')) >= 2:
                    address = {
                        "value": address_text,
                        "confidence": 0.9
                    }
                    break
        return address


    def _extract_delivery_date(self, text: str) -> Dict:
        """Enhanced delivery date extraction that handles multiple formats"""
        date_patterns = [
            r'(?:required by|due by|by|needed by|arrive by)\s*([A-Za-z]+\s+\d{1,2}(?:\s*,\s*\d{4})?)',
            r'(?:delivery date|deliver by)\s*:\s*([A-Za-z]+\s+\d{1,2}(?:\s*,\s*\d{4})?)',
            r'need these by\s*(next\s+[A-Za-z]+|next\s+week|tomorrow)',
            r'must arrive before\s*([A-Za-z]+\s+\d{1,2}(?:\s*,\s*\d{4})?)',
            r'(\bMarch\s+\d{1,2}\b|\bApr(?:il)?\s+\d{1,2}\b|\bMay\s+\d{1,2}\b|\bJun(?:e)?\s+\d{1,2}\b|\bJul(?:y)?\s+\d{1,2}\b|\bAug(?:ust)?\s+\d{1,2}\b|\bSep(?:tember)?\s+\d{1,2}\b|\bOct(?:ober)?\s+\d{1,2}\b|\bNov(?:ember)?\s+\d{1,2}\b|\bDec(?:ember)?\s+\d{1,2}\b|\bJan(?:uary)?\s+\d{1,2}\b|\bFeb(?:ruary)?\s+\d{1,2}\b)'
        ]
        
        for pattern in date_patterns:
            if match := re.search(pattern, text, re.IGNORECASE):
                date_str = match.group(1).strip()
                try:
                    date = parser.parse(date_str, fuzzy=True)
                    return {
                        "value": date.strftime("%Y-%m-%d"),
                        "confidence": 0.9
                    }
                except:
                    continue
        
        # Handle relative dates like "next Friday"
        if "next Friday" in text:
            today = datetime.now()
            days_ahead = (4 - today.weekday()) % 7  # Friday is weekday 4
            if days_ahead <= 0:  # If today is Friday or after
                days_ahead += 7  # Get next Friday
            next_friday = today + timedelta(days=days_ahead)
            return {
                "value": next_friday.strftime("%Y-%m-%d"),
                "confidence": 0.8
            }
        
        return {"value": None, "confidence": 0.0}
    

    def _extract_special_instructions(self, text: str) -> List[str]:
        instructions = []
        if match := re.search(r'(?i)special instructions:?(.*?)(?:\n\n|\Z)', text, re.DOTALL):
            for line in match.group(1).split('\n'):
                if line.strip():
                    instructions.append(line.strip())
        return instructions

    def _extract_contact_info(self, text: str) -> Dict:
        contact = {}
        if email_match := re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text):
            contact['email'] = email_match.group(1)
        if phone_match := re.search(r'(\(\d{3}\) \d{3}-\d{4})', text):
            contact['phone'] = phone_match.group(1)
        return contact

    def _detect_priority(self, text: str) -> str:
        return "urgent" if any(kw in text.lower() for kw in self.priority_keywords) else "normal"


    def _extract_quantity_near_product(self, doc, product_span) -> Dict:
        """Extract quantity near product in the document"""
        # Look in the same sentence if available
        if hasattr(product_span, 'sent'):
            for token in product_span.sent:
                if token.like_num and token.i < product_span.end + 5:  # Look a few tokens ahead
                    return {"value": int(token.text), "confidence": 0.9}
        
        # Fallback to looking in nearby tokens
        start = max(0, product_span.start - 3)
        end = min(len(doc), product_span.end + 3)
        for token in doc[start:end]:
            if token.like_num:
                return {"value": int(token.text), "confidence": 0.7}
        
        # Final fallback
        return {"value": 1, "confidence": 0.5}

    def _find_product_in_catalog(self, text: str) -> Optional[Dict]:
        text_lower = text.lower()
        for product in self.catalog['products']:
            if text_lower == product['name'].lower() or text_lower == product['sku'].lower():
                return product
        return None

    def _needs_review(self, order_data: Dict) -> bool:
        if not order_data['customer_name']['value'] or order_data['customer_name']['confidence'] < 0.5:
            return True
        if not order_data['products']:
            return True
        if not order_data['shipping_address']['value']:
            return True
        for product in order_data['products']:
            if product['quantity'] <= 0 or product['quantity'] > 1000:
                return True
        return False