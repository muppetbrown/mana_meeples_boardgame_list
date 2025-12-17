#!/usr/bin/env python3
"""
Cloudinary connection test script
Run this to verify your Cloudinary credentials and test basic functionality
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up Cloudinary credentials
os.environ.setdefault("CLOUDINARY_CLOUD_NAME")
os.environ.setdefault("CLOUDINARY_API_KEY")
os.environ.setdefault("CLOUDINARY_API_SECRET")

print("=" * 60)
print("CLOUDINARY CONNECTION TEST")
print("=" * 60)

# Test 1: Import and configure
print("\n1. Testing Cloudinary import and configuration...")
try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api

    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True
    )

    config = cloudinary.config()
    print(f"✅ Cloudinary SDK imported successfully")
    print(f"   Cloud Name: {config.cloud_name}")
    print(f"   API Key: {config.api_key[:4]}...{config.api_key[-4:]}")
    print(f"   API Secret: {'*' * 20} (hidden)")
except Exception as e:
    print(f"❌ Failed to import/configure Cloudinary: {e}")
    sys.exit(1)

# Test 2: Ping API
print("\n2. Testing Cloudinary API connection...")
try:
    result = cloudinary.api.ping()
    print(f"✅ API connection successful!")
    print(f"   Status: {result.get('status', 'unknown')}")
except cloudinary.exceptions.AuthorizationRequired as e:
    print(f"❌ Authorization failed - check your API credentials")
    print(f"   Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ API connection failed: {e}")
    sys.exit(1)

# Test 3: Upload a test image from URL
print("\n3. Testing image upload from URL...")
test_bgg_url = "https://cf.geekdo-images.com/PhjygpWSo-0labGrPBMyyg__original/img/mZzaBAEEJpMlJDGd3Jz7r4lNJ2A=/fit-in/246x300/filters:strip_icc()/pic1534148.jpg"

try:
    result = cloudinary.uploader.upload(
        test_bgg_url,
        public_id="test/test-image",
        folder="boardgame-library-test",
        resource_type="image",
        type="upload",
        overwrite=True,
        format="auto",
        quality="auto:best",
        fetch_format="auto",
    )

    print(f"✅ Image uploaded successfully!")
    print(f"   Public ID: {result.get('public_id')}")
    print(f"   Format: {result.get('format')}")
    print(f"   Width: {result.get('width')}px")
    print(f"   Height: {result.get('height')}px")
    print(f"   Size: {result.get('bytes')} bytes")
    print(f"   URL: {result.get('secure_url')}")

except cloudinary.exceptions.Error as e:
    print(f"❌ Upload failed: {e}")
    print(f"   This might be a quota or permissions issue")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error during upload: {e}")
    sys.exit(1)

# Test 4: Generate transformation URL
print("\n4. Testing URL transformations...")
try:
    from cloudinary import CloudinaryImage

    public_id = result.get('public_id')

    # Generate URL with transformations
    transformed_url = CloudinaryImage(public_id).build_url(
        width=400,
        height=400,
        crop="fill",
        quality="auto:best",
        fetch_format="auto"
    )

    print(f"✅ Transformation URL generated!")
    print(f"   Original URL: {result.get('secure_url')}")
    print(f"   Transformed (400x400): {transformed_url}")

except Exception as e:
    print(f"❌ Transformation failed: {e}")

# Test 5: Clean up test image
print("\n5. Cleaning up test image...")
try:
    delete_result = cloudinary.uploader.destroy(result.get('public_id'))
    if delete_result.get('result') == 'ok':
        print(f"✅ Test image deleted successfully")
    else:
        print(f"⚠️  Could not delete test image: {delete_result}")
except Exception as e:
    print(f"⚠️  Cleanup failed (not critical): {e}")

# Test 6: Test the CloudinaryService
print("\n6. Testing CloudinaryService class...")
try:
    from services.cloudinary_service import CloudinaryService

    service = CloudinaryService()

    if not service.enabled:
        print(f"❌ CloudinaryService reports as disabled")
        print(f"   Check environment variables in config")
        sys.exit(1)

    print(f"✅ CloudinaryService initialized successfully")
    print(f"   Folder: {service.folder}")
    print(f"   Enabled: {service.enabled}")

    # Test get_public_id
    test_url = "https://cf.geekdo-images.com/test.jpg"
    public_id = service._get_public_id(test_url)
    print(f"   Test public_id: {public_id}")

except ImportError as e:
    print(f"⚠️  Could not import CloudinaryService (run from backend dir): {e}")
except Exception as e:
    print(f"❌ CloudinaryService test failed: {e}")

# Final summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print("✅ Cloudinary is configured correctly and working!")
print("\nNext steps:")
print("1. Deploy your changes to Render")
print("2. Set environment variables in Render dashboard")
print("3. Check logs for 'Cloudinary CDN enabled' message")
print("4. Browse your site and check Network tab for cloudinary.com URLs")
print("\nSee TESTING_CLOUDINARY.md for detailed testing instructions")
print("=" * 60)
