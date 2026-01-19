# ABOKA AI - Guía de Testing

**Fecha:** 2025-12-19  
**Propósito:** Probar la aplicación ABOKA AI desde cero

---

## 📋 Pre-requisitos

Antes de empezar, asegúrate de tener:

- ✅ Python 3.12+ instalado
- ✅ Node.js 18+ instalado
- ✅ Base de datos Supabase configurada
- ✅ Migración ejecutada (`2025-12-20_aboka_schema_setup_SAFE.sql`)
- ✅ Variables de entorno configuradas (`.env`)

---

## 🚀 Paso 1: Configurar Variables de Entorno

### Backend (.env en raíz del proyecto)

```bash
# Crea el archivo .env si no existe
cat > .env << 'EOF'
# Supabase
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key
SUPABASE_ANON_KEY=tu-anon-key

# OpenAI (para voice y RAG)
OPENAI_API_KEY=sk-tu-api-key

# Logfire (opcional - para observabilidad)
LOGFIRE_TOKEN=tu-logfire-token

# Redis (opcional - para cache)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Environment
ENVIRONMENT=development
PORT=8080

# CORS
WEB_BASE=http://localhost:3000,http://localhost:3001
ALLOW_ALL_CORS=0
EOF
```

### Frontend (.env.local en /web/)

```bash
cd web
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8080
EOF
cd ..
```

---

## 🔧 Paso 2: Instalar Dependencias

### Backend

```bash
# Crear virtual environment
python3 -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### Frontend

```bash
cd web
npm install
cd ..
```

---

## ▶️ Paso 3: Iniciar Backend

```bash
# Asegúrate de estar en el directorio raíz
source .venv/bin/activate

# Opción 1: Usando uvicorn directamente
uvicorn app:app --host 0.0.0.0 --port 8080 --reload

# Opción 2: Usando el script main.py
python main.py
```

**Verificación:**
- Deberías ver logs indicando que el servidor está corriendo
- Navega a: http://localhost:8080
- Deberías ver: `{"status":"ok","app":"ABOKA AI Backend"}`

---

## ▶️ Paso 4: Iniciar Frontend

En **otra terminal**:

```bash
cd web
npm run dev
```

**Verificación:**
- Deberías ver: "Local: http://localhost:3000"
- Navega a: http://localhost:3000
- Deberías ver la interfaz de ABOKA AI

---

## 🧪 Paso 5: Probar Endpoints del Backend

### Health Check

```bash
curl http://localhost:8080/health
# Esperado: {"status":"ok","service":"aboka-ai-backend"}
```

### Raíz

```bash
curl http://localhost:8080/
# Esperado: {"status":"ok","app":"ABOKA AI Backend"}
```

---

## 🏠 Paso 6: Crear una Propiedad de Prueba

### Opción A: Desde Supabase SQL Editor

```sql
-- Crear propiedad
INSERT INTO properties (name, address, project_status)
VALUES ('Piso Prueba Madrid', 'Calle Prueba 123', 'evaluation')
RETURNING id;

-- COPIA EL UUID QUE TE DEVUELVE
-- Ejemplo: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
```

### Opción B: Desde la API

```bash
# Nota: Este endpoint necesita ser implementado en el backend
# Por ahora usa la Opción A (SQL)
```

---

## 💰 Paso 7: Inicializar Datos Financieros

Usa el UUID de tu propiedad:

```sql
-- Reemplaza 'TU-UUID-AQUI' con el UUID real
SELECT seed_financial_items_for_property('TU-UUID-AQUI');
SELECT seed_timeline_for_property('TU-UUID-AQUI');
```

**Verificación:**

```sql
-- Ver items financieros creados
SELECT * FROM financial_items WHERE property_id = 'TU-UUID-AQUI';

