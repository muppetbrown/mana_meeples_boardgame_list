# Performance Monitoring SQL Queries
**Quick Reference for Database Performance Analysis**

---

## Index Usage Analysis

### Check Index Usage Statistics
```sql
-- See which indexes are being used and how often
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE tablename = 'boardgames'
ORDER BY idx_scan DESC;

-- Expected: New indexes should have idx_scan > 0 after queries
```

### Find Unused Indexes
```sql
-- Indexes that are never used (candidates for removal)
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE tablename = 'boardgames'
  AND idx_scan = 0
  AND indexname NOT LIKE '%pkey%'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Index Effectiveness
```sql
-- Compare sequential scans vs index scans
SELECT 
    schemaname,
    tablename,
    seq_scan as sequential_scans,
    seq_tup_read as seq_rows_read,
    idx_scan as index_scans,
    idx_tup_fetch as idx_rows_fetched,
    CASE 
        WHEN seq_scan + idx_scan > 0 
        THEN ROUND(100.0 * idx_scan / (seq_scan + idx_scan), 2)
        ELSE 0
    END as index_usage_percent
FROM pg_stat_user_tables
WHERE tablename = 'boardgames';

-- Target: index_usage_percent > 95%
```

---

## Query Performance Analysis

### Enable Query Statistics (One-Time Setup)
```sql
-- Install pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Enable query logging
ALTER DATABASE mana_meeples 
SET log_statement = 'all';

-- Set slow query threshold
ALTER DATABASE mana_meeples 
SET log_min_duration_statement = 50;  -- Log queries > 50ms
```

### View Slow Queries
```sql
-- Top 20 slowest queries by average execution time
SELECT 
    query,
    calls,
    ROUND(total_exec_time::numeric, 2) as total_time_ms,
    ROUND(mean_exec_time::numeric, 2) as avg_time_ms,
    ROUND(max_exec_time::numeric, 2) as max_time_ms,
    ROUND(stddev_exec_time::numeric, 2) as stddev_time_ms,
    ROUND(100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0), 2) as cache_hit_ratio
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
  AND mean_exec_time > 10  -- Only queries averaging > 10ms
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Focus on: High mean_exec_time with high calls (biggest impact)
```

### Query Plan Analysis
```sql
-- Explain query plans for common queries

-- Example 1: Category filter with rating sort
EXPLAIN ANALYZE
SELECT * FROM boardgames 
WHERE mana_meeple_category = 'CORE_STRATEGY'
  AND (status = 'OWNED' OR status IS NULL)
ORDER BY average_rating DESC NULLS LAST
LIMIT 24;

-- Look for:
-- ✅ Index Scan (good)
-- ✅ Index Only Scan (excellent - covering index)
-- ⚠️ Seq Scan (needs index)
-- ⚠️ Sort operation (expensive - needs indexed sort)

-- Example 2: Designer search
EXPLAIN ANALYZE
SELECT * FROM boardgames 
WHERE designers @> '["Jamey Stegmaier"]'::jsonb
  AND (status = 'OWNED' OR status IS NULL)
LIMIT 24;

-- Should use: idx_designers_gin (GIN index)

-- Example 3: Player count filter with expansion support
EXPLAIN ANALYZE
SELECT bg.* 
FROM boardgames bg
WHERE (
    -- Base game supports player count
    (bg.players_min IS NULL OR bg.players_min <= 4)
    AND (bg.players_max IS NULL OR bg.players_max >= 4)
  ) OR (
    -- Or has expansion that supports player count
    bg.id IN (
        SELECT base_game_id 
        FROM boardgames exp
        WHERE exp.base_game_id IS NOT NULL
          AND (exp.modifies_players_min IS NULL OR exp.modifies_players_min <= 4)
          AND (exp.modifies_players_max IS NULL OR exp.modifies_players_max >= 4)
    )
  )
  AND (bg.status = 'OWNED' OR bg.status IS NULL)
LIMIT 24;
```

---

## Cache Performance

### Database Cache Hit Ratio
```sql
-- Overall cache hit ratio (target: > 99%)
SELECT 
    ROUND(
        100.0 * sum(blks_hit) / NULLIF(sum(blks_hit) + sum(blks_read), 0), 
        2
    ) as cache_hit_ratio,
    sum(blks_hit) as cache_hits,
    sum(blks_read) as disk_reads
FROM pg_stat_database
WHERE datname = current_database();

-- If < 99%, consider increasing shared_buffers
```

### Table Cache Hit Ratio
```sql
-- Cache hit ratio per table
SELECT 
    relname as table_name,
    heap_blks_read + idx_blks_read as disk_reads,
    heap_blks_hit + idx_blks_hit as cache_hits,
    CASE 
        WHEN heap_blks_hit + idx_blks_hit + heap_blks_read + idx_blks_read > 0
        THEN ROUND(
            100.0 * (heap_blks_hit + idx_blks_hit) / 
            (heap_blks_hit + idx_blks_hit + heap_blks_read + idx_blks_read),
            2
        )
        ELSE 0
    END as cache_hit_ratio
