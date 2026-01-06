-- ═══════════════════════════════════════════════════════════════════════════════
-- ABOKA AI - Armario Digital de 6 Cajones
-- Migración: Estructura de documentos para operaciones inmobiliarias
-- Fecha: 2026-01-05
-- ═══════════════════════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════════════════════════
-- PASO 1: Crear tabla principal de documentos del armario
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS armario_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    
    -- Estructura del armario: Cajón → Subcajón → Documento
    cajon TEXT NOT NULL CHECK (cajon IN (
        'COMPRA',       -- Cajón 1: Adquisición
        'REFORMA',      -- Cajón 2: Transformación
        'FINANCIERO',   -- Cajón 3: Financiación
        'GESTIONES',    -- Cajón 4: Gestión Recurrente
        'VENTA',        -- Cajón 5: Comercialización
        'CIERRE'        -- Cajón 6: Resultado Final
    )),
    
    subcajon TEXT NOT NULL,  -- Ej: "Due Diligence", "Contrata", "Hipoteca"
    
    -- Información del documento
    document_name TEXT NOT NULL,           -- Nombre canónico del documento
    document_type TEXT,                    -- Tipo específico (para filtros)
    storage_path TEXT,                     -- Path en Supabase Storage (NULL = pendiente)
    content_type TEXT,                     -- MIME type del archivo
    original_filename TEXT,                -- Nombre original del archivo subido
    
    -- Metadatos financieros (para vincular con el estudio económico)
    importe NUMERIC,                       -- Importe asociado al documento (ej: factura)
    fecha_documento DATE,                  -- Fecha del documento
    fecha_vencimiento DATE,                -- Fecha de vencimiento (facturas recurrentes)
    
    -- Estado y tracking
    is_placeholder BOOLEAN DEFAULT FALSE,  -- TRUE = celda vacía esperando documento
    is_uploaded BOOLEAN DEFAULT FALSE,     -- TRUE = archivo subido
    is_required BOOLEAN DEFAULT TRUE,      -- TRUE = documento obligatorio
    
    -- Facturas recurrentes
    parent_document_id UUID REFERENCES armario_documents(id),  -- Para facturas vinculadas a contratos
    is_recurring BOOLEAN DEFAULT FALSE,    -- TRUE = genera facturas recurrentes
    
    -- Metadata adicional (JSON flexible)
    metadata JSONB DEFAULT '{}',
    
    -- Auditoría
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT DEFAULT 'system',
    
    -- Índice único: un solo documento por celda del armario
    UNIQUE(property_id, cajon, subcajon, document_name)
);

-- Índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_armario_property ON armario_documents(property_id);
CREATE INDEX IF NOT EXISTS idx_armario_cajon ON armario_documents(cajon);
CREATE INDEX IF NOT EXISTS idx_armario_uploaded ON armario_documents(is_uploaded);
CREATE INDEX IF NOT EXISTS idx_armario_pending ON armario_documents(is_placeholder) WHERE is_placeholder = TRUE;

-- ═══════════════════════════════════════════════════════════════════════════════
-- PASO 2: Habilitar RLS (Row Level Security)
-- ═══════════════════════════════════════════════════════════════════════════════

ALTER TABLE armario_documents ENABLE ROW LEVEL SECURITY;

-- Política permisiva (ajustar para multi-tenancy en producción)
CREATE POLICY "Allow all access to armario_documents" ON armario_documents
    FOR ALL USING (true);

