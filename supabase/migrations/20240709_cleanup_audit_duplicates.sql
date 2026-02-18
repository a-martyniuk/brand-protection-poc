-- Migration: Cleanup and enforce unique listing_id in compliance_audit
-- This fixes the metric inflation issue where historical audits were being counted multiple times.

-- 1. Remove duplicates keeping only the latest audit per listing
DELETE FROM compliance_audit a
WHERE id NOT IN (
    SELECT id
    FROM (
        SELECT id, ROW_NUMBER() OVER (PARTITION BY listing_id ORDER BY processed_at DESC) as row_num
        FROM compliance_audit
    ) sub
    WHERE row_num = 1
);

-- 2. Add unique constraint to listing_id to allow upserting in the future
ALTER TABLE compliance_audit ADD CONSTRAINT unique_listing_audit UNIQUE (listing_id);
