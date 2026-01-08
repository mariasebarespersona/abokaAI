-- Migration: Create property_photos table for storing renovation photos
-- Categories: ANTES (before renovation), DURANTE (during), DESPUES (after)

CREATE TABLE IF NOT EXISTS property_photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK (category IN ('ANTES', 'DURANTE', 'DESPUES')),
    storage_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    original_filename TEXT,
    content_type TEXT DEFAULT 'image/jpeg',
    is_featured BOOLEAN DEFAULT FALSE,
    description TEXT,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_property_photos_property_id ON property_photos(property_id);
CREATE INDEX IF NOT EXISTS idx_property_photos_category ON property_photos(property_id, category);
CREATE INDEX IF NOT EXISTS idx_property_photos_featured ON property_photos(property_id, is_featured) WHERE is_featured = TRUE;

-- RLS (Row Level Security) - Allow all operations for now
ALTER TABLE property_photos ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all operations on property_photos" ON property_photos
    FOR ALL USING (true) WITH CHECK (true);

-- Comment on table
COMMENT ON TABLE property_photos IS 'Stores renovation progress photos: ANTES (before), DURANTE (during), DESPUES (after)';
COMMENT ON COLUMN property_photos.is_featured IS 'Photos marked as featured appear in the property dashboard';

