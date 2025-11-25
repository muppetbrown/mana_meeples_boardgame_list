# Library Frontend Refactoring - Deployment Guide

## Overview
This guide explains how to deploy the refactored board game library frontend that is now hosted on Render instead of cPanel. This eliminates the need for manual uploads and simplifies the deployment process.

## Architecture Changes

### Before:
- **Frontend**: Manually uploaded to cPanel at `/library/` path
- **API**: Hosted on Render, accessed via PHP proxy
- **Updates**: Required manual build and upload to cPanel

### After:
- **Frontend**: Hosted on Render as static site
- **API**: Hosted on Render (same as before)
- **Updates**: Automatic deployment on git push
- **DNS**: CNAME redirect from library.manaandmeeples.co.nz → Render

---

## Step-by-Step Deployment Instructions

### Step 1: Commit and Push Changes ✅ (You can do this now)

All code changes have been made. Commit and push to your repository:

```bash
git add .
git commit -m "Refactor library frontend to Render static hosting"
git push origin claude/refactor-game-library-setup-012Wa9Z3Dswq9JCrbfMAPjSh
```

### Step 2: Create New Render Service 🔧 (Do this in Render Dashboard)

1. **Go to Render Dashboard**: https://dashboard.render.com/
2. **Connect to existing repo**: Select your `mana_meeples_boardgame_list` repository
3. **The new service should auto-create** from `render.yaml`:
   - Service name: `mana-meeples-library-web`
   - Type: Static Site
   - Region: Singapore
   - Build command: `cd frontend && npm install && npm run build`
   - Publish directory: `./frontend/build`

4. **If it doesn't auto-create**, manually create a new **Static Site**:
   - Click "New +" → "Static Site"
   - Connect your repository
   - Name: `mana-meeples-library-web`
   - Region: Singapore
   - Build command: `cd frontend && npm install && npm run build`
   - Publish directory: `./frontend/build`
   - Add environment variable:
     - Key: `REACT_APP_API_BASE`
     - Value: `https://mana-meeples-boardgame-list.onrender.com`

5. **Save and deploy** - Render will build your frontend

### Step 3: Update Backend Service (if needed) 🔧 (Do this in Render Dashboard)

The `render.yaml` file has been updated with new CORS origins, but you may need to verify:

1. Go to your **existing** `mana-meeples-boardgame-list` service
2. Navigate to **Environment** tab
3. Find `CORS_ORIGINS` and verify it includes:
   ```
   https://manaandmeeples.co.nz,https://www.manaandmeeples.co.nz,https://library.manaandmeeples.co.nz,https://mana-meeples-library-web.onrender.com
   ```
4. If not updated automatically, add the new domains manually
5. **Save Changes** (this will trigger a redeploy)

### Step 4: Add Custom Domain to Render 🔧 (Do this in Render Dashboard)

1. Go to your **new** `mana-meeples-library-web` service
2. Navigate to **Settings** → **Custom Domains**
3. Click **Add Custom Domain**
4. Enter: `library.manaandmeeples.co.nz`
5. Render will show you the CNAME target (usually `mana-meeples-library-web.onrender.com`)

### Step 5: Update DNS in cPanel 🔧 (Do this in cPanel)

1. **Log into cPanel**
2. Go to **Zone Editor** or **DNS Management**
3. **Add a new CNAME record**:
   - **Type**: CNAME
   - **Name**: `library` (or `library.manaandmeeples.co.nz`)
   - **Target/Points to**: `mana-meeples-library-web.onrender.com`
   - **TTL**: 14400 (or default)

4. **Remove old library files** (optional cleanup):
   - In cPanel File Manager, you can delete the old `/library/` directory
   - This is optional but recommended to avoid confusion

### Step 6: Wait for DNS Propagation ⏳ (Automatic, 5-30 minutes)

DNS changes can take 5-30 minutes to propagate. You can check status with:
```bash
dig library.manaandmeeples.co.nz
```

Or use online tools like: https://www.whatsmydns.net/

### Step 7: Verify SSL Certificate 🔒 (Automatic in Render)

