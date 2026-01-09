-- Migration: Email Inbound + Push Notifications tables
-- For automatic document ingestion via email and PWA push notifications

-- ═══════════════════════════════════════════════════════════════════════════════
-- Table 1: pending_document_approvals
-- Stores documents received via email waiting for user approval
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS pending_document_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
    property_name TEXT NOT NULL,
    document_hint TEXT NOT NULL,
    suggested_cajon TEXT,
    suggested_subcajon TEXT,
    suggested_document_name TEXT,
    temp_storage_path TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    content_type TEXT DEFAULT 'application/pdf',
    sender_email TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    rejection_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_pending_approvals_property ON pending_document_approvals(property_id);
CREATE INDEX IF NOT EXISTS idx_pending_approvals_status ON pending_document_approvals(status) WHERE status = 'pending';

-- RLS
ALTER TABLE pending_document_approvals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all on pending_document_approvals" ON pending_document_approvals
    FOR ALL USING (true) WITH CHECK (true);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Table 2: push_subscriptions
-- Stores Web Push subscriptions for sending notifications
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_identifier TEXT NOT NULL,
    endpoint TEXT NOT NULL UNIQUE,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE
);

-- Index for user lookups
CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user ON push_subscriptions(user_identifier);

-- RLS
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all on push_subscriptions" ON push_subscriptions
    FOR ALL USING (true) WITH CHECK (true);

-- Comments
COMMENT ON TABLE pending_document_approvals IS 'Documents received via email pending user approval before upload to Armario Digital';
COMMENT ON TABLE push_subscriptions IS 'Web Push API subscriptions for PWA notifications';

