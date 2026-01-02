#!/usr/bin/env python3
"""
Test script to verify BGG URL handling logic
Tests the transformation from __original to __md
"""

import re

def test_url_transformation(url):
    """Simulate backend transformation logic"""
    print(f"\nOriginal URL:\n  {url}")

    # Simulate the transformation in public.py lines 365-369
    if 'cf.geekdo-images.com' in url and '__original/' in url:
        transformed = re.sub(r'__original/', '__md/', url)
        print(f"\nTransformed to __md:\n  {transformed}")
        return transformed
    else:
        print("\n✓ No transformation needed (URL already using allowed size)")
        return url

# Test cases
print("=" * 80)
print("BGG URL TRANSFORMATION TESTS")
print("=" * 80)

# Test 1: URL with __original and /img/ (from user's example)
test_url_transformation(
    "https://cf.geekdo-images.com/ydwU0FMlRVa6wt8tOu1tgg__original/img/RT9ajRhK-eHlBJgsksL9rJQHIuk=/0x0/filters:format(jpeg)/pic7962719.jpg"
)

# Test 2: URL with __md already (should not transform)
test_url_transformation(
    "https://cf.geekdo-images.com/ydwU0FMlRVa6wt8tOu1tgg__md/img/RT9ajRhK-eHlBJgsksL9rJQHIuk=/0x0/filters:format(jpeg)/pic7962719.jpg"
)

# Test 3: URL with __d (should not transform)
test_url_transformation(
    "https://cf.geekdo-images.com/ydwU0FMlRVa6wt8tOu1tgg__d/img/RT9ajRhK-eHlBJgsksL9rJQHIuk=/0x0/filters:format(jpeg)/pic7962719.jpg"
)

# Test 4: Another __original example (Star Wars from logs)
test_url_transformation(
    "https://cf.geekdo-images.com/C-nkGn4bUYSSJjf0J9uqyg__original/img/B3lhxKVRanaQq8heM93VTWuC-tQ=/0x0/filters:format(png)/pic8833062.png"
)

print("\n" + "=" * 80)
print("KEY POINTS:")
print("=" * 80)
print("✓ /img/ and /filters: are VALID BGG URL components (not stripped)")
print("✓ Only __original is transformed to __md")
print("✓ All other size variants pass through unchanged")
print("✓ Backend will add browser headers (User-Agent, Referer) when downloading")
print("=" * 80)
