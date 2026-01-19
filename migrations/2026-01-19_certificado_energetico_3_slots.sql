-- MIGRATION: Certificado Energético - 3 Slots
-- Date: 2026-01-19
-- Description: Replace single "Certificado Energético Nuevo" with 3 separate slots:
--   1. Certificado Energético - Etiqueta (required)
--   2. Certificado Energético - Informe (optional)
--   3. Certificado Energético - Medidas (optional)

-- ============================================================================
-- 1. UPDATE EXISTING SLOT: Rename "Certificado Energético Nuevo" to "Certificado Energético - Etiqueta"
-- ============================================================================

UPDATE armario_documents
SET 
    document_name = 'Certificado Energético - Etiqueta',
    is_required = TRUE,
    updated_at = NOW()
WHERE 
    cajon = 'VENTA' 
    AND subcajon = 'Dossier Comercial' 
    AND document_name = 'Certificado Energético Nuevo';

-- ============================================================================
-- 2. ADD NEW OPTIONAL SLOTS for existing properties
-- ============================================================================

-- Add "Certificado Energético - Informe" for all properties that have the Etiqueta slot
INSERT INTO armario_documents (
    id,
    property_id,
    cajon,
    subcajon,
    document_name,
    is_placeholder,
    is_uploaded,
    is_required,
    created_at,
    updated_at
)
SELECT 
    gen_random_uuid(),
    property_id,
    'VENTA',
    'Dossier Comercial',
    'Certificado Energético - Informe',
    TRUE,
    FALSE,
    FALSE,  -- Optional
    NOW(),
    NOW()
FROM armario_documents
WHERE 
    cajon = 'VENTA' 
    AND subcajon = 'Dossier Comercial' 
    AND document_name = 'Certificado Energético - Etiqueta'
ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;

-- Add "Certificado Energético - Medidas" for all properties that have the Etiqueta slot
INSERT INTO armario_documents (
    id,
    property_id,
    cajon,
    subcajon,
    document_name,
    is_placeholder,
    is_uploaded,
    is_required,
    created_at,
    updated_at
)
SELECT 
    gen_random_uuid(),
    property_id,
    'VENTA',
    'Dossier Comercial',
    'Certificado Energético - Medidas',
    TRUE,
    FALSE,
    FALSE,  -- Optional
    NOW(),
    NOW()
FROM armario_documents
WHERE 
    cajon = 'VENTA' 
    AND subcajon = 'Dossier Comercial' 
    AND document_name = 'Certificado Energético - Etiqueta'
ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;

-- ============================================================================
-- 3. UPDATE seed_armario_digital FUNCTION to include new slots
-- ============================================================================

