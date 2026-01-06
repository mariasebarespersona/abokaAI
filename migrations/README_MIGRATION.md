# ABOKA AI - Database Migration Guide

## Error: "column acquisition_stage does not exist"

Si recibes este error, es porque estás comenzando con una base de datos fresca (sin MANINOS previo).

## Solución: Usa el script SAFE

### Opción 1: Script Seguro (Recomendado)

Usa este script que es 100% seguro para instalaciones frescas:

```sql
\i migrations/2025-12-20_aboka_schema_setup_SAFE.sql
```

Este script:
- ✅ Crea todas las tablas necesarias
- ✅ No asume que existen columnas legacy
- ✅ Funciona con base de datos fresca o existente
- ✅ Incluye funciones de seed data

### Opción 2: Script Original (Actualizado)

El script original ha sido actualizado y ahora también debería funcionar:

```sql
\i migrations/2025-12-20_aboka_schema_setup.sql
```

## Qué hace la migración

### Tablas Creadas

1. **`properties`** (si no existe)
   - Campos básicos: id, name, address
   - Campos financieros: asking_price, market_value, arv, repair_estimate
   - **`project_status`** (NUEVO) - Estado del proyecto ABOKA
   - `acquisition_stage` (opcional, para compatibilidad)

2. **`maninos_documents`** (si no existe)
   - Almacena todos los documentos
   - Funciona para MANINOS y ABOKA

3. **`financial_items`** (NUEVA)
   - Motor del "Aboka Excel"
   - Categorías: Compra, Reforma, Gastos, Venta
   - Campos: estimated_amount, real_amount
   - Verificación con documentos

4. **`renovation_timeline`** (NUEVA)
   - Milestones del proyecto
   - target_date, actual_date
   - status: pending, in_progress, completed, delayed

### Funciones Auxiliares

El script SAFE incluye dos funciones útiles:

```sql
-- Inicializar items financieros para una propiedad
SELECT seed_financial_items_for_property('property-uuid-here');

-- Inicializar timeline para una propiedad
SELECT seed_timeline_for_property('property-uuid-here');
```

## Verificar que funcionó

Después de ejecutar el script, verifica con:

```sql
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name IN ('properties', 'maninos_documents', 'financial_items', 'renovation_timeline')
ORDER BY table_name, ordinal_position;
```

Deberías ver todas las tablas y columnas listadas.

## Valores de project_status

Los valores válidos para `project_status` son:

- `evaluation` - Evaluación inicial de propiedad (DEFAULT)
- `acquisition` - Propiedad en proceso de compra
- `renovation_planning` - Planificando la reforma
- `renovation_active` - Reforma en curso
- `marketing` - Propiedad en venta
- `sold` - Propiedad vendida

## Ejemplo de Uso

### 1. Crear una propiedad

```sql
INSERT INTO properties (name, address, project_status)
VALUES ('Piso Madrid Centro', 'Calle Gran Vía 28', 'evaluation')
RETURNING id;
```

### 2. Inicializar datos

```sql
-- Usa el UUID que te devolvió el INSERT anterior
SELECT seed_financial_items_for_property('tu-uuid-aqui');
SELECT seed_timeline_for_property('tu-uuid-aqui');
```

### 3. Verificar

```sql
-- Ver items financieros
SELECT * FROM financial_items WHERE property_id = 'tu-uuid-aqui';

-- Ver timeline
SELECT * FROM renovation_timeline WHERE property_id = 'tu-uuid-aqui';
```

## Troubleshooting

### Error: "table properties does not exist"

Si la tabla `properties` no existe, el script la creará automáticamente.

### Error: "relation maninos_documents does not exist"

El script SAFE crea esta tabla automáticamente. Si usas el script original, asegúrate de que está actualizado.

### Error: "duplicate key violates unique constraint"

Si ves errores de políticas duplicadas, es normal - el script los maneja con `EXCEPTION WHEN duplicate_object`.

### Error en foreign key

Asegúrate de ejecutar el script completo en orden. Las tablas se crean en el orden correcto para respetar las foreign keys.

## Siguiente Paso

Una vez completada la migración:

1. ✅ Reinicia el backend (si está corriendo)
2. ✅ Verifica que los endpoints funcionan:
   ```bash
   curl "http://localhost:8080/api/aboka/numbers?propertyId=your-id"
   curl "http://localhost:8080/api/aboka/timeline?propertyId=your-id"
   ```
3. ✅ Integra el componente `AbokaExcel.tsx` en el frontend

## Soporte

Si aún tienes problemas:

1. Verifica que tienes permisos en Supabase
2. Comprueba que la tabla `properties` existe antes de ejecutar
3. Ejecuta el script línea por línea para identificar dónde falla
4. Revisa los logs de Supabase para ver el error exacto

---

**Última Actualización:** 2025-12-19  
**Versión del Script:** 2.0 (SAFE)

