#!/bin/bash
# Direct SQL test to check pagination issues
# This script tests the exact SQL queries that would be executed

echo "==================================="
echo "Testing Pagination Issue - SQL Direct"
echo "==================================="

# Note: You'll need to run this with database credentials
# Example: DATABASE_URL="postgresql://..." bash test_pagination_sql.sh

# Test 1: Count query for "all" category
echo ""
echo "Test 1: Count ALL games (should match total in API)"
echo "---------------------------------------------------"
echo "SELECT COUNT(id) FROM boardgames
WHERE (status = 'OWNED' OR status IS NULL)
AND NOT (is_expansion = TRUE AND expansion_type = 'requires_base');"

# Test 2: Count with pagination for pages 17-19
echo ""
echo "Test 2: Items on page 17 (offset 192, limit 12)"
echo "------------------------------------------------"
echo "SELECT id, title FROM boardgames
WHERE (status = 'OWNED' OR status IS NULL)
AND NOT (is_expansion = TRUE AND expansion_type = 'requires_base')
ORDER BY title ASC
OFFSET 192 LIMIT 12;"

echo ""
echo "Test 3: Items on page 18 (offset 204, limit 12)"
echo "------------------------------------------------"
echo "SELECT id, title FROM boardgames
WHERE (status = 'OWNED' OR status IS NULL)
AND NOT (is_expansion = TRUE AND expansion_type = 'requires_base')
ORDER BY title ASC
OFFSET 204 LIMIT 12;"

echo ""
echo "Test 4: Items on page 19 (offset 216, limit 12)"
echo "------------------------------------------------"
echo "SELECT id, title FROM boardgames
WHERE (status = 'OWNED' OR status IS NULL)
AND NOT (is_expansion = TRUE AND expansion_type = 'requires_base')
ORDER BY title ASC
OFFSET 216 LIMIT 12;"

echo ""
echo "Test 5: Count PARTY_ICEBREAKERS (should be 61)"
echo "------------------------------------------------"
echo "SELECT COUNT(id) FROM boardgames
WHERE (status = 'OWNED' OR status IS NULL)
AND NOT (is_expansion = TRUE AND expansion_type = 'requires_base')
AND mana_meeple_category = 'PARTY_ICEBREAKERS';"

echo ""
echo "Test 6: PARTY_ICEBREAKERS page 5 (offset 48, limit 12)"
echo "--------------------------------------------------------"
echo "SELECT id, title FROM boardgames
WHERE (status = 'OWNED' OR status IS NULL)
AND NOT (is_expansion = TRUE AND expansion_type = 'requires_base')
AND mana_meeple_category = 'PARTY_ICEBREAKERS'
ORDER BY title ASC
OFFSET 48 LIMIT 12;"

echo ""
echo "Test 7: PARTY_ICEBREAKERS page 6 (offset 60, limit 12)"
echo "--------------------------------------------------------"
echo "SELECT id, title FROM boardgames
WHERE (status = 'OWNED' OR status IS NULL)
AND NOT (is_expansion = TRUE AND expansion_type = 'requires_base')
AND mana_meeple_category = 'PARTY_ICEBREAKERS'
ORDER BY title ASC
OFFSET 60 LIMIT 12;"

echo ""
echo "==================================="
echo "NOTE: Copy these SQL queries and run them directly"
echo "against your PostgreSQL database to verify results"
echo "==================================="
