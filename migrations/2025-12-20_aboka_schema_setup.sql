-- ABOKA AI SCHEMA SETUP
-- Date: 2025-12-20
-- Description: Transition from Maninos (Acquisition) to Aboka (Renovation/Flipping)
-- Author: Senior Database Architect

-- ============================================================================
-- 1. SETUP PROPERTIES TABLE
-- ============================================================================

-- Remove old Maninos constraints that block the new flow (if they exist)
DO $$ 
BEGIN 
    -- Drop acquisition_stage check if exists
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'properties_acquisition_stage_check') THEN
        ALTER TABLE properties DROP CONSTRAINT properties_acquisition_stage_check;
    END IF;
    
    -- Drop status check if exists (too rigid for flipping)
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'properties_status_check') THEN
        ALTER TABLE properties DROP CONSTRAINT properties_status_check;
    END IF;
END $$;

-- Add acquisition_stage column if it doesn't exist (for backward compatibility)
ALTER TABLE properties ADD COLUMN IF NOT EXISTS acquisition_stage TEXT;

-- Add new Project Status for Flipping lifecycle
-- Values: evaluation, acquisition, renovation_planning, renovation_active, marketing, sold
ALTER TABLE properties ADD COLUMN IF NOT EXISTS project_status TEXT DEFAULT 'evaluation';

-- Ensure basic fields exist (just in case)
ALTER TABLE properties ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS user_id UUID; -- For potential future auth linkage
ALTER TABLE properties ADD COLUMN IF NOT EXISTS asking_price NUMERIC;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS market_value NUMERIC;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS arv NUMERIC;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS repair_estimate NUMERIC;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS title_status TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE properties ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- ============================================================================
-- 2. CREATE DOCUMENTS TABLE (if not exists)
-- ============================================================================

-- Create maninos_documents table if it doesn't exist
-- This table stores all documents (works for both MANINOS and ABOKA)
CREATE TABLE IF NOT EXISTS maninos_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    document_type TEXT NOT NULL,
    document_name TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    content_type TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast retrieval by property
CREATE INDEX IF NOT EXISTS idx_maninos_documents_property ON maninos_documents(property_id);

-- Enable RLS
ALTER TABLE maninos_documents ENABLE ROW LEVEL SECURITY;

-- Policy: Allow all for now (MVP)
DO $$
BEGIN
    -- Drop policy if exists to avoid duplicates
    DROP POLICY IF EXISTS "Allow all access maninos_documents" ON maninos_documents;
    
    -- Create policy
    CREATE POLICY "Allow all access maninos_documents" ON maninos_documents FOR ALL USING (true);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- 3. CREATE FINANCIAL ITEMS (The "Aboka Excel" Engine)
-- ============================================================================

CREATE TABLE IF NOT EXISTS financial_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    
    -- Categorization
    category TEXT NOT NULL,      -- 'Compra', 'Reforma', 'Gastos', 'Venta'
    item_name TEXT NOT NULL,     -- 'Fontanero', 'Notaría', 'Licencia'
    
    -- The Core Comparison: Estimate vs Real
    estimated_amount NUMERIC DEFAULT 0,
    real_amount NUMERIC DEFAULT 0,
    
    -- Verification & Evidence (The "Audit" layer)
    real_amount_verified BOOLEAN DEFAULT FALSE,
    evidence_doc_id UUID REFERENCES maninos_documents(id) ON DELETE SET NULL, -- Links to the Invoice/Receipt PDF
    
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast retrieval by property (Excel view)
CREATE INDEX IF NOT EXISTS idx_financial_items_property ON financial_items(property_id);

-- ============================================================================
-- 4. RENOVATION TIMELINE (Simple Milestones)
-- ============================================================================

CREATE TABLE IF NOT EXISTS renovation_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    
    milestone_name TEXT NOT NULL, -- 'Firma Escritura', 'Inicio Obra', 'Fin Obra', 'Puesta en Venta'
    target_date DATE,
    actual_date DATE,
    
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'delayed')),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_timeline_property ON renovation_timeline(property_id);

-- ============================================================================
-- 5. ADD COMMENTS TO COLUMNS (Documentation)
-- ============================================================================

-- Document the purpose of columns
DO $$
BEGIN
    -- Only add comments if columns exist
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'properties' AND column_name = 'acquisition_stage') THEN
        COMMENT ON COLUMN properties.acquisition_stage IS 'OPTIONAL: Legacy Maninos stage or custom workflow stage. Use project_status for ABOKA flow.';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'properties' AND column_name = 'arv') THEN
        COMMENT ON COLUMN properties.arv IS 'After Repair Value (ARV). Can be used as Projected Sale Value in ABOKA.';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'properties' AND column_name = 'project_status') THEN
        COMMENT ON COLUMN properties.project_status IS 'ABOKA project phase: evaluation, acquisition, renovation_planning, renovation_active, marketing, sold';
    END IF;
END $$;

-- ============================================================================
-- 6. ENABLE RLS (Security Best Practice)
-- ============================================================================

ALTER TABLE financial_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE renovation_timeline ENABLE ROW LEVEL SECURITY;

-- Policy: Allow all for now (MVP), later restrict by user_id
DO $$
BEGIN
    -- Drop policies if they exist to avoid duplicates
    DROP POLICY IF EXISTS "Allow all access financial" ON financial_items;
    DROP POLICY IF EXISTS "Allow all access timeline" ON renovation_timeline;
    
    -- Create policies
    CREATE POLICY "Allow all access financial" ON financial_items FOR ALL USING (true);
    CREATE POLICY "Allow all access timeline" ON renovation_timeline FOR ALL USING (true);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

