-- ═══════════════════════════════════════════════════════════════════════════════
-- MIGRACIÓN: Estudio Económico Template System
-- Fecha: 2026-01-05
-- Descripción: Añade el campo 'item_key' a financial_items para identificar
--              cada celda de la plantilla del estudio económico.
-- ═══════════════════════════════════════════════════════════════════════════════

-- 1. Añadir columna item_key si no existe
ALTER TABLE financial_items 
ADD COLUMN IF NOT EXISTS item_key TEXT;

-- 2. Crear índice único para property_id + item_key
CREATE UNIQUE INDEX IF NOT EXISTS idx_financial_items_property_key 
ON financial_items(property_id, item_key) 
WHERE item_key IS NOT NULL;

-- 3. Añadir columna order_index para mantener el orden
ALTER TABLE financial_items 
ADD COLUMN IF NOT EXISTS order_index INTEGER DEFAULT 0;

-- 4. Añadir columna subcategory para agrupación visual
ALTER TABLE financial_items 
ADD COLUMN IF NOT EXISTS subcategory TEXT;

-- ═══════════════════════════════════════════════════════════════════════════════
-- RPC: seed_estudio_economico
-- Inicializa la plantilla del estudio económico para una propiedad
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION seed_estudio_economico(p_property_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_count INTEGER := 0;
BEGIN
    -- COMPRA DEL ACTIVO
    INSERT INTO financial_items (property_id, category, item_key, item_name, order_index)
    VALUES 
        (p_property_id, 'COMPRA', 'compra_precio', 'Precio Compra Activo', 1),
        (p_property_id, 'COMPRA', 'compra_itp', 'ITP (Impuesto Transmisiones)', 2),
        (p_property_id, 'COMPRA', 'compra_notaria', 'Notaría + Registro + Gestoría', 3),
        (p_property_id, 'COMPRA', 'compra_ibi', 'IBI Prorrateado', 4),
        (p_property_id, 'COMPRA', 'compra_gestion', 'Gestión ABOKA 1%', 5)
    ON CONFLICT (property_id, item_key) DO NOTHING;
    
    -- REFORMA
    INSERT INTO financial_items (property_id, category, item_key, item_name, subcategory, order_index)
    VALUES 
        (p_property_id, 'REFORMA', 'reforma_proyecto', 'Proyecto / Arquitecto', 'Licencias', 10),
        (p_property_id, 'REFORMA', 'reforma_licencia', 'Licencia de Obra / ICIO', 'Licencias', 11),
        (p_property_id, 'REFORMA', 'reforma_contrata', 'Contrata de Obra', 'Obra', 12),
        (p_property_id, 'REFORMA', 'reforma_cocina', 'Mobiliario Cocina + Electros', 'Materiales', 13),
        (p_property_id, 'REFORMA', 'reforma_banos', 'Sanitarios Baños + Griferías', 'Materiales', 14),
        (p_property_id, 'REFORMA', 'reforma_suelos', 'Tarima / Suelos', 'Materiales', 15),
        (p_property_id, 'REFORMA', 'reforma_carpinteria', 'Armarios y Carpintería', 'Materiales', 16),
        (p_property_id, 'REFORMA', 'reforma_ac', 'Aire Acondicionado', 'Materiales', 17),
        (p_property_id, 'REFORMA', 'reforma_otros', 'Otros Materiales', 'Materiales', 18),
        (p_property_id, 'REFORMA', 'reforma_amueblamiento', 'Amueblamiento / Home Staging', 'Decoración', 19),
        (p_property_id, 'REFORMA', 'reforma_contingencia', 'Contingencia (5-10%)', NULL, 20)
    ON CONFLICT (property_id, item_key) DO NOTHING;
    
    -- FINANCIEROS
    INSERT INTO financial_items (property_id, category, item_key, item_name, order_index)
    VALUES 
        (p_property_id, 'FINANCIERO', 'fin_constitucion', 'Gastos Constitución Hipoteca', 30),
        (p_property_id, 'FINANCIERO', 'fin_tasacion', 'Tasación Oficial', 31),
        (p_property_id, 'FINANCIERO', 'fin_intereses', 'Intereses Soportados', 32),
        (p_property_id, 'FINANCIERO', 'fin_cancelacion', 'Gastos Cancelación Hipoteca', 33),
        (p_property_id, 'FINANCIERO', 'fin_seguro', 'Seguro Multirriesgo', 34)
    ON CONFLICT (property_id, item_key) DO NOTHING;
    
    -- GESTIONES
    INSERT INTO financial_items (property_id, category, item_key, item_name, order_index)
    VALUES 
        (p_property_id, 'GESTIONES', 'gest_comunidad', 'Comunidad de Propietarios', 40),
        (p_property_id, 'GESTIONES', 'gest_ibi', 'IBI Anual', 41),
        (p_property_id, 'GESTIONES', 'gest_suministros', 'Suministros (Luz, Gas, Agua)', 42),
        (p_property_id, 'GESTIONES', 'gest_plusvalia', 'Plusvalía Municipal', 43),
        (p_property_id, 'GESTIONES', 'gest_comision', 'Comisión Agencia Venta', 44)
    ON CONFLICT (property_id, item_key) DO NOTHING;
    
    -- VENTA / INGRESOS
    INSERT INTO financial_items (property_id, category, item_key, item_name, order_index)
    VALUES 
        (p_property_id, 'VENTA', 'venta_precio', 'Precio Venta Vivienda', 50),
        (p_property_id, 'VENTA', 'venta_alquileres', 'Alquileres Temporales', 51)
    ON CONFLICT (property_id, item_key) DO NOTHING;
    
    -- Contar items creados
    SELECT COUNT(*) INTO v_count 
    FROM financial_items 
    WHERE property_id = p_property_id AND item_key IS NOT NULL;
    
    RETURN jsonb_build_object(
        'success', true,
        'message', 'Estudio económico inicializado con ' || v_count || ' celdas',
        'items_count', v_count
    );
END;
$$;

-- ═══════════════════════════════════════════════════════════════════════════════
-- RPC: get_estudio_economico
-- Obtiene todos los items del estudio económico de una propiedad
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION get_estudio_economico(p_property_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_items JSONB;
BEGIN
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', id,
            'key', item_key,
            'label', item_name,
            'category', category,
            'subcategory', subcategory,
            'estimado', COALESCE(estimated_amount, 0),
            'real', COALESCE(real_amount, 0),
            'order', order_index
        ) ORDER BY order_index
    )
    INTO v_items
    FROM financial_items
    WHERE property_id = p_property_id
      AND item_key IS NOT NULL;
    
    RETURN jsonb_build_object(
        'ok', true,
        'items', COALESCE(v_items, '[]'::jsonb)
    );