-- Drop existing function (if exists) and recreate with new slots
CREATE OR REPLACE FUNCTION seed_armario_digital(p_property_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_count INTEGER := 0;
    v_existing INTEGER;
BEGIN
    -- Check if already seeded
    SELECT COUNT(*) INTO v_existing 
    FROM armario_documents 
    WHERE property_id = p_property_id;
    
    IF v_existing > 0 THEN
        RETURN jsonb_build_object(
            'success', TRUE,
            'message', 'Armario already seeded',
            'documents_existing', v_existing
        );
    END IF;

    -- ═══════════════════════════════════════════════════════════════════
    -- CAJÓN 1: COMPRA DEL ACTIVO
    -- ═══════════════════════════════════════════════════════════════════
    
    -- Due Diligence
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'COMPRA', 'Due Diligence', 'Nota Simple Informativa', TRUE),
        (gen_random_uuid(), p_property_id, 'COMPRA', 'Due Diligence', 'Referencia Catastral', TRUE),
        (gen_random_uuid(), p_property_id, 'COMPRA', 'Due Diligence', 'Certificado Deuda IBI', TRUE),
        (gen_random_uuid(), p_property_id, 'COMPRA', 'Due Diligence', 'Certificado Corriente Comunidad', TRUE),
        (gen_random_uuid(), p_property_id, 'COMPRA', 'Due Diligence', 'Certificado Energético Original', TRUE),
        (gen_random_uuid(), p_property_id, 'COMPRA', 'Due Diligence', 'Informe de Cargas y Gravámenes', FALSE);
    v_count := v_count + 6;
    
    -- Contrato de Compra
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'COMPRA', 'Contrato', 'Contrato de Arras / Señal', TRUE),
        (gen_random_uuid(), p_property_id, 'COMPRA', 'Contrato', 'Escritura Pública de Compraventa', TRUE);
    v_count := v_count + 2;
    
    -- Gastos de Compra
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'COMPRA', 'Gastos', 'Factura Notaría + Registro + Gestoría CPVTA', TRUE),
        (gen_random_uuid(), p_property_id, 'COMPRA', 'Gastos', 'Modelo 600 ITP Presentado', TRUE),
        (gen_random_uuid(), p_property_id, 'COMPRA', 'Gastos', 'Recibo IBI', FALSE),
        (gen_random_uuid(), p_property_id, 'COMPRA', 'Gastos', 'Gastos de Gestión 1%', FALSE);
    v_count := v_count + 4;

    -- ═══════════════════════════════════════════════════════════════════
    -- CAJÓN 2: REFORMA Y OBRA
    -- ═══════════════════════════════════════════════════════════════════
    
    -- Licencias
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Licencias', 'Proyecto Básico / Memoria Técnica', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Licencias', 'Licencia de Obra / Declaración Responsable', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Licencias', 'Tasas Urbanísticas ICIO', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Licencias', 'Licencia Ocupación Vía Pública', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Licencias', 'Contrato y Facturas Arquitecto', FALSE);
    v_count := v_count + 5;
    
    -- Contrata
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Contrata', 'Contrato Contrata de Obra', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Contrata', 'Presupuesto de Obra', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Contrata', 'Facturas Contrata de Obra', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Contrata', 'Certificaciones de Obra', FALSE);
    v_count := v_count + 4;
    
    -- Partidas (Materiales)
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Partidas', 'Factura Mobiliario Baños + Griferías', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Partidas', 'Factura Cocina Completa', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Partidas', 'Factura Carpintería + Puertas', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Partidas', 'Factura Suelos y Pavimentos', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Partidas', 'Factura Aire Acondicionado', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Partidas', 'Factura Electrodomésticos', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Partidas', 'Factura Iluminación', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Partidas', 'Factura Pintura y Acabados', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Partidas', 'Factura Cristalería / Ventanas', FALSE),
        (gen_random_uuid(), p_property_id, 'REFORMA', 'Partidas', 'Otros Materiales', FALSE);
    v_count := v_count + 10;

    -- ═══════════════════════════════════════════════════════════════════
    -- CAJÓN 3: GASTOS FINANCIEROS
    -- ═══════════════════════════════════════════════════════════════════
    
    -- Hipoteca
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'FINANCIERO', 'Hipoteca', 'Escritura Préstamo Hipotecario', FALSE),
        (gen_random_uuid(), p_property_id, 'FINANCIERO', 'Hipoteca', 'Cuadro de Amortización', FALSE),
        (gen_random_uuid(), p_property_id, 'FINANCIERO', 'Hipoteca', 'Recibos Mensuales Hipoteca', FALSE),
        (gen_random_uuid(), p_property_id, 'FINANCIERO', 'Hipoteca', 'Certificado Cancelación Hipoteca', FALSE);
    v_count := v_count + 4;
    
    -- Tasación y Seguros
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'FINANCIERO', 'Tasación', 'Informe de Tasación', FALSE),
        (gen_random_uuid(), p_property_id, 'FINANCIERO', 'Seguros', 'Póliza Seguro Multirriesgo + Vinculación', FALSE),
        (gen_random_uuid(), p_property_id, 'FINANCIERO', 'Seguros', 'Recibos Seguro Anual', FALSE);
    v_count := v_count + 3;

    -- ═══════════════════════════════════════════════════════════════════
    -- CAJÓN 4: GESTIONES Y GASTOS VARIOS
    -- ═══════════════════════════════════════════════════════════════════
    
    -- Suministros
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'GESTIONES', 'Suministros', 'Contrato Suministro Luz', FALSE),
        (gen_random_uuid(), p_property_id, 'GESTIONES', 'Suministros', 'Facturas Mensuales Luz', FALSE),
        (gen_random_uuid(), p_property_id, 'GESTIONES', 'Suministros', 'Contrato Suministro Gas', FALSE),
        (gen_random_uuid(), p_property_id, 'GESTIONES', 'Suministros', 'Facturas Mensuales Gas', FALSE),
        (gen_random_uuid(), p_property_id, 'GESTIONES', 'Suministros', 'Contrato Suministro Agua', FALSE),
        (gen_random_uuid(), p_property_id, 'GESTIONES', 'Suministros', 'Facturas Mensuales Agua', FALSE);
    v_count := v_count + 6;
    
    -- Comunidad e Impuestos
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'GESTIONES', 'Comunidad', 'Recibos Comunidad de Propietarios', FALSE),
        (gen_random_uuid(), p_property_id, 'GESTIONES', 'Comunidad', 'Actas Junta de Propietarios', FALSE),
        (gen_random_uuid(), p_property_id, 'GESTIONES', 'Impuestos', 'Plusvalía Municipal IIVTNU', FALSE),
        (gen_random_uuid(), p_property_id, 'GESTIONES', 'Impuestos', 'Modelo 210 (No Residentes)', FALSE);
    v_count := v_count + 4;
    
    -- Comisiones
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'GESTIONES', 'Comisiones', 'Factura Comisión Agencia Inmobiliaria', FALSE),
        (gen_random_uuid(), p_property_id, 'GESTIONES', 'Comisiones', 'Factura Honorarios API', FALSE);
    v_count := v_count + 2;

    -- ═══════════════════════════════════════════════════════════════════
    -- CAJÓN 5: VENTA Y COMERCIALIZACIÓN
    -- ═══════════════════════════════════════════════════════════════════
    
    -- Dossier Comercial (UPDATED: 3 Certificado Energético slots)
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'VENTA', 'Dossier Comercial', 'Renders / Infografías 3D', FALSE),
        (gen_random_uuid(), p_property_id, 'VENTA', 'Dossier Comercial', 'Fotografías Profesionales', FALSE),
        (gen_random_uuid(), p_property_id, 'VENTA', 'Dossier Comercial', 'Plano Comercial de Venta', FALSE),
        (gen_random_uuid(), p_property_id, 'VENTA', 'Dossier Comercial', 'Certificado Energético - Etiqueta', TRUE),  -- Required
        (gen_random_uuid(), p_property_id, 'VENTA', 'Dossier Comercial', 'Certificado Energético - Informe', FALSE), -- Optional
        (gen_random_uuid(), p_property_id, 'VENTA', 'Dossier Comercial', 'Certificado Energético - Medidas', FALSE), -- Optional
        (gen_random_uuid(), p_property_id, 'VENTA', 'Dossier Comercial', 'Fotografías Home Staging', FALSE);
    v_count := v_count + 7;
    
    -- Cierre de Venta
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'VENTA', 'Cierre', 'Contrato de Reserva / Oferta', FALSE),
        (gen_random_uuid(), p_property_id, 'VENTA', 'Cierre', 'Contrato de Arras (Venta)', FALSE),
        (gen_random_uuid(), p_property_id, 'VENTA', 'Cierre', 'Escritura Pública de Venta', TRUE);
    v_count := v_count + 3;
    
    -- Alquileres Temporales
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'VENTA', 'Alquileres', 'Contratos Alquiler Temporal', FALSE),
        (gen_random_uuid(), p_property_id, 'VENTA', 'Alquileres', 'Justificantes Pago Alquileres', FALSE);
    v_count := v_count + 2;

    -- ═══════════════════════════════════════════════════════════════════
    -- CAJÓN 6: RESULTADO / CIERRE
    -- ═══════════════════════════════════════════════════════════════════
    
    -- Liquidación
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'CIERRE', 'Liquidación', 'Estudio Económico de la Operación', FALSE),
        (gen_random_uuid(), p_property_id, 'CIERRE', 'Liquidación', 'Factura Honorarios ABOKA', TRUE),
        (gen_random_uuid(), p_property_id, 'CIERRE', 'Liquidación', 'Documento Liquidación Operación', FALSE);
    v_count := v_count + 3;
    
    -- Fiscal
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'CIERRE', 'Fiscal', 'Declaración IRPF Ganancias Patrimoniales', FALSE),
        (gen_random_uuid(), p_property_id, 'CIERRE', 'Fiscal', 'Declaración Impuesto Sociedades', FALSE);
    v_count := v_count + 2;
    
    -- Inversores
    INSERT INTO armario_documents (id, property_id, cajon, subcajon, document_name, is_required)
    VALUES
        (gen_random_uuid(), p_property_id, 'CIERRE', 'Inversores', 'Documento Cierre con Inversores', FALSE),
        (gen_random_uuid(), p_property_id, 'CIERRE', 'Inversores', 'Documento Reparto de Beneficios', FALSE);
    v_count := v_count + 2;

    RETURN jsonb_build_object(
        'success', TRUE,
        'message', 'Armario Digital initialized successfully',
        'documents_seeded', v_count
    );
    
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', FALSE,
        'error', SQLERRM
    );
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION seed_armario_digital(UUID) TO authenticated, anon, service_role;

-- ============================================================================
-- 4. VERIFY MIGRATION
-- ============================================================================

-- Show all Certificado Energético slots in VENTA
SELECT 
    property_id,
    document_name,
    is_required,
    is_uploaded
FROM armario_documents
WHERE 
    cajon = 'VENTA' 
    AND subcajon = 'Dossier Comercial'
    AND document_name LIKE 'Certificado Energético%'
ORDER BY property_id, document_name;

