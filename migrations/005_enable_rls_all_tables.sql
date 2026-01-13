-- ============================================================================
-- MIGRATION: Enable Row Level Security (RLS) on all tables
-- Date: January 2026
-- Description: Adds RLS policies to ensure users can only access their own data
-- ============================================================================

-- IMPORTANT: Before running this migration:
-- 1. Add 'user_id' column to 'properties' table if it doesn't exist
-- 2. Ensure Supabase Auth is enabled in your project
-- 3. Run this in Supabase SQL Editor

-- ============================================================================
-- STEP 1: Add user_id to properties table (if not exists)
-- ============================================================================

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'properties' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE properties ADD COLUMN user_id UUID REFERENCES auth.users(id);
        
        -- Create index for faster queries
        CREATE INDEX IF NOT EXISTS idx_properties_user_id ON properties(user_id);
    END IF;
END $$;

-- ============================================================================
-- STEP 2: Enable RLS on all tables
-- ============================================================================

-- Properties table
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;

-- Armario documents (linked to properties)
ALTER TABLE armario_documents ENABLE ROW LEVEL SECURITY;

-- Financial items (linked to properties)
ALTER TABLE financial_items ENABLE ROW LEVEL SECURITY;

-- Property photos (linked to properties)
ALTER TABLE property_photos ENABLE ROW LEVEL SECURITY;

-- Pending document approvals (linked to properties)
ALTER TABLE pending_document_approvals ENABLE ROW LEVEL SECURITY;

-- Push subscriptions (linked to user)
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- STEP 3: Create RLS Policies for PROPERTIES
-- ============================================================================

-- Drop existing policies if any (for clean re-run)
DROP POLICY IF EXISTS "Users can view their own properties" ON properties;
DROP POLICY IF EXISTS "Users can insert their own properties" ON properties;
DROP POLICY IF EXISTS "Users can update their own properties" ON properties;
DROP POLICY IF EXISTS "Users can delete their own properties" ON properties;

-- SELECT: Users can only see their own properties
CREATE POLICY "Users can view their own properties"
ON properties FOR SELECT
USING (auth.uid() = user_id);

-- INSERT: Users can only create properties for themselves
CREATE POLICY "Users can insert their own properties"
ON properties FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- UPDATE: Users can only update their own properties
CREATE POLICY "Users can update their own properties"
ON properties FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- DELETE: Users can only delete their own properties
CREATE POLICY "Users can delete their own properties"
ON properties FOR DELETE
USING (auth.uid() = user_id);

-- ============================================================================
-- STEP 4: Create RLS Policies for ARMARIO_DOCUMENTS
-- ============================================================================

DROP POLICY IF EXISTS "Users can view their property documents" ON armario_documents;
DROP POLICY IF EXISTS "Users can insert documents to their properties" ON armario_documents;
DROP POLICY IF EXISTS "Users can update their property documents" ON armario_documents;
DROP POLICY IF EXISTS "Users can delete their property documents" ON armario_documents;