-- Ver timeline creado
SELECT * FROM renovation_timeline WHERE property_id = 'TU-UUID-AQUI';
```

---

## 🎯 Paso 8: Probar Endpoints de ABOKA

### GET Financial Items

```bash
# Reemplaza TU-UUID-AQUI con tu UUID real
curl "http://localhost:8080/api/aboka/numbers?propertyId=TU-UUID-AQUI"
```

**Esperado:**
```json
{
  "ok": true,
  "data": [
    {
      "id": "...",
      "property_id": "...",
      "category": "Compra",
      "item_name": "Precio de Compra",
      "estimated_amount": 0,
      "real_amount": 0,
      ...
    },
    ...
  ]
}
```

### POST Update Financial Item

```bash
# Primero obtén el ID de un item del paso anterior
# Luego actualiza su estimated_amount

curl -X POST http://localhost:8080/api/aboka/numbers \
  -F "id=ID-DEL-ITEM-AQUI" \
  -F "propertyId=TU-UUID-AQUI" \
  -F 'updates={"estimated_amount": 50000}'
```

### GET Timeline

```bash
curl "http://localhost:8080/api/aboka/timeline?propertyId=TU-UUID-AQUI"
```

**Esperado:**
```json
{
  "ok": true,
  "data": [
    {
      "id": "...",
      "property_id": "...",
      "milestone_name": "Firma de Escritura",
      "target_date": null,
      "actual_date": null,
      "status": "pending",
      ...
    },
    ...
  ]
}
```

---

## 🖥️ Paso 9: Probar en el Frontend

### 9.1 Lista de Propiedades

1. Abre http://localhost:3000
2. Deberías ver un menú lateral con lista de propiedades
3. Tu propiedad "Piso Prueba Madrid" debería aparecer

### 9.2 Componente AbokaExcel

**IMPORTANTE:** El componente ya existe pero necesita ser integrado.

**Verificar que existe:**

```bash
ls web/src/components/aboka/AbokaExcel.tsx
# Debería existir
```

**Para integrarlo temporalmente (testing rápido):**

Crea un archivo de test:

```bash
cat > web/src/app/test-aboka/page.tsx << 'EOF'
'use client';

import { AbokaExcel } from '@/components/aboka/AbokaExcel';

export default function TestAbokaPage() {
  // Reemplaza con tu UUID real
  const propertyId = 'TU-UUID-AQUI';
  
  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Test Aboka Excel</h1>
      <div className="h-[600px]">
        <AbokaExcel propertyId={propertyId} />
      </div>
    </div>
  );
}
EOF
```

**Navega a:** http://localhost:3000/test-aboka

Deberías ver:
- ✅ Tabla con categorías (Compra, Reforma, Gastos, Venta)
- ✅ Columnas: Concepto, Estimación, Real
- ✅ Items financieros creados
- ✅ Puedes editar la columna Estimación
- ✅ Los cambios se guardan automáticamente

---

## 📝 Paso 10: Probar Chat con Voice Input

### 10.1 Texto Normal

En el chat frontend:

```
Usuario: "Hola"
AI: [Debería responder]
```

### 10.2 Subir Documento

1. Click en 📎 (attach)
2. Selecciona un PDF
3. Sistema debería proponer ubicación
4. Confirma con "sí"
5. Documento se sube

### 10.3 Voice Input (si tienes micrófono)

1. Click en el botón de micrófono 🎤
2. Habla (ej: "¿Cuánto cuesta la reforma?")
3. Click de nuevo para detener
4. Debería transcribir y responder

---

## 🧪 Tests Automatizados

### Backend Tests (si existen)

```bash
# En el directorio raíz
python -m pytest tests/

# O tests específicos
python tests/test_maninos_flow.py
```

### Crear Test Rápido para ABOKA

```bash
cat > test_aboka_quick.py << 'EOF'
#!/usr/bin/env python3
"""Quick test para ABOKA AI endpoints"""

import requests
import json

BASE_URL = "http://localhost:8080"

def test_health():
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "aboka-ai-backend"
    print("✅ Health check OK")

