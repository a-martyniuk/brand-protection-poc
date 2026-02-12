-- Migration: Add status to compliance_audit for frontend tracking
ALTER TABLE public.compliance_audit ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'PENDING';
