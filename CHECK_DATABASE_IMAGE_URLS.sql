-- Check what URLs are actually in the database
-- This will show if there's a mismatch between requested URLs and stored URLs

-- 1. Check which image size variants are in the database
SELECT
    CASE
        WHEN image LIKE '%__original%' THEN '__original'
        WHEN image LIKE '%__d%' THEN '__d (detail)'
        WHEN image LIKE '%__md%' THEN '__md (medium)'
        WHEN image LIKE '%__mt%' THEN '__mt (medium-thumb)'
        WHEN image LIKE '%__t%' THEN '__t (thumbnail)'
        ELSE 'other'
    END as image_size_variant,
    COUNT(*) as count
FROM boardgames
WHERE image IS NOT NULL
GROUP BY image_size_variant
ORDER BY count DESC;

-- 2. Sample 5 games to see actual URLs
SELECT
    id,
    title,
    SUBSTRING(image, 1, 100) as image_url_preview,
    SUBSTRING(cloudinary_url, 1, 100) as cloudinary_url_preview,
    CASE
        WHEN image LIKE '%__original%' THEN '__original'
        WHEN image LIKE '%__d%' THEN '__d'
        WHEN image LIKE '%__md%' THEN '__md'
        WHEN image LIKE '%__mt%' THEN '__mt'
        WHEN image LIKE '%__t%' THEN '__t'
    END as size_in_database
FROM boardgames
WHERE image IS NOT NULL
LIMIT 5;

-- 3. Check if frontend-requested URLs match database URLs
-- These are the failing URLs from your logs:
SELECT
    id,
    title,
    image,
    cloudinary_url
FROM boardgames
WHERE
    image = 'https://cf.geekdo-images.com/C-nkGn4bUYSSJjf0J9uqyg__original/pic8833062.png'
    OR image = 'https://cf.geekdo-images.com/MmJapKYTIXA0Sf4WCCSmQg__original/pic7440823.jpg'
    OR image = 'https://cf.geekdo-images.com/1EeG4Iw7oH6HR15Yo9waQA__original/pic8272357.jpg';

-- 4. Check if those games exist with DIFFERENT size variants
SELECT
    id,
    title,
    image,
    CASE
        WHEN image LIKE '%C-nkGn4bUYSSJjf0J9uqyg%' THEN 'pic8833062 (first failing URL)'
        WHEN image LIKE '%MmJapKYTIXA0Sf4WCCSmQg%' THEN 'pic7440823 (second failing URL)'
        WHEN image LIKE '%1EeG4Iw7oH6HR15Yo9waQA%' THEN 'pic8272357 (third failing URL)'
    END as match_reason
FROM boardgames
WHERE
    image LIKE '%C-nkGn4bUYSSJjf0J9uqyg%'
    OR image LIKE '%MmJapKYTIXA0Sf4WCCSmQg%'
    OR image LIKE '%1EeG4Iw7oH6HR15Yo9waQA%';