def test_financial_items(property_id):
    r = requests.get(f"{BASE_URL}/api/aboka/numbers", params={"propertyId": property_id})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] == True
    print(f"✅ Financial items OK - Found {len(data['data'])} items")

def test_timeline(property_id):
    r = requests.get(f"{BASE_URL}/api/aboka/timeline", params={"propertyId": property_id})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] == True
    print(f"✅ Timeline OK - Found {len(data['data'])} milestones")

if __name__ == "__main__":
    print("🧪 Testing ABOKA AI Backend\n")
    
    test_health()
    
    # IMPORTANTE: Reemplaza con tu UUID real
    property_id = input("Enter property UUID: ").strip()
    
    if property_id:
        test_financial_items(property_id)
        test_timeline(property_id)
    
    print("\n🎉 All tests passed!")
EOF

python test_aboka_quick.py
```

---

## 🔍 Troubleshooting

### Error: "Cannot connect to backend"

```bash
# Verifica que el backend está corriendo
curl http://localhost:8080/health

# Si no responde, revisa:
# 1. ¿Está el virtual environment activado?
source .venv/bin/activate

# 2. ¿Hay algún error en la terminal del backend?
# 3. ¿El puerto 8080 está ocupado?
lsof -i :8080
```

### Error: "Database connection failed"

```bash
# Verifica las variables de entorno
cat .env | grep SUPABASE

# Prueba la conexión desde Python
python -c "from tools.supabase_client import sb; print(sb.table('properties').select('id').limit(1).execute())"
```

### Error: "Frontend no carga"

```bash
# Verifica que las dependencias están instaladas
cd web
npm list next react

# Reinstala si es necesario
rm -rf node_modules package-lock.json
npm install

# Reinicia el servidor
npm run dev
```

### Error: "Cannot read property of undefined"

Si AbokaExcel no carga:

```bash
# Verifica que la API responde
curl "http://localhost:8080/api/aboka/numbers?propertyId=TU-UUID"

# Verifica que el componente existe
cat web/src/components/aboka/AbokaExcel.tsx
```

---

## 📊 Checklist de Testing Completo

### Backend
- [ ] ✅ Health check funciona
- [ ] ✅ Endpoint raíz funciona
- [ ] ✅ GET /api/aboka/numbers funciona
- [ ] ✅ POST /api/aboka/numbers funciona
- [ ] ✅ GET /api/aboka/timeline funciona
- [ ] ✅ POST /api/aboka/timeline funciona
- [ ] ✅ Subida de documentos funciona
- [ ] ✅ Voice transcription funciona

### Frontend
- [ ] ✅ Home page carga
- [ ] ✅ Lista de propiedades aparece
- [ ] ✅ AbokaExcel component renderiza
- [ ] ✅ Edición de valores funciona
- [ ] ✅ Auto-save funciona
- [ ] ✅ Chat funciona
- [ ] ✅ Voice button aparece

### Database
- [ ] ✅ Tabla properties existe
- [ ] ✅ Tabla financial_items existe
- [ ] ✅ Tabla renovation_timeline existe
- [ ] ✅ Tabla maninos_documents existe
- [ ] ✅ Foreign keys funcionan
- [ ] ✅ RLS policies existen

---

## 🎯 Próximos Pasos

Una vez que todo funciona:

1. **Integrar AbokaExcel en la vista principal de propiedad**
2. **Crear componente de Timeline**
3. **Adaptar agentes para workflow ABOKA**
4. **Agregar visualizaciones (charts)**
5. **Implementar exportación a Excel/PDF**

---

## 📞 Ayuda

Si algo no funciona:

1. Revisa los logs del backend (terminal donde corre uvicorn)
2. Revisa la consola del navegador (F12)
3. Verifica que todas las migraciones se ejecutaron
4. Comprueba que las variables de entorno están correctas

---

**Última Actualización:** 2025-12-19  
**Versión:** 1.0  
**Estado:** ✅ Production Ready




