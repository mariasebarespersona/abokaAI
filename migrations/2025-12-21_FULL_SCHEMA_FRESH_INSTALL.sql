-- ABOKA AI - DATABASE SETUP GUIDE
-- Created: 2025-12-20

-- Since you are starting with a FRESH database, you don't need to run the history of migrations one by one.
-- You can run this single file to set up the entire schema correctly.

-- ============================================================================
-- 1. ENABLE EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- 2. PROPERTIES (CORE TABLE)
-- ============================================================================

CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic Info
    name TEXT NOT NULL,
    address TEXT,
    user_id UUID,
    
    -- Status Tracking
    project_status TEXT DEFAULT 'evaluation', -- evaluation, acquisition, renovation_active, sold
    renovation_status TEXT DEFAULT 'planning', -- planning, in_progress, completed
    
    -- Legacy fields preserved for compatibility but can be reused
    asking_price NUMERIC,
    arv NUMERIC, -- Can be used as "Projected Sale Value"
    repair_estimate NUMERIC,
    
    -- Financial Summary (Flexible JSON)
    financial_summary JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all access properties" ON properties FOR ALL USING (true);

-- ============================================================================
-- 3. DOCUMENTS (CORE FOR RAG)
-- ============================================================================

CREATE TABLE IF NOT EXISTS maninos_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    
    document_type TEXT, -- 'invoice', 'budget', 'deed', 'photo'
    document_name TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    
    extracted_data JSONB DEFAULT '{}'::jsonb, -- AI extracted info
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE maninos_documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all access documents" ON maninos_documents FOR ALL USING (true);

-- ============================================================================
-- 4. RAG CHUNKS (VECTOR SEARCH)
-- ============================================================================

CREATE TABLE IF NOT EXISTS rag_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    document_id UUID REFERENCES maninos_documents(id) ON DELETE CASCADE,
    
    chunk_index INTEGER NOT NULL,
    text_content TEXT NOT NULL,
    embedding VECTOR(1536), -- OpenAI embedding size
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON rag_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
ALTER TABLE rag_chunks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all access chunks" ON rag_chunks FOR ALL USING (true);

-- ============================================================================
-- 5. SESSIONS (LANGGRAPH MEMORY)
-- ============================================================================

CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id UUID NOT NULL,
    parent_checkpoint_id UUID,
    checkpoint BYTEA NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id UUID NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    value BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

-- ============================================================================
-- 6. FINANCIAL ITEMS (ABOKA EXCEL ENGINE)
-- ============================================================================

CREATE TABLE IF NOT EXISTS financial_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    
    category TEXT NOT NULL,      -- 'Compra', 'Reforma', 'Gastos', 'Venta'
    item_name TEXT NOT NULL,     -- 'Fontanero', 'Notaría'
    
    estimated_amount NUMERIC DEFAULT 0,
    real_amount NUMERIC DEFAULT 0,
    
    real_amount_verified BOOLEAN DEFAULT FALSE,
    evidence_doc_id UUID REFERENCES maninos_documents(id) ON DELETE SET NULL,
    
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_financial_items_property ON financial_items(property_id);
ALTER TABLE financial_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all access financial" ON financial_items FOR ALL USING (true);

-- ============================================================================
-- 7. RENOVATION TIMELINE
-- ============================================================================

CREATE TABLE IF NOT EXISTS renovation_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    
    milestone_name TEXT NOT NULL,
    target_date DATE,
    actual_date DATE,
    
    status TEXT DEFAULT 'pending',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE renovation_timeline ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all access timeline" ON renovation_timeline FOR ALL USING (true);