Render automatically provisions SSL certificates for custom domains. Once DNS propagates:

1. Go back to Render Dashboard → `mana-meeples-library-web` → **Settings** → **Custom Domains**
2. Check that `library.manaandmeeples.co.nz` shows **"Verified"** with a green checkmark
3. SSL certificate should show as **"Active"**

This may take a few minutes after DNS propagation.

### Step 8: Test the New Setup ✅ (You can do this)

1. **Visit the new URL**: https://library.manaandmeeples.co.nz
2. **Test key features**:
   - Browse games by category
   - Search for games
   - View game details
   - Check that images load correctly
   - Test filters (NZ designers, categories)

3. **Test on mobile and desktop** to ensure responsive design works

4. **Check API connectivity**:
   - Open browser console (F12)
   - Look for API calls to `https://mana-meeples-boardgame-list.onrender.com`
   - Verify no CORS errors

---

## Troubleshooting

### Problem: CORS Errors in Browser Console

**Solution**:
- Verify CORS_ORIGINS includes `https://library.manaandmeeples.co.nz` in the backend service
- Redeploy the backend service after updating CORS_ORIGINS

### Problem: "Site Not Found" or 404 Errors

**Solution**:
- Check DNS propagation: `dig library.manaandmeeples.co.nz`
- Verify CNAME points to correct Render URL
- Wait 5-30 minutes for DNS to propagate

### Problem: SSL Certificate Not Working

**Solution**:
- Ensure DNS has fully propagated first
- In Render Dashboard, go to Custom Domains and click **"Retry"** if certificate provisioning failed
- Wait a few minutes and refresh

### Problem: Images Not Loading

**Solution**:
- Check browser console for errors
- Verify API_BASE is correctly set: should be `https://mana-meeples-boardgame-list.onrender.com`
- Check that image proxy endpoint works: `/api/public/image-proxy`

### Problem: Builds Failing on Render

**Solution**:
- Check Render build logs
- Common issues:
  - Missing `node_modules` - ensure `npm install` runs
  - Build command path - ensure `cd frontend` is in build command
  - Environment variables - verify `REACT_APP_API_BASE` is set

---

## Future Deployments (After Initial Setup)

Once everything is set up, future updates are **automatic**:

1. Make changes to frontend code
2. Commit and push to your repository
3. Render automatically detects the push and rebuilds
4. New version deploys automatically (usually takes 2-5 minutes)

**No more manual cPanel uploads! 🎉**

---

## What Changed in the Code

### Files Modified:

1. **render.yaml**: Added new static site service for library frontend
2. **frontend/package.json**: Removed `homepage: "/library"` path restriction
3. **frontend/public/index.html**:
   - Removed PHP proxy configuration
   - Updated SEO meta tags to use `library.manaandmeeples.co.nz`
   - Updated canonical URLs and Open Graph tags
4. **CORS Configuration**: Added new library domain to allowed origins

### Key Benefits:

✅ **Automatic deployments** - No more manual uploads
✅ **Simplified architecture** - No PHP proxy needed
✅ **Better performance** - Render's CDN and caching
✅ **Consistent with shop** - Same pattern as shop.manaandmeeples.co.nz
✅ **Version control** - All deployments tracked in git
✅ **Rollback capability** - Easy to revert if needed

---

## Summary Checklist

Use this checklist to track your progress:

- [ ] Commit and push code changes
- [ ] Create new `mana-meeples-library-web` service on Render
- [ ] Verify CORS_ORIGINS updated on backend service
- [ ] Add custom domain `library.manaandmeeples.co.nz` in Render
- [ ] Create CNAME record in cPanel DNS
- [ ] Wait for DNS propagation (5-30 minutes)
- [ ] Verify SSL certificate is active
- [ ] Test the new library URL
- [ ] (Optional) Remove old `/library/` files from cPanel

---

## Support

If you run into issues:
1. Check the Troubleshooting section above
2. Review Render build logs for errors
3. Check browser console for frontend errors
4. Verify DNS with `dig` or online tools

**Questions?** Check the Render documentation or reach out for help!
