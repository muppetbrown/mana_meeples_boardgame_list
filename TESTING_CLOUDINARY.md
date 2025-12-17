# Testing Cloudinary Integration

This guide shows you how to verify that Cloudinary is working correctly.

## Quick Test Checklist

- [ ] Backend shows "Cloudinary CDN enabled" in logs
- [ ] Image URLs redirect to cloudinary.com domains
- [ ] Images appear in Cloudinary dashboard
- [ ] Images are delivered as WebP/AVIF
- [ ] Responsive sizes are working

---

## 1. Check Backend Logs (Production)

### On Render Dashboard:

1. Go to https://dashboard.render.com
2. Select your `mana-meeples-boardgame-list` service
3. Click "Logs" tab
4. Look for this message on startup:

```
✅ SUCCESS - You should see:
Cloudinary CDN enabled: dsobsswqq

❌ FAILURE - If you see this instead:
WARNING: Cloudinary not configured - using direct BGG image URLs
```

**If you see the warning:**
- Environment variables are not set correctly
- Go to Environment tab and verify all three are set:
  - CLOUDINARY_CLOUD_NAME
  - CLOUDINARY_API_KEY
  - CLOUDINARY_API_SECRET

---

## 2. Test Image Proxy Endpoint (Quick API Test)

### Test URL directly in browser:

```
https://mana-meeples-boardgame-list-opgf.onrender.com/api/public/image-proxy?url=https://cf.geekdo-images.com/PhjygpWSo-0labGrPBMyyg__original/img/mZzaBAEEJpMlJDGd3Jz7r4lNJ2A=/fit-in/246x300/filters:strip_icc()/pic1534148.jpg&width=400&height=400
```

**What should happen:**

1. **Browser redirects** (check Network tab in DevTools)
2. **Final URL should contain**: `res.cloudinary.com/dsobsswqq/`
3. **Image loads successfully**

**If it fails:**
- Check the HTTP status code
- 400 = URL validation failed
- 502 = Cloudinary upload failed
- Check backend logs for detailed error

---

## 3. Check Network Tab (Most Reliable Test)

### Steps:

1. **Open your site**: https://library.manaandmeeples.co.nz
2. **Open DevTools**: Press F12 or right-click → Inspect
3. **Go to Network tab**
4. **Filter by "Img"**: Click the "Img" button in the filter bar
5. **Reload the page**: Ctrl+R or Cmd+R
6. **Click on any image request**

### What to look for:

**✅ Cloudinary Working:**
```
Request URL: https://mana-meeples-boardgame-list-opgf.onrender.com/api/public/image-proxy?url=...
Status: 302 Found
Location: https://res.cloudinary.com/dsobsswqq/image/upload/...
```

**✅ Image is optimized:**
```
Final URL: https://res.cloudinary.com/dsobsswqq/image/upload/f_auto,q_auto:best,w_400,h_400/...
Content-Type: image/webp  (or image/avif on newer browsers)
```

**❌ Cloudinary NOT Working:**
```
Request URL: https://mana-meeples-boardgame-list-opgf.onrender.com/api/public/image-proxy?url=...
Status: 200 OK
Content-Type: image/jpeg
(No redirect, serving directly from backend)
```

---

## 4. Verify in Cloudinary Dashboard

### Steps:

1. Go to https://console.cloudinary.com/console
2. Click "Media Library" in left sidebar
3. Look for "boardgame-library" folder
4. You should see uploaded images with hash names

**What you'll see:**

```
boardgame-library/
  ├── a1b2c3d4e5f6...  (245 KB, format: jpg)
  ├── b2c3d4e5f6g7...  (189 KB, format: jpg)
  └── ...
```

**If folder is empty:**
- Cloudinary is configured but no images have been uploaded yet
- Try browsing some games on your site to trigger uploads
- Check backend logs for upload errors

---

## 5. Test Responsive Images (srcset)

### View the HTML:

1. Open your site
2. Right-click on a game image → Inspect
3. Look at the `<img>` tag

