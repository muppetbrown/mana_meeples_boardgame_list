# Sleeve Fetching Setup Guide

## Overview

The sleeve data fetching system uses GitHub Actions to scrape BoardGameGeek's sleeve pages with Selenium. This approach avoids the need to install Chrome on the Render server and provides a more reliable scraping environment.

## How It Works

1. **Select games** in the Manage Library tab
2. **Click "Fetch Sleeve Data"** button
3. **GitHub Actions workflow** is triggered automatically
4. **Selenium scrapes** sleeve data from BGG in GitHub's environment
5. **Data is saved** directly to the PostgreSQL database

## Setup Requirements

### 1. GitHub Personal Access Token

Create a Personal Access Token with `workflow` permissions:

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name: "Sleeve Fetch Workflow Trigger"
4. Select scopes:
   - ✅ **workflow** (required)
5. Generate and copy the token

### 2. Environment Variables on Render

Add the following environment variables to your Render backend service:

```
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO_OWNER=muppetbrown
GITHUB_REPO_NAME=mana_meeples_boardgame_list
```

**Note**: `GITHUB_REPO_OWNER` and `GITHUB_REPO_NAME` have defaults in config.py, but you can override them if needed.

### 3. Database URL in GitHub Secrets

Ensure the GitHub repository has the following secret configured:

- **Name**: `DATABASE_URL`
- **Value**: Your PostgreSQL connection string from Render

This is required for the GitHub Actions workflow to connect to the database.

## Usage

### Fetch Sleeve Data for Selected Games

1. Log in to the staff dashboard
2. Go to "Manage Library" tab
3. Select one or more games using checkboxes
4. Click "🔄 Fetch Sleeve Data" button
5. Confirm the action
6. The workflow will run in the background (check GitHub Actions tab to monitor)

### Fetch Sleeve Data for All Games

You can also manually trigger the workflow from GitHub:

1. Go to GitHub → Actions → "Fetch Sleeve Data" workflow
2. Click "Run workflow"
3. Leave "game_ids" field empty to fetch for all games
4. Click "Run workflow" button

## Technical Details

### Backend Endpoint

- **URL**: `POST /api/admin/trigger-sleeve-fetch`
- **Auth**: Requires admin JWT token
- **Payload**: Array of game IDs
- **Returns**: Success confirmation or error message

### GitHub Workflow

- **File**: `.github/workflows/fetch_sleeves.yml`
- **Trigger**: `workflow_dispatch` with optional `game_ids` input
- **Environment**: Ubuntu with Chrome/ChromeDriver installed
- **Timeout**: 2 hours maximum
- **Rate Limiting**: 1 second delay between games

### Script

- **File**: `scripts/fetch_all_sleeves.py`
- **Usage**: `python scripts/fetch_all_sleeves.py [--game-ids "1,2,3"]`
- **Features**:
  - Accepts comma-separated game IDs
  - Fetches all games if no IDs specified
  - Automatic driver restart every 50 games
  - Hard timeout per game (30 seconds)
  - Thread-based timeout handling

## Troubleshooting

### Workflow Not Triggering

**Error**: "GitHub token not configured"

**Solution**: Ensure `GITHUB_TOKEN` is set in Render environment variables and redeploy.

### Workflow Failing

**Check**:
1. GitHub Actions logs for detailed error messages
2. Ensure `DATABASE_URL` secret is correctly set in GitHub repository
3. Verify the PostgreSQL database is accessible from GitHub Actions IPs

### No Sleeve Data After Successful Run

**Possible causes**:
1. Game doesn't have sleeve data on BGG
2. BGG changed their HTML structure (requires scraper update)
3. Timeout occurred during scraping

**Check**: Look at the workflow logs to see which games succeeded/failed.

## Future Improvements

- Add webhook to notify when workflow completes
- Show workflow status in the frontend
- Automatic retry for failed games
- Batch processing with progress updates
