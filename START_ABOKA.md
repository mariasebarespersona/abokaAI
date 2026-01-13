# 🚀 Cómo Iniciar ABOKA AI

## ✅ Estado: READY TO START

El backend de ABOKA AI ha sido adaptado exitosamente y está listo para iniciar.

---

## 🔧 Paso 1: Activar Virtual Environment

```bash
cd /Users/mariasebares/Documents/RAMA_AI/aboka-ai
source .venv/bin/activate
```

---

## ▶️ Paso 2: Iniciar Backend

```bash
# Opción 1: Usar main.py
python main.py

# Opción 2: Usar uvicorn directamente
uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

Deberías ver:
```
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
INFO:     Started reloader process
```

---

## 🧪 Paso 3: Probar el Backend

En otra terminal:

```bash
# Health check
curl http://localhost:8080/health
# Esperado: {"status":"ok","service":"aboka-ai-backend"}

# Home
curl http://localhost:8080/
# Esperado: {"status":"ok","app":"ABOKA AI Backend"}
```

---

## 💾 Paso 4: Crear Propiedad de Prueba

Ve a Supabase SQL Editor y ejecuta:

```sql
-- Crear propiedad
INSERT INTO properties (name, address, project_status)
VALUES ('Piso Prueba ABOKA', 'Calle Test 123, Madrid', 'evaluation')
RETURNING id, name;

-- GUARDA EL UUID QUE TE DEVUELVE
```

---

## 📊 Paso 5: Inicializar Datos

Usando el UUID de tu propiedad:

```sql
-- Reemplaza 'TU-UUID-AQUI' con el UUID real
SELECT seed_financial_items_for_property('TU-UUID-AQUI');
SELECT seed_timeline_for_property('TU-UUID-AQUI');
```

---

## 🎯 Paso 6: Probar Endpoints ABOKA

```bash
# Reemplaza con tu UUID real
export PROPERTY_ID="TU-UUID-AQUI"

# Get financial items
curl "http://localhost:8080/api/aboka/numbers?propertyId=$PROPERTY_ID"

# Get timeline
curl "http://localhost:8080/api/aboka/timeline?propertyId=$PROPERTY_ID"
```

---

## 🖥️ Paso 7: Iniciar Frontend (Opcional)

En otra terminal:

```bash
cd /Users/mariasebares/Documents/RAMA_AI/aboka-ai/web

# Verificar .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8080" > .env.local

# Instalar dependencias si es necesario
npm install

# Iniciar frontend
npm run dev
```

Navega a: http://localhost:3000

---

## ⚠️ Notas Importantes

### DATABASE_URL Warning
Si ves este warning:
```
WARNING:agentic:⚠️  DATABASE_URL not found! Using local checkpoint fallback...
```

**Esto es NORMAL y la app funciona**. Añade esto a tu `.env` para eliminarlo:

```bash
DATABASE_URL=postgresql://postgres:[password]@db.tdmoslqfavtybathdnnv.supabase.co:5432/postgres
```

### Funciones Deprecadas
Algunas funciones de MANINOS han sido deprecadas:
- `get_numbers` → Use ABOKA `/api/aboka/numbers`
- `set_number` → Use ABOKA `/api/aboka/numbers` (POST)
- `set_numbers_table_cell_tool` → Use ABOKA API directamente

Estas funciones ahora retornan un mensaje de deprecated.

---

## 🐛 Troubleshooting

### Error: "Address already in use"
```bash
# Buscar proceso usando puerto 8080
lsof -i :8080

# Matar proceso
kill -9 PID
```

### Error: "Module not found"
```bash
# Reinstalar dependencias
pip install -r requirements.txt --force-reinstall
```

### Backend no responde
```bash
# Ver logs
tail -f /tmp/aboka-backend.log

# Verificar que está corriendo
ps aux | grep uvicorn
```

---

## ✅ Checklist de Inicio

- [ ] Virtual environment activado
- [ ] Backend corriendo en puerto 8080
- [ ] Health check responde
- [ ] Propiedad de prueba creada
- [ ] Datos inicializados (financial_items, timeline)
- [ ] Endpoints ABOKA responden
- [ ] (Opcional) Frontend corriendo en puerto 3000

---

## 📚 Documentación Adicional

- **Testing Guide**: `docs/TESTING_GUIDE.md`
- **Migration Guide**: `migrations/README_MIGRATION.md`
- **Adaptation Summary**: `docs/ABOKA_ADAPTATION_SUMMARY.md`

---

**¡Listo para empezar a usar ABOKA AI! 🎉**