FROM pg_statio_user_tables
WHERE schemaname = 'public'
ORDER BY cache_hit_ratio ASC;

-- boardgames table should have > 99% hit ratio
```

---

## Connection Pool Monitoring

### Active Connections
```sql
-- Current connection stats
SELECT 
    COUNT(*) as total_connections,
    COUNT(*) FILTER (WHERE state = 'active') as active,
    COUNT(*) FILTER (WHERE state = 'idle') as idle,
    COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
    COUNT(*) FILTER (WHERE wait_event_type IS NOT NULL) as waiting
FROM pg_stat_activity
WHERE datname = current_database();

-- Monitor: idle_in_transaction should be 0 (indicates hanging transactions)
```

### Connection Pool Usage
```sql
-- See which clients are connected
SELECT 
    application_name,
    client_addr,
    state,
    COUNT(*) as connection_count,
    MAX(EXTRACT(EPOCH FROM (now() - query_start))) as longest_query_seconds
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid != pg_backend_pid()
GROUP BY application_name, client_addr, state
ORDER BY connection_count DESC;

-- FastAPI/Uvicorn should show pool_size + max_overflow connections max
```

---

## Table Statistics

### Table Size and Bloat
```sql
-- Table and index sizes
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size,
    ROUND(
        100.0 * (pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) / 
        NULLIF(pg_total_relation_size(schemaname||'.'||tablename), 0),
        2
    ) as index_ratio_percent
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Row Count and Estimates
```sql
-- Accurate row counts
SELECT 
    tablename,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) as dead_ratio_percent,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;

-- If dead_ratio_percent > 10%, consider VACUUM
```

---

## Performance Benchmarks

### Benchmark Common Queries (Before/After)

```sql
-- Clear cache to get realistic cold-cache performance
DISCARD ALL;

-- Benchmark 1: Category filter + sort (most common query)
EXPLAIN (ANALYZE, BUFFERS, TIMING)
SELECT id, title, thumbnail_url, year, players_min, players_max, average_rating
FROM boardgames 
WHERE mana_meeple_category = 'CORE_STRATEGY'
  AND (status = 'OWNED' OR status IS NULL)
  AND NOT (is_expansion = true AND expansion_type = 'requires_base')
ORDER BY average_rating DESC NULLS LAST
LIMIT 24;

-- Record: Execution Time

-- Benchmark 2: Designer search
EXPLAIN (ANALYZE, BUFFERS, TIMING)
SELECT id, title, thumbnail_url
FROM boardgames 
WHERE designers @> '["Jamey Stegmaier"]'::jsonb
  AND (status = 'OWNED' OR status IS NULL)
LIMIT 24;

-- Record: Execution Time

-- Benchmark 3: Player count filter
EXPLAIN (ANALYZE, BUFFERS, TIMING)
SELECT id, title, thumbnail_url, players_min, players_max
FROM boardgames 
WHERE (players_min IS NULL OR players_min <= 4)
  AND (players_max IS NULL OR players_max >= 4)
  AND (status = 'OWNED' OR status IS NULL)
LIMIT 24;

-- Record: Execution Time

-- Benchmark 4: Full-text search
EXPLAIN (ANALYZE, BUFFERS, TIMING)
SELECT id, title, thumbnail_url, description
FROM boardgames 
WHERE (
    title ILIKE '%wingspan%'
    OR CAST(designers AS TEXT) ILIKE '%wingspan%'
    OR description ILIKE '%wingspan%'
  )
  AND (status = 'OWNED' OR status IS NULL)
LIMIT 24;

-- Record: Execution Time
```

