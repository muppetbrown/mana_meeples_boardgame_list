#!/usr/bin/env python3
"""
Test Cloudinary URL Generation
===============================

Quick test to verify what URLs the Cloudinary service actually generates.
"""

import sys
import os
import hashlib

# Setup paths
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
os.chdir(backend_dir)

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services.cloudinary_service import cloudinary_service

# Test URL from BGG
test_bgg_url = "https://cf.geekdo-images.com/camo/abc123def456__original/pic123456.jpg"

print("=" * 70)
print("CLOUDINARY URL GENERATION TEST")
print("=" * 70)
print()

print(f"Cloudinary enabled: {cloudinary_service.enabled}")
print(f"Cloudinary folder: {cloudinary_service.folder}")
print()

# Test 1: get_image_url() WITHOUT width/height (used by image-proxy endpoint)
print("TEST 1: get_image_url(url) - NO width/height")
print(f"  Input: {test_bgg_url}")
url1 = cloudinary_service.get_image_url(test_bgg_url)
print(f"  Output: {url1}")
print(f"  Has f_auto? {'f_auto' in url1}")
print(f"  Has q_auto:best? {'q_auto:best' in url1}")
print(f"  Has w_800? {'w_800' in url1}")
print()

# Test 2: get_image_url() WITH width/height (should include all transformations)
print("TEST 2: get_image_url(url, width=800, height=800)")
print(f"  Input: {test_bgg_url}")
url2 = cloudinary_service.get_image_url(test_bgg_url, width=800, height=800)
print(f"  Output: {url2}")
print(f"  Has f_auto? {'f_auto' in url2}")
print(f"  Has q_auto:best? {'q_auto:best' in url2}")
print(f"  Has w_800? {'w_800' in url2}")
print()

# Test 3: generate_optimized_url() (used by backfill script and game import)
print("TEST 3: generate_optimized_url(url, width=800, height=800)")
print(f"  Input: {test_bgg_url}")
url3 = cloudinary_service.generate_optimized_url(
    test_bgg_url,
    width=800,
    height=800,
    quality="auto:best",
    format="auto"
)
print(f"  Output: {url3}")
print(f"  Has f_auto? {'f_auto' in url3}")
print(f"  Has q_auto:best? {'q_auto:best' in url3}")
print(f"  Has w_800? {'w_800' in url3}")
print()

# Test 4: User's actual URL
user_url = "https://res.cloudinary.com/dsobsswqq/image/upload/v1767163180/boardgame-library/d2371cc1cd0826517d166f1ea63dbecf.png"
print("TEST 4: User's Actual URL Analysis")
print(f"  URL: {user_url}")
print(f"  Has f_auto? {'f_auto' in user_url}")
print(f"  Has q_auto:best? {'q_auto:best' in user_url}")
print(f"  Has w_800? {'w_800' in user_url}")
print(f"  Has transformations? {',' in user_url.split('/image/upload/')[1].split('/')[0]}")
print()

# Expected vs Actual
print("=" * 70)
print("EXPECTED vs ACTUAL")
print("=" * 70)
print()
print("EXPECTED (with transformations):")
expected_hash = hashlib.md5(test_bgg_url.encode()).hexdigest()
expected_url = f"https://res.cloudinary.com/dsobsswqq/image/upload/f_auto,q_auto:best,w_800,h_800,c_limit/boardgame-library/{expected_hash}"
print(f"  {expected_url}")
print()
print("USER'S ACTUAL (missing transformations):")
print(f"  {user_url}")
print()

print("=" * 70)
print("DIAGNOSIS")
print("=" * 70)
print()

if not cloudinary_service.enabled:
    print("❌ PROBLEM: Cloudinary is NOT enabled!")
    print("   - Check environment variables: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET")
elif 'f_auto' not in url3:
    print("❌ PROBLEM: generate_optimized_url() not adding transformations!")
    print("   - This is a bug in cloudinary_service.py")
    print("   - Check CloudinaryImage().build_url() implementation")
elif 'f_auto' not in user_url:
    print("⚠️  PROBLEM: Database has raw URLs instead of transformed URLs")
    print("   - The backfill script needs to be run")
    print("   - Or the database was populated before transformations were added")
    print()
    print("SOLUTION:")
    print("  1. Run: python -m backend.scripts.backfill_cloudinary_urls --dry-run")
    print("  2. Review the URLs that would be generated")
    print("  3. Run: python -m backend.scripts.backfill_cloudinary_urls")
    print("  4. Verify in database that cloudinary_url has transformations")
else:
    print("✓ Cloudinary URL generation appears correct")
    print("  The database might just need updating")
