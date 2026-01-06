-- ═══════════════════════════════════════════════════════════════════════════════
-- MIGRACIÓN: Campos de Extracción Automática para Armario Digital
-- Fecha: 2026-01-05
-- Descripción: Añade campos para la extracción automática de datos de facturas
--              y su mapeo al Estudio Económico.
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. CAMPOS DE EXTRACCIÓN
-- ─────────────────────────────────────────────────────────────────────────────

-- Datos extraídos por GPT-4 (concepto, valor, fecha, proveedor, etc.)
ALTER TABLE armario_documents 
ADD COLUMN IF NOT EXISTS extracted_data JSONB DEFAULT '{}';

-- Estado del proceso de extracción
-- 'none'             = No procesado (documento no requiere extracción)
-- 'pending'          = Pendiente de extracción
-- 'extracted'        = Datos extraídos, pendiente de mapeo
-- 'pending_approval' = Propuesto al usuario, esperando confirmación
-- 'applied'          = Usuario aceptó, valor añadido al Estudio Económico
-- 'rejected'         = Usuario rechazó la extracción
-- 'failed'           = Error en la extracción
ALTER TABLE armario_documents 
ADD COLUMN IF NOT EXISTS extraction_status TEXT DEFAULT 'none';

-- item_key del Estudio Económico al que se mapeó este documento
-- Ej: 'reforma_ac', 'compra_itp', 'fin_intereses'
ALTER TABLE armario_documents 
ADD COLUMN IF NOT EXISTS mapped_estudio_key TEXT;

-- Confianza de la extracción (0.0 - 1.0)
ALTER TABLE armario_documents 
ADD COLUMN IF NOT EXISTS extraction_confidence FLOAT;

-- Fecha de extracción
ALTER TABLE armario_documents 
ADD COLUMN IF NOT EXISTS extracted_at TIMESTAMPTZ;


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. SCHEMA DE extracted_data (Documentación)
-- ─────────────────────────────────────────────────────────────────────────────
/*
extracted_data JSONB schema:
{
    "tipo_documento": "factura" | "presupuesto" | "contrato" | "ticket" | "otro",
    "concepto_detectado": "Instalación aire acondicionado split",
    "concepto_normalizado": "Aire Acondicionado",  -- Mapeado al Estudio Económico
    "valor_total": 5000.00,
    "valor_sin_iva": 4132.23,
    "iva_porcentaje": 21,
    "fecha_documento": "2024-01-15",
    "proveedor": "Climatización Madrid SL",
    "numero_factura": "F-2024-0123",
    "descripcion_items": ["Split 1x1", "Instalación", "Materiales"],
    "modelo_extraccion": "gpt-4o",
    "prompt_version": "v1",
    "timestamp_extraccion": "2024-01-16T10:30:00Z"
}
*/


-- ─────────────────────────────────────────────────────────────────────────────
-- 3. RPC: Obtener documentos pendientes de aprobación
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION get_pending_extractions(p_property_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_docs JSONB;
BEGIN
    SELECT jsonb_agg(
        jsonb_build_object(
            'document_id', id,
            'document_name', document_name,
            'original_filename', original_filename,
            'cajon', cajon,
            'subcajon', subcajon,
            'extracted_data', extracted_data,
            'mapped_estudio_key', mapped_estudio_key,
            'extraction_confidence', extraction_confidence,
            'extracted_at', extracted_at
        ) ORDER BY extracted_at DESC
    )
    INTO v_docs
    FROM armario_documents
    WHERE property_id = p_property_id
      AND extraction_status = 'pending_approval';
    
    RETURN jsonb_build_object(
        'ok', true,
        'documents', COALESCE(v_docs, '[]'::jsonb),
        'count', (SELECT COUNT(*) FROM armario_documents 
                  WHERE property_id = p_property_id 
                  AND extraction_status = 'pending_approval')
    );
END;
$$;


-- ─────────────────────────────────────────────────────────────────────────────
-- 4. RPC: Aprobar extracción (actualizar Estudio Económico)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION approve_extraction(
    p_document_id UUID,
    p_estudio_key TEXT DEFAULT NULL  -- Si NULL, usa mapped_estudio_key
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_doc RECORD;
    v_valor NUMERIC;
    v_property_id UUID;
    v_key TEXT;
BEGIN
    -- Obtener documento
    SELECT * INTO v_doc
    FROM armario_documents
    WHERE id = p_document_id;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Document not found');
    END IF;
    
    -- Determinar el key del estudio
    v_key := COALESCE(p_estudio_key, v_doc.mapped_estudio_key);
    
    IF v_key IS NULL THEN
        RETURN jsonb_build_object('ok', false, 'error', 'No estudio key provided or mapped');
    END IF;
    
    -- Obtener valor extraído
    v_valor := (v_doc.extracted_data->>'valor_total')::NUMERIC;
    
    IF v_valor IS NULL OR v_valor <= 0 THEN
        RETURN jsonb_build_object('ok', false, 'error', 'No valid value extracted');
    END IF;
    
    v_property_id := v_doc.property_id;
    
    -- Actualizar financial_items (columna REAL)
    UPDATE financial_items
    SET real_amount = v_valor,
        updated_at = NOW()
    WHERE property_id = v_property_id
      AND item_key = v_key;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Estudio item not found: ' || v_key);
    END IF;
    
    -- Marcar documento como aplicado
    UPDATE armario_documents
    SET extraction_status = 'applied',
        importe = v_valor
    WHERE id = p_document_id;
    
    RETURN jsonb_build_object(
        'ok', true,
        'message', 'Valor aplicado al Estudio Económico',
        'estudio_key', v_key,
        'valor', v_valor
    );
END;
$$;


-- ─────────────────────────────────────────────────────────────────────────────
-- 5. RPC: Rechazar extracción
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION reject_extraction(p_document_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE armario_documents
    SET extraction_status = 'rejected'
    WHERE id = p_document_id;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Document not found');
    END IF;
    
    RETURN jsonb_build_object('ok', true, 'message', 'Extracción rechazada');
END;
$$;


-- ─────────────────────────────────────────────────────────────────────────────
-- 6. Índice para consultas de estado
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_armario_extraction_status 
ON armario_documents(property_id, extraction_status)
WHERE extraction_status != 'none';


-- ─────────────────────────────────────────────────────────────────────────────
-- Verificación
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    RAISE NOTICE '✅ Migración completada:';
    RAISE NOTICE '   - Campos añadidos: extracted_data, extraction_status, mapped_estudio_key, extraction_confidence, extracted_at';
    RAISE NOTICE '   - RPCs creadas: get_pending_extractions, approve_extraction, reject_extraction';
    RAISE NOTICE '   - Índice creado: idx_armario_extraction_status';
END;
$$;