-- ═══════════════════════════════════════════════════════════════════════════════
-- PASO 3: Función para sembrar el armario con estructura vacía
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION seed_armario_digital(p_property_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    docs_created INT := 0;
BEGIN
    -- ═══════════════════════════════════════════════════════════════════
    -- CAJÓN 1: COMPRA DEL ACTIVO (Adquisición)
    -- ═══════════════════════════════════════════════════════════════════
    
    -- Due Diligence Pre-Compra
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'COMPRA', 'Due Diligence', 'Nota Simple Informativa', TRUE, TRUE),
        (p_property_id, 'COMPRA', 'Due Diligence', 'Referencia Catastral', TRUE, TRUE),
        (p_property_id, 'COMPRA', 'Due Diligence', 'Certificado Deuda IBI', TRUE, TRUE),
        (p_property_id, 'COMPRA', 'Due Diligence', 'Certificado Corriente Comunidad', TRUE, TRUE),
        (p_property_id, 'COMPRA', 'Due Diligence', 'Certificado Energético Original', TRUE, TRUE),
        (p_property_id, 'COMPRA', 'Due Diligence', 'Informe de Cargas y Gravámenes', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    GET DIAGNOSTICS docs_created = ROW_COUNT;
    
    -- Contrato de Compra
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'COMPRA', 'Contrato', 'Contrato de Arras / Señal', TRUE, TRUE),
        (p_property_id, 'COMPRA', 'Contrato', 'Escritura Pública de Compraventa', TRUE, TRUE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Gastos de Compra
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'COMPRA', 'Gastos', 'Factura Notaría + Registro + Gestoría CPVTA', TRUE, TRUE),
        (p_property_id, 'COMPRA', 'Gastos', 'Modelo 600 ITP Presentado', TRUE, TRUE),
        (p_property_id, 'COMPRA', 'Gastos', 'Recibo IBI', TRUE, FALSE),
        (p_property_id, 'COMPRA', 'Gastos', 'Gastos de Gestión 1%', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- ═══════════════════════════════════════════════════════════════════
    -- CAJÓN 2: REFORMA Y OBRA (Transformación)
    -- ═══════════════════════════════════════════════════════════════════
    
    -- Licencias y Proyecto
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'REFORMA', 'Licencias', 'Proyecto Básico / Memoria Técnica', TRUE, FALSE),
        (p_property_id, 'REFORMA', 'Licencias', 'Licencia de Obra / Declaración Responsable', TRUE, FALSE),
        (p_property_id, 'REFORMA', 'Licencias', 'Tasas Urbanísticas ICIO', TRUE, FALSE),
        (p_property_id, 'REFORMA', 'Licencias', 'Contrato y Facturas Arquitecto', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Contrata de Obra
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required, is_recurring)
    VALUES
        (p_property_id, 'REFORMA', 'Contrata', 'Contrato Contrata de Obra', TRUE, FALSE, TRUE),
        (p_property_id, 'REFORMA', 'Contrata', 'Presupuesto de Obra', TRUE, FALSE, FALSE),
        (p_property_id, 'REFORMA', 'Contrata', 'Certificaciones de Obra', TRUE, FALSE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Partidas de Materiales (opcional según operación)
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'REFORMA', 'Partidas', 'Factura Mobiliario Baños + Griferías', TRUE, FALSE),
        (p_property_id, 'REFORMA', 'Partidas', 'Factura Aire Acondicionado', TRUE, FALSE),
        (p_property_id, 'REFORMA', 'Partidas', 'Factura Tarima Flotante', TRUE, FALSE),
        (p_property_id, 'REFORMA', 'Partidas', 'Factura Cerámica Baños', TRUE, FALSE),
        (p_property_id, 'REFORMA', 'Partidas', 'Factura Armarios y Carpintería', TRUE, FALSE),
        (p_property_id, 'REFORMA', 'Partidas', 'Factura Mobiliario Cocina + Encimeras + Electros', TRUE, FALSE),
        (p_property_id, 'REFORMA', 'Partidas', 'Factura Puertas Cristal Interiores', TRUE, FALSE),
        (p_property_id, 'REFORMA', 'Partidas', 'Factura Contingencias y Otros', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Amueblamiento
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'REFORMA', 'Amueblamiento', 'Facturas Amueblamiento y Menaje', TRUE, FALSE),
        (p_property_id, 'REFORMA', 'Amueblamiento', 'Facturas Home Staging', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Certificados Técnicos
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'REFORMA', 'Certificados', 'Boletín Eléctrico (CIE)', TRUE, FALSE),
        (p_property_id, 'REFORMA', 'Certificados', 'Boletín Gas / RITE', TRUE, FALSE),
        (p_property_id, 'REFORMA', 'Certificados', 'Certificado Final de Obra', TRUE, FALSE),
        (p_property_id, 'REFORMA', 'Certificados', 'Garantías de Materiales', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- ═══════════════════════════════════════════════════════════════════
    -- CAJÓN 3: GASTOS FINANCIEROS (Financiación)
    -- ═══════════════════════════════════════════════════════════════════
    
    -- Hipoteca
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'FINANCIERO', 'Hipoteca', 'FEIN / FIAE Oferta Vinculante', TRUE, FALSE),
        (p_property_id, 'FINANCIERO', 'Hipoteca', 'Escritura Préstamo Hipotecario', TRUE, FALSE),
        (p_property_id, 'FINANCIERO', 'Hipoteca', 'Tasación Oficial ECO', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Gastos Constitución Hipoteca
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'FINANCIERO', 'Gastos Constitución', 'Gastos Constitución Hipoteca - Notaría', TRUE, FALSE),
        (p_property_id, 'FINANCIERO', 'Gastos Constitución', 'Gastos Constitución Hipoteca - Registro', TRUE, FALSE),
        (p_property_id, 'FINANCIERO', 'Gastos Constitución', 'Gastos Constitución Hipoteca - ITP AJD', TRUE, FALSE),
        (p_property_id, 'FINANCIERO', 'Gastos Constitución', 'Gastos Constitución Hipoteca - Gestoría', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Cancelación Hipoteca
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'FINANCIERO', 'Cancelación', 'Certificado Deuda Cero Banco', TRUE, FALSE),
        (p_property_id, 'FINANCIERO', 'Cancelación', 'Modelo 601 AJD Cancelación', TRUE, FALSE),
        (p_property_id, 'FINANCIERO', 'Cancelación', 'Gastos Cancelación Hipoteca (Total)', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Seguros
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required, is_recurring)
    VALUES
        (p_property_id, 'FINANCIERO', 'Seguros', 'Póliza Seguro Multirriesgo + Vinculación', TRUE, FALSE, TRUE),
        (p_property_id, 'FINANCIERO', 'Seguros', 'Seguro Responsabilidad Civil', TRUE, FALSE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Intereses
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'FINANCIERO', 'Intereses', 'Cuadro de Amortización', TRUE, FALSE),
        (p_property_id, 'FINANCIERO', 'Intereses', 'Justificantes Intereses Soportados', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- ═══════════════════════════════════════════════════════════════════
    -- CAJÓN 4: GASTOS VARIOS (Gestión Recurrente)
    -- ═══════════════════════════════════════════════════════════════════
    
    -- Suministros
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required, is_recurring)
    VALUES
        (p_property_id, 'GESTIONES', 'Suministros', 'Contrato Suministro Luz', TRUE, FALSE, TRUE),
        (p_property_id, 'GESTIONES', 'Suministros', 'Contrato Suministro Gas', TRUE, FALSE, TRUE),
        (p_property_id, 'GESTIONES', 'Suministros', 'Contrato Suministro Fibra/Internet', TRUE, FALSE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Comunidad
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required, is_recurring)
    VALUES
        (p_property_id, 'GESTIONES', 'Comunidad', 'Recibos Comunidad de Propietarios', TRUE, FALSE, TRUE),
        (p_property_id, 'GESTIONES', 'Comunidad', 'Certificado y Derramas', TRUE, FALSE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Impuestos
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'GESTIONES', 'Impuestos', 'Plusvalía Municipal IIVTNU', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Comisiones
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'GESTIONES', 'Comisiones', 'Factura Comisión Agencia Inmobiliaria', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- ═══════════════════════════════════════════════════════════════════
    -- CAJÓN 5: VENTA Y COMERCIALIZACIÓN (Salida)
    -- ═══════════════════════════════════════════════════════════════════
    
    -- Dossier Comercial
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'VENTA', 'Dossier Comercial', 'Renders / Infografías 3D', TRUE, FALSE),
        (p_property_id, 'VENTA', 'Dossier Comercial', 'Fotografías Profesionales', TRUE, FALSE),
        (p_property_id, 'VENTA', 'Dossier Comercial', 'Plano Comercial de Venta', TRUE, FALSE),
        (p_property_id, 'VENTA', 'Dossier Comercial', 'Certificado Energético Nuevo', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Cierre de Venta
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'VENTA', 'Cierre', 'Contrato de Reserva / Oferta', TRUE, FALSE),
        (p_property_id, 'VENTA', 'Cierre', 'Contrato de Arras (Venta)', TRUE, TRUE),
        (p_property_id, 'VENTA', 'Cierre', 'Escritura Pública de Venta', TRUE, TRUE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Alquileres Temporales
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required, is_recurring)
    VALUES
        (p_property_id, 'VENTA', 'Alquileres', 'Contratos Alquiler Temporal', TRUE, FALSE, TRUE),
        (p_property_id, 'VENTA', 'Alquileres', 'Justificantes Pago Alquileres', TRUE, FALSE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- ═══════════════════════════════════════════════════════════════════
    -- CAJÓN 6: RESULTADO / CIERRE (Control Final)
    -- ═══════════════════════════════════════════════════════════════════
    
    -- Liquidación
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'CIERRE', 'Liquidación', 'Estudio Económico de la Operación', TRUE, TRUE),
        (p_property_id, 'CIERRE', 'Liquidación', 'Factura Honorarios ABOKA', TRUE, TRUE),
        (p_property_id, 'CIERRE', 'Liquidación', 'Documento Liquidación Operación', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Fiscal
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'CIERRE', 'Fiscal', 'Declaración IRPF Ganancias Patrimoniales', TRUE, FALSE),
        (p_property_id, 'CIERRE', 'Fiscal', 'Declaración Impuesto Sociedades', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Inversores
    INSERT INTO armario_documents (property_id, cajon, subcajon, document_name, is_placeholder, is_required)
    VALUES
        (p_property_id, 'CIERRE', 'Inversores', 'Documento Cierre con Inversores', TRUE, FALSE),
        (p_property_id, 'CIERRE', 'Inversores', 'Informe de Rentabilidad Final', TRUE, FALSE)
    ON CONFLICT (property_id, cajon, subcajon, document_name) DO NOTHING;
    
    -- Contar documentos creados
    SELECT COUNT(*) INTO docs_created FROM armario_documents WHERE property_id = p_property_id;
    
    RETURN jsonb_build_object(
        'success', TRUE,
        'property_id', p_property_id,
        'documents_seeded', docs_created,
        'message', 'Armario digital inicializado con ' || docs_created || ' celdas'
    );
END;
$$;

-- ═══════════════════════════════════════════════════════════════════════════════
-- PASO 4: Función para listar documentos del armario por cajón
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION list_armario_documents(
    p_property_id UUID,
    p_cajon TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    cajon TEXT,
    subcajon TEXT,
    document_name TEXT,
    is_uploaded BOOLEAN,
    is_required BOOLEAN,
    storage_path TEXT,
    importe NUMERIC,
    fecha_documento DATE,
    original_filename TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ad.id,
        ad.cajon,
        ad.subcajon,
        ad.document_name,
        ad.is_uploaded,
        ad.is_required,
        ad.storage_path,
        ad.importe,
        ad.fecha_documento,
        ad.original_filename
    FROM armario_documents ad
    WHERE ad.property_id = p_property_id
      AND (p_cajon IS NULL OR ad.cajon = p_cajon)
    ORDER BY 
        CASE ad.cajon 
            WHEN 'COMPRA' THEN 1
            WHEN 'REFORMA' THEN 2
            WHEN 'FINANCIERO' THEN 3
            WHEN 'GESTIONES' THEN 4
            WHEN 'VENTA' THEN 5
            WHEN 'CIERRE' THEN 6
        END,
        ad.subcajon,
        ad.document_name;
END;
$$;

-- ═══════════════════════════════════════════════════════════════════════════════
-- PASO 5: Función para subir documento al armario
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION upload_armario_document(
    p_property_id UUID,
    p_cajon TEXT,
    p_subcajon TEXT,
    p_document_name TEXT,
    p_storage_path TEXT,
    p_content_type TEXT DEFAULT 'application/pdf',
    p_original_filename TEXT DEFAULT NULL,
    p_importe NUMERIC DEFAULT NULL,
    p_fecha_documento DATE DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_doc_id UUID;
BEGIN
    -- Actualizar el documento existente o insertar nuevo
    INSERT INTO armario_documents (
        property_id, cajon, subcajon, document_name,
        storage_path, content_type, original_filename,
        importe, fecha_documento,
        is_placeholder, is_uploaded, updated_at
    )
    VALUES (
        p_property_id, p_cajon, p_subcajon, p_document_name,
        p_storage_path, p_content_type, p_original_filename,
        p_importe, p_fecha_documento,
        FALSE, TRUE, NOW()
    )
    ON CONFLICT (property_id, cajon, subcajon, document_name)
    DO UPDATE SET
        storage_path = EXCLUDED.storage_path,
        content_type = EXCLUDED.content_type,
        original_filename = EXCLUDED.original_filename,
        importe = COALESCE(EXCLUDED.importe, armario_documents.importe),
        fecha_documento = COALESCE(EXCLUDED.fecha_documento, armario_documents.fecha_documento),
        is_placeholder = FALSE,
        is_uploaded = TRUE,
        updated_at = NOW()
    RETURNING id INTO v_doc_id;
    
    RETURN jsonb_build_object(
        'success', TRUE,
        'document_id', v_doc_id,
        'cajon', p_cajon,
        'subcajon', p_subcajon,
        'document_name', p_document_name,
        'storage_path', p_storage_path
    );
END;
$$;

-- ═══════════════════════════════════════════════════════════════════════════════
-- PASO 6: Función para obtener resumen del armario (progreso por cajón)
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION get_armario_summary(p_property_id UUID)
RETURNS TABLE (
    cajon TEXT,
    total_docs BIGINT,
    uploaded_docs BIGINT,
    required_docs BIGINT,
    required_uploaded BIGINT,
    completion_percentage NUMERIC
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ad.cajon,
        COUNT(*) AS total_docs,
        COUNT(*) FILTER (WHERE ad.is_uploaded = TRUE) AS uploaded_docs,
        COUNT(*) FILTER (WHERE ad.is_required = TRUE) AS required_docs,
        COUNT(*) FILTER (WHERE ad.is_required = TRUE AND ad.is_uploaded = TRUE) AS required_uploaded,
        ROUND(
            CASE 
                WHEN COUNT(*) FILTER (WHERE ad.is_required = TRUE) = 0 THEN 100
                ELSE (COUNT(*) FILTER (WHERE ad.is_required = TRUE AND ad.is_uploaded = TRUE)::NUMERIC / 
                      COUNT(*) FILTER (WHERE ad.is_required = TRUE)::NUMERIC) * 100
            END, 2
        ) AS completion_percentage
    FROM armario_documents ad
    WHERE ad.property_id = p_property_id
    GROUP BY ad.cajon
    ORDER BY 
        CASE ad.cajon 
            WHEN 'COMPRA' THEN 1
            WHEN 'REFORMA' THEN 2
            WHEN 'FINANCIERO' THEN 3
            WHEN 'GESTIONES' THEN 4
            WHEN 'VENTA' THEN 5
            WHEN 'CIERRE' THEN 6
        END;
END;
$$;

-- ═══════════════════════════════════════════════════════════════════════════════
-- PASO 7: Trigger para auto-crear armario cuando se crea una propiedad
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION auto_seed_armario_on_property_create()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Auto-sembrar el armario digital para la nueva propiedad
    PERFORM seed_armario_digital(NEW.id);
    RETURN NEW;
END;
$$;

-- Crear trigger solo si no existe
DROP TRIGGER IF EXISTS trigger_auto_seed_armario ON properties;
CREATE TRIGGER trigger_auto_seed_armario
    AFTER INSERT ON properties
    FOR EACH ROW
    EXECUTE FUNCTION auto_seed_armario_on_property_create();

-- ═══════════════════════════════════════════════════════════════════════════════
-- PASO 8: Comentarios de documentación
-- ═══════════════════════════════════════════════════════════════════════════════

COMMENT ON TABLE armario_documents IS 
'Armario Digital ABOKA - Almacena todos los documentos de una operación inmobiliaria organizados en 6 cajones';

COMMENT ON COLUMN armario_documents.cajon IS 
'Cajón principal: COMPRA, REFORMA, FINANCIERO, GESTIONES, VENTA, CIERRE';

COMMENT ON COLUMN armario_documents.subcajon IS 
'Subcajón dentro de cada cajón (ej: Due Diligence, Contrata, Hipoteca, etc.)';

COMMENT ON COLUMN armario_documents.is_placeholder IS 
'TRUE = celda vacía esperando que el usuario suba el documento';

COMMENT ON COLUMN armario_documents.is_recurring IS 
'TRUE = este documento genera facturas/recibos recurrentes (ej: contrato luz → facturas mensuales)';

-- ═══════════════════════════════════════════════════════════════════════════════
-- FIN DE MIGRACIÓN
-- ═══════════════════════════════════════════════════════════════════════════════

-- Ejecutar: SELECT seed_armario_digital('uuid-de-propiedad-existente');
-- para inicializar el armario de una propiedad existente