-- SELECT: Users can only see documents from their properties
CREATE POLICY "Users can view their property documents"
ON armario_documents FOR SELECT
USING (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

-- INSERT: Users can only add documents to their properties
CREATE POLICY "Users can insert documents to their properties"
ON armario_documents FOR INSERT
WITH CHECK (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

-- UPDATE: Users can only update documents in their properties
CREATE POLICY "Users can update their property documents"
ON armario_documents FOR UPDATE
USING (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

-- DELETE: Users can only delete documents from their properties
CREATE POLICY "Users can delete their property documents"
ON armario_documents FOR DELETE
USING (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

-- ============================================================================
-- STEP 5: Create RLS Policies for FINANCIAL_ITEMS
-- ============================================================================

DROP POLICY IF EXISTS "Users can view their property financials" ON financial_items;
DROP POLICY IF EXISTS "Users can insert financials to their properties" ON financial_items;
DROP POLICY IF EXISTS "Users can update their property financials" ON financial_items;
DROP POLICY IF EXISTS "Users can delete their property financials" ON financial_items;

CREATE POLICY "Users can view their property financials"
ON financial_items FOR SELECT
USING (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

CREATE POLICY "Users can insert financials to their properties"
ON financial_items FOR INSERT
WITH CHECK (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

CREATE POLICY "Users can update their property financials"
ON financial_items FOR UPDATE
USING (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

CREATE POLICY "Users can delete their property financials"
ON financial_items FOR DELETE
USING (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

-- ============================================================================
-- STEP 6: Create RLS Policies for PROPERTY_PHOTOS
-- ============================================================================

DROP POLICY IF EXISTS "Users can view their property photos" ON property_photos;
DROP POLICY IF EXISTS "Users can insert photos to their properties" ON property_photos;
DROP POLICY IF EXISTS "Users can update their property photos" ON property_photos;
DROP POLICY IF EXISTS "Users can delete their property photos" ON property_photos;

CREATE POLICY "Users can view their property photos"
ON property_photos FOR SELECT
USING (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

CREATE POLICY "Users can insert photos to their properties"
ON property_photos FOR INSERT
WITH CHECK (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

CREATE POLICY "Users can update their property photos"
ON property_photos FOR UPDATE
USING (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

CREATE POLICY "Users can delete their property photos"
ON property_photos FOR DELETE
USING (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

-- ============================================================================
-- STEP 7: Create RLS Policies for PENDING_DOCUMENT_APPROVALS
-- ============================================================================

DROP POLICY IF EXISTS "Users can view their pending approvals" ON pending_document_approvals;
DROP POLICY IF EXISTS "Users can insert pending approvals" ON pending_document_approvals;
DROP POLICY IF EXISTS "Users can update their pending approvals" ON pending_document_approvals;
DROP POLICY IF EXISTS "Users can delete their pending approvals" ON pending_document_approvals;

CREATE POLICY "Users can view their pending approvals"
ON pending_document_approvals FOR SELECT
USING (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

CREATE POLICY "Users can insert pending approvals"
ON pending_document_approvals FOR INSERT
WITH CHECK (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

CREATE POLICY "Users can update their pending approvals"
ON pending_document_approvals FOR UPDATE
USING (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

CREATE POLICY "Users can delete their pending approvals"
ON pending_document_approvals FOR DELETE
USING (
    property_id IN (
        SELECT id FROM properties WHERE user_id = auth.uid()
    )
);

-- ============================================================================
-- STEP 8: Create RLS Policies for PUSH_SUBSCRIPTIONS
-- ============================================================================

-- Add user_id column if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'push_subscriptions' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE push_subscriptions ADD COLUMN user_id UUID REFERENCES auth.users(id);
        CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user_id ON push_subscriptions(user_id);
    END IF;
END $$;

DROP POLICY IF EXISTS "Users can view their push subscriptions" ON push_subscriptions;
DROP POLICY IF EXISTS "Users can insert their push subscriptions" ON push_subscriptions;
DROP POLICY IF EXISTS "Users can update their push subscriptions" ON push_subscriptions;
DROP POLICY IF EXISTS "Users can delete their push subscriptions" ON push_subscriptions;

CREATE POLICY "Users can view their push subscriptions"
ON push_subscriptions FOR SELECT
USING (user_id = auth.uid() OR user_id IS NULL);

CREATE POLICY "Users can insert their push subscriptions"
ON push_subscriptions FOR INSERT
WITH CHECK (user_id = auth.uid() OR user_id IS NULL);

CREATE POLICY "Users can update their push subscriptions"
ON push_subscriptions FOR UPDATE
USING (user_id = auth.uid() OR user_id IS NULL);

CREATE POLICY "Users can delete their push subscriptions"
ON push_subscriptions FOR DELETE
USING (user_id = auth.uid() OR user_id IS NULL);

-- ============================================================================
-- STEP 9: Service Role Bypass (for backend operations)
-- ============================================================================
-- Note: The backend uses SUPABASE_SERVICE_ROLE_KEY which bypasses RLS.
-- This is intentional for system operations like:
-- - Email inbound processing (no user context)
-- - Push notifications (system-wide)
-- - Background jobs

-- The SERVICE_ROLE_KEY should NEVER be exposed to the frontend.
-- Frontend should only use SUPABASE_ANON_KEY which respects RLS.

-- ============================================================================
-- VERIFICATION QUERIES (run these to verify RLS is enabled)
-- ============================================================================

-- Check RLS status on all tables:
-- SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';

-- Check policies:
-- SELECT * FROM pg_policies WHERE schemaname = 'public';

-- ============================================================================
-- ROLLBACK (if needed)
-- ============================================================================

-- To disable RLS (NOT RECOMMENDED in production):
-- ALTER TABLE properties DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE armario_documents DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE financial_items DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE property_photos DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE pending_document_approvals DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE push_subscriptions DISABLE ROW LEVEL SECURITY;

