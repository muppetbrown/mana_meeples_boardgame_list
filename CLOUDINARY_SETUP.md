# Cloudinary CDN Setup Guide

This guide explains how to set up Cloudinary for the Mana & Meeples Board Game Library.

## What is Cloudinary?

Cloudinary is an image CDN (Content Delivery Network) that provides:
- **Automatic image optimization** - Reduces image size by 20-30%
- **Modern format delivery** - Serves WebP/AVIF based on browser support
- **Global CDN** - Faster image loading worldwide
- **Responsive images** - Automatic resizing for different screen sizes
- **Smart cropping** - AI-powered image cropping and focal point detection

## Free Tier Limits

Cloudinary's free tier includes:
- ✅ 25 GB storage
- ✅ 25 GB bandwidth per month
- ✅ 25,000 transformations per month
- ✅ Unlimited images

This is sufficient for ~400-500 board game cover images with typical usage patterns.

## Setup Steps

### 1. Create Cloudinary Account

1. Go to https://cloudinary.com
2. Click "Sign Up for Free"
3. Complete registration
4. Verify your email

### 2. Get Your Credentials

1. Log in to https://console.cloudinary.com/console
2. On the dashboard, find your credentials:
   - **Cloud Name**: `dsobsswqq`
   - **API Key**: `159742555664292`
   - **API Secret**: `6-fZDSeelRLTGe9J4a-w0GG8Gow` (keep this private!)

### 3. Configure Render Environment Variables

**For Production (Render Dashboard):**

1. Go to https://dashboard.render.com
2. Select your `mana-meeples-boardgame-list` service
3. Click "Environment" in the left sidebar
4. Add these environment variables:

```
CLOUDINARY_CLOUD_NAME=dsobsswqq
CLOUDINARY_API_KEY=159742555664292
CLOUDINARY_API_SECRET=6-fZDSeelRLTGe9J4a-w0GG8Gow
```

5. Click "Save Changes"
6. Render will automatically redeploy with Cloudinary enabled

### 4. Verify Setup

After deployment completes, check the logs:

```bash
# Look for this message in Render logs:
Cloudinary CDN enabled: dsobsswqq
```

If you see:
```bash
WARNING: Cloudinary not configured - using direct BGG image URLs
```

Then the environment variables are not set correctly.

## How It Works

### Automatic Image Upload

When a user first views a game image:

1. **Frontend** requests image via `/api/public/image-proxy?url=...&width=400&height=400`
2. **Backend** checks if image exists in Cloudinary
3. If not exists:
   - Downloads image from BoardGameGeek
   - Uploads to Cloudinary (stored permanently)
   - Returns Cloudinary URL
4. If exists:
   - Returns cached Cloudinary URL immediately

### Responsive Images

The frontend generates srcset with multiple sizes:

```html
<img
  srcset="
    /api/public/image-proxy?url=...&width=200&height=200 200w,
    /api/public/image-proxy?url=...&width=400&height=400 400w,
    /api/public/image-proxy?url=...&width=600&height=600 600w,
    /api/public/image-proxy?url=...&width=800&height=800 800w,
    /api/public/image-proxy?url=...&width=1200&height=1200 1200w
  "
  sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 400px"
/>
```

Cloudinary automatically:
- Serves the best size for the device
- Converts to WebP on supported browsers
- Converts to AVIF on cutting-edge browsers
- Compresses with optimal quality

### Transformations

Cloudinary applies these transformations automatically:

- **Format**: `auto` (WebP/AVIF/JPG based on browser)
- **Quality**: `auto:best` (optimized compression)
- **Crop**: `fill` (resize to fit dimensions)
- **Gravity**: `auto` (AI-powered focal point)

## Monitoring Usage

### Check Cloudinary Dashboard

1. Go to https://console.cloudinary.com/console
2. View your usage:
   - **Transformations**: Should stay under 25,000/month
   - **Bandwidth**: Should stay under 25 GB/month
   - **Storage**: Should stay under 25 GB total

### Check Image Count

```bash
# In Cloudinary console, navigate to:
Media Library → boardgame-library folder

# You'll see all uploaded game images
```

### API Endpoint

Check image stats via API:

```bash
curl -X GET "https://api.cloudinary.com/v1_1/dsobsswqq/resources/image" \
  -u "159742555664292:6-fZDSeelRLTGe9J4a-w0GG8Gow"
```

## Fallback Behavior

If Cloudinary is unavailable or disabled:

- ✅ Images still work (falls back to direct BGG proxy)
- ⚠️ No optimization (larger file sizes)
- ⚠️ No WebP/AVIF support
- ⚠️ No global CDN caching

## Performance Comparison

### Before Cloudinary
- **Image Size**: ~200-500 KB per image (PNG/JPG)
- **Load Time**: 2-5 seconds on slow connections
- **Format**: JPG/PNG only

### After Cloudinary
- **Image Size**: ~60-200 KB per image (WebP/AVIF)
- **Load Time**: 0.5-2 seconds on slow connections
- **Format**: WebP (Chrome/Edge), AVIF (cutting-edge), JPG (fallback)

**Bandwidth Savings**: ~40-70% reduction

## Troubleshooting

### Images not loading

1. Check Render logs for Cloudinary errors
2. Verify environment variables are set correctly
3. Check Cloudinary dashboard for quota exceeded

### Images loading but not optimized

1. Check browser DevTools → Network tab
2. Look for `cf.cloudinary.com` in image URLs
3. If still seeing `cf.geekdo-images.com`, Cloudinary is disabled

### Quota exceeded

If you exceed free tier limits:

1. **Upgrade to paid plan** ($89/month for 75GB bandwidth)
2. **Optimize usage**:
   - Reduce image sizes
   - Use more aggressive caching
   - Limit transformations

## Advanced Configuration

### Custom Transformations

Edit `backend/services/cloudinary_service.py` to customize:

```python
# Change quality
transformation = {
    "quality": "auto:eco",  # More aggressive compression
}

# Add effects
transformation = {
    "quality": "auto:best",
    "effect": "sharpen:100",  # Sharpen images
}

# Custom cropping
transformation = {
    "crop": "thumb",  # Thumbnail mode
    "gravity": "face",  # Focus on faces
}
```

### Folder Organization

Images are stored in Cloudinary under:
```
boardgame-library/
  ├── abc123def456  (hashed URL)
  ├── def456ghi789
  └── ...
```

To change folder:
```python
# In cloudinary_service.py
self.folder = "my-custom-folder"
```

## Security Notes

### API Secret

**NEVER** commit your `CLOUDINARY_API_SECRET` to Git!

- ✅ Set in Render dashboard environment variables
- ✅ Set in local `.env` file (gitignored)
- ❌ Do not put in code
- ❌ Do not put in `render.yaml` (uses `sync: false`)

### URL Signing (Optional)

For extra security, enable URL signing:

```python
# In cloudinary_service.py
upload_options = {
    "sign_url": True,  # Prevent URL tampering
}
```

## Cost Optimization

### Tips to stay within free tier:

1. **Use cached URLs** - Cloudinary deduplicates identical transformations
2. **Limit size variations** - Stick to 5 standard sizes
3. **Lazy load images** - Only load visible images
4. **Progressive loading** - Use Phase 1 + Phase 2 optimizations

## Support

- **Cloudinary Docs**: https://cloudinary.com/documentation
- **Cloudinary Support**: https://support.cloudinary.com
- **Status Page**: https://status.cloudinary.com
