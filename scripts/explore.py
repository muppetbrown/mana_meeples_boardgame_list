#!/usr/bin/env python3
"""
Explore BGG API for 7 Wonders to see if sleeve information exists
"""

import requests
import xml.etree.ElementTree as ET
import os

# BGG API details
BGG_API_KEY = "81fe2a56-cd5e-41b2-b501-29d58fdd9a3e"
BGG_ID_7_WONDERS = 68448

# Fetch the game data
url = f"https://boardgamegeek.com/xmlapi2/thing?id={BGG_ID_7_WONDERS}&stats=1"
headers = {
    "Authorization": f"Bearer {BGG_API_KEY}"
}

print(f"Fetching data for 7 Wonders (BGG ID: {BGG_ID_7_WONDERS})...")
print(f"URL: {url}\n")

try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    # Save the raw XML in the current directory
    output_file = '7_wonders_api_response.xml'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    print(f"✓ Successfully fetched and saved to: {os.path.abspath(output_file)}")
    print(f"Response length: {len(response.text)} characters\n")
    
    # Parse the XML
    root = ET.fromstring(response.text)
    
    # Print all element types
    print("=" * 80)
    print("ALL XML ELEMENTS AND LINK TYPES")
    print("=" * 80)
    
    def print_element(elem, indent=0):
        """Recursively print element structure"""
        prefix = "  " * indent
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        print(f"{prefix}<{tag}>", end="")
        
        if elem.attrib:
            attrs = ", ".join([f"{k}='{v}'" for k, v in elem.attrib.items()])
            print(f" [{attrs}]", end="")
        
        if elem.text and elem.text.strip() and len(elem) == 0:
            text = elem.text.strip()[:100]
            print(f" = '{text}...'", end="")
        
        print()
        
        for child in elem:
            print_element(child, indent + 1)
    
    print_element(root)
    
    # Search for sleeve keywords
    print("\n" + "=" * 80)
    print("SEARCHING FOR SLEEVE-RELATED KEYWORDS")
    print("=" * 80)
    
    keywords = ['sleeve', 'card', 'protector', 'accessory']
    xml_text = response.text.lower()
    
    for keyword in keywords:
        count = xml_text.count(keyword)
        print(f"  '{keyword}': found {count} times")
    
    print(f"\nCheck the full XML file at: {os.path.abspath(output_file)}")
    
except Exception as e:
    print(f"✗ Error: {e}")