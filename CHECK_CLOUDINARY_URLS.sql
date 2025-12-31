-- Check Cloudinary URLs in Database
-- Run this query in your Render PostgreSQL shell or local database

-- 1. Count games with/without cloudinary_url
SELECT
    COUNT(*) as total_games,
    COUNT(cloudinary_url) as with_cloudinary_url,
    COUNT(*) - COUNT(cloudinary_url) as missing_cloudinary_url,
    ROUND(100.0 * COUNT(cloudinary_url) / COUNT(*), 1) as percentage_with_cloudinary
FROM boardgames
WHERE image IS NOT NULL OR thumbnail_url IS NOT NULL;

-- 2. Sample cloudinary_url values (first 5 games)
SELECT
    id,
    title,
    SUBSTRING(cloudinary_url, 1, 100) as cloudinary_url_preview,
    CASE
        WHEN cloudinary_url LIKE '%f_auto%' THEN 'YES'
        ELSE 'NO'
    END as has_f_auto,
    CASE
        WHEN cloudinary_url LIKE '%q_auto%' THEN 'YES'
        ELSE 'NO'
    END as has_q_auto,
    CASE
        WHEN cloudinary_url LIKE '%w_800%' THEN 'YES'
        ELSE 'NO'
    END as has_w_800
FROM boardgames
WHERE cloudinary_url IS NOT NULL
LIMIT 5;

-- 3. Count URLs with/without transformations
SELECT
    COUNT(*) as total_with_cloudinary_url,
    SUM(CASE WHEN cloudinary_url LIKE '%f_auto%' THEN 1 ELSE 0 END) as has_f_auto,
    SUM(CASE WHEN cloudinary_url LIKE '%q_auto%' THEN 1 ELSE 0 END) as has_q_auto,
    SUM(CASE WHEN cloudinary_url LIKE '%w_800%' THEN 1 ELSE 0 END) as has_w_800,
    SUM(CASE WHEN cloudinary_url NOT LIKE '%f_auto%' THEN 1 ELSE 0 END) as missing_transformations
FROM boardgames
WHERE cloudinary_url IS NOT NULL;

-- 4. Find games with RAW cloudinary URLs (missing transformations)
SELECT
    id,
    title,
    cloudinary_url
FROM boardgames
WHERE cloudinary_url IS NOT NULL
  AND cloudinary_url NOT LIKE '%f_auto%'
LIMIT 10;
