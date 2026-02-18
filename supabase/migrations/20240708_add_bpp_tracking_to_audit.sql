-- Migration: Add BPP Tracking Columns to Compliance Audit
-- Adds support for tracking MercadoLibre Brand Protection Program reporting status.

ALTER TABLE compliance_audit 
ADD COLUMN IF NOT EXISTS bpp_status TEXT DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS bpp_complaint_id TEXT,
ADD COLUMN IF NOT EXISTS bpp_reason_id TEXT;

COMMENT ON COLUMN compliance_audit.bpp_status IS 'Status of the BPP report: pending, reported, rejected, etc.';
COMMENT ON COLUMN compliance_audit.bpp_complaint_id IS 'External ID returned by Meli BPP API';
COMMENT ON COLUMN compliance_audit.bpp_reason_id IS 'Meli BPP motive code used for the report';