**✅ Should see srcset:**
```html
<img
  src="/api/public/image-proxy?url=https://cf.geekdo-images.com/..."
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

### Test different screen sizes:

1. In DevTools, click the device toolbar icon (or Ctrl+Shift+M)
2. Select different devices (iPhone, iPad, Desktop)
3. Reload page for each device
4. Check Network tab - browser should load different sizes:
   - **iPhone**: ~200-400w
   - **iPad**: ~600-800w
   - **Desktop**: ~800-1200w

---

## 6. Verify Modern Format Delivery

### Check image format:

1. Open Network tab
2. Click on an image request
3. Look at "Response Headers"

**✅ Modern browsers (Chrome, Edge, Firefox):**
```
Content-Type: image/webp
```

**✅ Cutting-edge browsers (Chrome 94+, Edge 94+):**
```
Content-Type: image/avif
```

**⚠️ Old browsers (IE11, old Safari):**
```
Content-Type: image/jpeg
```

This is correct! Cloudinary automatically serves the best format for each browser.

---

## 7. Test Performance Impact

### Measure bandwidth savings:

**Before Cloudinary (direct BGG):**
1. Disable Cloudinary (comment out env vars in Render)
2. Clear browser cache
3. Load catalogue page
4. Check total image size in Network tab → Bottom status bar
5. Note the total: e.g., "15.2 MB transferred"

**After Cloudinary:**
1. Re-enable Cloudinary
2. Clear browser cache
3. Load catalogue page
4. Check total image size
5. Note the total: e.g., "5.8 MB transferred"

**Expected savings: 40-70% reduction**

---

## 8. Local Development Testing

### Test locally before deploying:

```bash
# 1. Navigate to backend directory
cd backend

# 2. Install dependencies (including cloudinary)
pip install -r requirements.txt

# 3. Set environment variables
export CLOUDINARY_CLOUD_NAME=dsobsswqq
export CLOUDINARY_API_KEY=159742555664292
export CLOUDINARY_API_SECRET=6-fZDSeelRLTGe9J4a-w0GG8Gow

# 4. Start backend
uvicorn main:app --reload

# 5. Check startup logs
# Should see: "Cloudinary CDN enabled: dsobsswqq"
```

### Test the endpoint:

```bash
# Test image proxy with curl
curl -I "http://localhost:8000/api/public/image-proxy?url=https://cf.geekdo-images.com/PhjygpWSo-0labGrPBMyyg__original/img/mZzaBAEEJpMlJDGd3Jz7r4lNJ2A=/fit-in/246x300/filters:strip_icc()/pic1534148.jpg&width=400&height=400"

# Expected response:
HTTP/1.1 302 Found
location: https://res.cloudinary.com/dsobsswqq/image/upload/...
```

---

## 9. Common Issues & Debugging

### Issue: Images still loading from BGG directly

**Symptoms:**
- Network tab shows no redirect (200 OK)
- URLs are `cf.geekdo-images.com` not `cloudinary.com`

**Solutions:**
1. Check environment variables are set
2. Restart Render service
3. Check logs for "Cloudinary CDN enabled"
4. Clear browser cache (old images may be cached)

---

### Issue: 502 Bad Gateway errors

**Symptoms:**
- Image proxy returns 502 error
- Backend logs show Cloudinary upload failures

**Solutions:**
1. Verify API credentials are correct
2. Check Cloudinary quota (free tier limits)
3. Test BGG URL is valid and accessible
4. Check Cloudinary status: https://status.cloudinary.com

---

### Issue: Images upload but don't show transformations

**Symptoms:**
- Images appear in Cloudinary dashboard
- But no width/height transformations applied

**Solutions:**
1. Check URL includes `w_400,h_400` parameters
2. Verify `get_image_url()` is being called with width/height
3. Check frontend is passing width/height to image-proxy endpoint

---

### Issue: Free tier quota exceeded

**Symptoms:**
- New images fail to upload
- Cloudinary dashboard shows quota warning

**Solutions:**
1. Check usage at https://console.cloudinary.com/console
2. Delete unused images from Media Library
3. Reduce number of transformation variants
4. Consider upgrading to paid plan ($89/month)

---

## 10. Monitoring Best Practices

### Weekly checks:

1. **Cloudinary Dashboard** → Check bandwidth usage (stay under 25 GB/month)
2. **Render Logs** → Look for Cloudinary errors
3. **Network Tab** → Spot-check images are serving as WebP/AVIF
4. **Lighthouse** → Run performance audit (should see improved scores)

### Monthly checks:

1. **Cloudinary Media Library** → Review stored images
2. **Delete unused images** → Free up storage
3. **Check transformation count** → Stay under 25,000/month

---

## Success Criteria

✅ **Cloudinary is working correctly if:**

1. Backend logs show "Cloudinary CDN enabled"
2. Image URLs redirect (302) to `res.cloudinary.com`
3. Images appear in Cloudinary dashboard under `boardgame-library/`
4. Network tab shows WebP/AVIF format delivery
5. Different screen sizes load different image widths
6. Total page bandwidth is 40-70% smaller than before

---

## Need Help?

If Cloudinary isn't working after following this guide:

1. **Check Render logs** for specific errors
2. **Review environment variables** in Render dashboard
3. **Test locally** to isolate the issue
4. **Check Cloudinary status page**: https://status.cloudinary.com
5. **Review CLOUDINARY_SETUP.md** for configuration details
