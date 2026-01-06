-- ABOKA AI SCHEMA SETUP (SAFE VERSION - Fresh Install)
-- Date: 2025-12-20
-- Description: Setup ABOKA AI schema from scratch
-- This version is safe for fresh installations without MANINOS legacy

-- ============================================================================
-- 1. ENSURE PROPERTIES TABLE EXISTS WITH ALL NEEDED COLUMNS
-- ============================================================================

-- Create properties table if it doesn't exist
CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    address TEXT,
    user_id UUID,
    
    -- Financial data
    asking_price NUMERIC,
    market_value NUMERIC,
    arv NUMERIC,
    repair_estimate NUMERIC,
    
    -- Status fields
    acquisition_stage TEXT,  -- Legacy/optional field
    project_status TEXT DEFAULT 'evaluation',  -- ABOKA main field
    title_status TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add columns if they don't exist (for existing properties tables)
DO $$
BEGIN
    -- Add project_status if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'properties' AND column_name = 'project_status') THEN
        ALTER TABLE properties ADD COLUMN project_status TEXT DEFAULT 'evaluation';
    END IF;
    
    -- Add acquisition_stage if missing (for compatibility)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'properties' AND column_name = 'acquisition_stage') THEN
        ALTER TABLE properties ADD COLUMN acquisition_stage TEXT;
    END IF;
    
    -- Add other optional fields
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'properties' AND column_name = 'user_id') THEN
        ALTER TABLE properties ADD COLUMN user_id UUID;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'properties' AND column_name = 'name') THEN
        ALTER TABLE properties ADD COLUMN name TEXT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'properties' AND column_name = 'address') THEN
        ALTER TABLE properties ADD COLUMN address TEXT;
    END IF;
END $$;

-- ============================================================================
-- 2. CREATE DOCUMENTS TABLE
-- ============================================================================

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

-- Index for fast retrieval
CREATE INDEX IF NOT EXISTS idx_maninos_documents_property 
ON maninos_documents(property_id);

-- ============================================================================
-- 3. CREATE FINANCIAL ITEMS (Aboka Excel)
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
    
    -- Verification & Evidence
    real_amount_verified BOOLEAN DEFAULT FALSE,
    evidence_doc_id UUID REFERENCES maninos_documents(id) ON DELETE SET NULL,
    
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast retrieval
CREATE INDEX IF NOT EXISTS idx_financial_items_property 
ON financial_items(property_id);

-- ============================================================================
-- 4. CREATE RENOVATION TIMELINE
-- ============================================================================

CREATE TABLE IF NOT EXISTS renovation_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    
    milestone_name TEXT NOT NULL,
    target_date DATE,
    actual_date DATE,
    
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'delayed')),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast retrieval
CREATE INDEX IF NOT EXISTS idx_timeline_property 
ON renovation_timeline(property_id);

-- ============================================================================
-- 5. ENABLE ROW LEVEL SECURITY
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE maninos_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE renovation_timeline ENABLE ROW LEVEL SECURITY;

-- Create permissive policies (MVP - later restrict by user_id)
DO $$
BEGIN
    -- Properties policy
    BEGIN
        CREATE POLICY "Allow all access properties" ON properties FOR ALL USING (true);
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    -- Documents policy
    BEGIN
        CREATE POLICY "Allow all access maninos_documents" ON maninos_documents FOR ALL USING (true);
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    -- Financial items policy
    BEGIN
        CREATE POLICY "Allow all access financial" ON financial_items FOR ALL USING (true);
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    -- Timeline policy
    BEGIN
        CREATE POLICY "Allow all access timeline" ON renovation_timeline FOR ALL USING (true);
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
END $$;

-- ============================================================================
-- 6. ADD SEED DATA FOR FINANCIAL ITEMS (Optional)
-- ============================================================================

-- This function can be called to initialize financial items for a new property
CREATE OR REPLACE FUNCTION seed_financial_items_for_property(p_property_id UUID)
RETURNS void AS $$
BEGIN
    -- Compra items
    INSERT INTO financial_items (property_id, category, item_name, estimated_amount)
    VALUES 
        (p_property_id, 'Compra', 'Precio de Compra', 0),
        (p_property_id, 'Compra', 'Notaría', 0),
        (p_property_id, 'Compra', 'Registro', 0),
        (p_property_id, 'Compra', 'Gestoría', 0);
    
    -- Reforma items
    INSERT INTO financial_items (property_id, category, item_name, estimated_amount)
    VALUES 
        (p_property_id, 'Reforma', 'Electricidad', 0),
        (p_property_id, 'Reforma', 'Fontanería', 0),
        (p_property_id, 'Reforma', 'Pintura', 0),
        (p_property_id, 'Reforma', 'Suelos', 0);
    
    -- Gastos items
    INSERT INTO financial_items (property_id, category, item_name, estimated_amount)
    VALUES 
        (p_property_id, 'Gastos', 'IBI', 0),
        (p_property_id, 'Gastos', 'Comunidad', 0),
        (p_property_id, 'Gastos', 'Seguros', 0),
        (p_property_id, 'Gastos', 'Licencias', 0);
    
    -- Venta items
    INSERT INTO financial_items (property_id, category, item_name, estimated_amount)
    VALUES 
        (p_property_id, 'Venta', 'Precio de Venta', 0),
        (p_property_id, 'Venta', 'Comisión Inmobiliaria', 0);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 7. ADD SEED DATA FOR TIMELINE (Optional)
-- ============================================================================

-- This function can be called to initialize timeline for a new property
CREATE OR REPLACE FUNCTION seed_timeline_for_property(p_property_id UUID)
RETURNS void AS $$
BEGIN
    INSERT INTO renovation_timeline (property_id, milestone_name, status)
    VALUES 
        (p_property_id, 'Firma de Escritura', 'pending'),
        (p_property_id, 'Inicio de Obra', 'pending'),
        (p_property_id, 'Fin de Obra', 'pending'),
        (p_property_id, 'Puesta en Venta', 'pending'),
        (p_property_id, 'Venta Cerrada', 'pending');
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VERIFICATION QUERY
-- ============================================================================

-- Run this to verify everything was created correctly:
-- SELECT table_name, column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name IN ('properties', 'maninos_documents', 'financial_items', 'renovation_timeline')
-- ORDER BY table_name, ordinal_position;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ ABOKA AI Schema Setup Complete!';
    RAISE NOTICE '📊 Tables created: properties, maninos_documents, financial_items, renovation_timeline';
    RAISE NOTICE '🔐 Row Level Security enabled on all tables';
    RAISE NOTICE '🎉 You can now use the ABOKA AI backend!';
    RAISE NOTICE '';
    RAISE NOTICE '📝 To seed data for a property, run:';
    RAISE NOTICE '   SELECT seed_financial_items_for_property(''your-property-id'');';
    RAISE NOTICE '   SELECT seed_timeline_for_property(''your-property-id'');';
END $$;