### Automated Performance Report
```sql
-- Generate performance summary report
WITH query_stats AS (
    SELECT 
        COUNT(*) as total_queries,
        SUM(calls) as total_calls,
        ROUND(AVG(mean_exec_time)::numeric, 2) as avg_exec_time,
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY mean_exec_time)::numeric, 2) as p95_exec_time,
        ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY mean_exec_time)::numeric, 2) as p99_exec_time
    FROM pg_stat_statements
    WHERE query NOT LIKE '%pg_stat_statements%'
),
cache_stats AS (
    SELECT 
        ROUND(100.0 * sum(blks_hit) / NULLIF(sum(blks_hit) + sum(blks_read), 0), 2) as cache_hit_ratio
    FROM pg_stat_database
    WHERE datname = current_database()
),
connection_stats AS (
    SELECT 
        COUNT(*) as total_connections,
        COUNT(*) FILTER (WHERE state = 'active') as active_connections
    FROM pg_stat_activity
    WHERE datname = current_database()
),
table_stats AS (
    SELECT 
        COUNT(*) as total_tables,
        SUM(n_live_tup) as total_rows,
        pg_size_pretty(SUM(pg_total_relation_size(schemaname||'.'||tablename))) as total_size
    FROM pg_stat_user_tables
    WHERE schemaname = 'public'
)
SELECT 
    'Database Performance Report' as report_type,
    current_database() as database,
    NOW() as generated_at,
    json_build_object(
        'queries', json_build_object(
            'total_unique', q.total_queries,
            'total_executions', q.total_calls,
            'avg_time_ms', q.avg_exec_time,
            'p95_time_ms', q.p95_exec_time,
            'p99_time_ms', q.p99_exec_time
        ),
        'cache', json_build_object(
            'hit_ratio_percent', c.cache_hit_ratio
        ),
        'connections', json_build_object(
            'total', conn.total_connections,
            'active', conn.active_connections
        ),
        'tables', json_build_object(
            'count', t.total_tables,
            'total_rows', t.total_rows,
            'total_size', t.total_size
        )
    ) as metrics
FROM query_stats q, cache_stats c, connection_stats conn, table_stats t;
```

---

## Performance Alerts

### Set Up Alerts (Using pg_stat_monitor or similar)

```sql
-- Alert 1: Slow queries detected
SELECT 
    'ALERT: Slow Query Detected' as alert,
    query,
    calls,
    ROUND(mean_exec_time::numeric, 2) as avg_time_ms,
    ROUND(max_exec_time::numeric, 2) as max_time_ms
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- > 100ms average
  AND calls > 10  -- Called more than 10 times
ORDER BY mean_exec_time DESC;

-- Alert 2: Cache hit ratio low
SELECT 
    'ALERT: Low Cache Hit Ratio' as alert,
    relname as table_name,
    ROUND(
        100.0 * (heap_blks_hit + idx_blks_hit) / 
        NULLIF(heap_blks_hit + idx_blks_hit + heap_blks_read + idx_blks_read, 0),
        2
    ) as cache_hit_ratio
FROM pg_statio_user_tables
WHERE (heap_blks_hit + idx_blks_hit + heap_blks_read + idx_blks_read) > 1000
  AND (
      100.0 * (heap_blks_hit + idx_blks_hit) / 
      NULLIF(heap_blks_hit + idx_blks_hit + heap_blks_read + idx_blks_read, 0)
  ) < 95;

-- Alert 3: High dead tuple ratio (needs VACUUM)
SELECT 
    'ALERT: High Dead Tuple Ratio' as alert,
    tablename,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) as dead_ratio_percent,
    last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
  AND (100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0)) > 10
ORDER BY dead_ratio_percent DESC;

-- Alert 4: Connection pool exhaustion
SELECT 
    'ALERT: High Connection Count' as alert,
    COUNT(*) as total_connections,
    COUNT(*) FILTER (WHERE state = 'active') as active,
    COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
FROM pg_stat_activity
WHERE datname = current_database()
HAVING COUNT(*) > 30  -- Threshold: pool_size + max_overflow
  OR COUNT(*) FILTER (WHERE state = 'idle in transaction') > 5;
```

---

## Maintenance Commands

### Regular Maintenance

```sql
-- Analyze tables (updates statistics for query planner)
ANALYZE boardgames;
ANALYZE buy_list_games;
ANALYZE price_snapshots;
ANALYZE sleeves;

-- Vacuum to reclaim dead tuple space
VACUUM ANALYZE boardgames;

-- Reindex if indexes become bloated (rare, but useful after bulk operations)
REINDEX TABLE boardgames;

-- Reset statistics (useful for benchmarking)
SELECT pg_stat_reset();
SELECT pg_stat_statements_reset();
```

---

## Usage Examples

### Daily Performance Check
```bash
# Run daily performance report
psql -d mana_meeples -f performance_report.sql > daily_report_$(date +%Y%m%d).txt

# Check for alerts
psql -d mana_meeples -c "
    SELECT * FROM (
        -- Slow queries
        SELECT 'SLOW_QUERY' as alert_type, query, mean_exec_time as value
        FROM pg_stat_statements
        WHERE mean_exec_time > 100 AND calls > 10
        ORDER BY mean_exec_time DESC
        LIMIT 5
    ) alerts
"
```

### Before/After Comparison
```bash
# Before optimization
psql -d mana_meeples -c "SELECT pg_stat_reset()"
psql -d mana_meeples -c "SELECT pg_stat_statements_reset()"

# Run workload (simulate traffic)
# ...

# Collect metrics
psql -d mana_meeples -f performance_report.sql > before_optimization.txt

# After optimization
# (same process)
psql -d mana_meeples -f performance_report.sql > after_optimization.txt

# Compare results
diff before_optimization.txt after_optimization.txt
```

---

**Document Version:** 1.0  
**Last Updated:** January 2, 2026  
**Status:** Ready for Use