END;
$$;

-- ═══════════════════════════════════════════════════════════════════════════════
-- RPC: update_estudio_item
-- Actualiza un valor específico del estudio económico
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION update_estudio_item(
    p_property_id UUID,
    p_key TEXT,
    p_field TEXT,    -- 'estimado' or 'real'
    p_value NUMERIC
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_column TEXT;
    v_updated_id UUID;
BEGIN
    -- Map field name to column
    IF p_field = 'estimado' THEN
        v_column := 'estimated_amount';
    ELSIF p_field = 'real' THEN
        v_column := 'real_amount';
    ELSE
        RETURN jsonb_build_object('ok', false, 'error', 'Invalid field: ' || p_field);
    END IF;
    
    -- Update using dynamic SQL
    IF v_column = 'estimated_amount' THEN
        UPDATE financial_items
        SET estimated_amount = p_value,
            updated_at = NOW()
        WHERE property_id = p_property_id AND item_key = p_key
        RETURNING id INTO v_updated_id;
    ELSE
        UPDATE financial_items
        SET real_amount = p_value,
            updated_at = NOW()
        WHERE property_id = p_property_id AND item_key = p_key
        RETURNING id INTO v_updated_id;
    END IF;
    
    IF v_updated_id IS NULL THEN
        RETURN jsonb_build_object('ok', false, 'error', 'Item not found');
    END IF;
    
    RETURN jsonb_build_object(
        'ok', true,
        'updated_id', v_updated_id,
        'key', p_key,
        'field', p_field,
        'value', p_value
    );
END;
$$;

-- ═══════════════════════════════════════════════════════════════════════════════
-- Trigger: Auto-seed estudio económico cuando se crea una propiedad
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION auto_seed_estudio_on_property_create()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    PERFORM seed_estudio_economico(NEW.id);
    RETURN NEW;
END;
$$;

-- Solo crear el trigger si no existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trigger_auto_seed_estudio'
    ) THEN
        CREATE TRIGGER trigger_auto_seed_estudio
        AFTER INSERT ON properties
        FOR EACH ROW
        EXECUTE FUNCTION auto_seed_estudio_on_property_create();
    END IF;
END;
$$;

-- ═══════════════════════════════════════════════════════════════════════════════
-- Notas para el desarrollador:
-- 
-- EJECUTAR EN SUPABASE SQL EDITOR:
-- 1. Ejecutar todo este script
-- 2. Para propiedades existentes, ejecutar:
--    SELECT seed_estudio_economico('property-uuid-here');
--
-- ENDPOINTS A CREAR EN app.py:
-- GET  /api/estudio/{property_id}          -> get_estudio_economico
-- POST /api/estudio/{property_id}/update   -> update_estudio_item
-- POST /api/estudio/{property_id}/seed     -> seed_estudio_economico
-- ═══════════════════════════════════════════════════════════════════════════════

-- Verificar que todo se creó correctamente
DO $$
BEGIN
    RAISE NOTICE '✅ Migración completada:';
    RAISE NOTICE '   - Columnas añadidas: item_key, order_index, subcategory';
    RAISE NOTICE '   - Funciones: seed_estudio_economico, get_estudio_economico, update_estudio_item';
    RAISE NOTICE '   - Trigger: auto_seed_estudio_on_property_create';
END;
$$;

