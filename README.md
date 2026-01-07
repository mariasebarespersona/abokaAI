# ABOKA AI - Gestión Inteligente de Reformas Inmobiliarias

<div align="center">

🏗️ **Asistente conversacional con IA para gestión de reformas y flipping inmobiliario**

[![GitHub](https://img.shields.io/badge/GitHub-abokaAI-blue?style=for-the-badge&logo=github)](https://github.com/mariasebarespersona/abokaAI)
[![Version](https://img.shields.io/badge/Version-1.0-green?style=for-the-badge)](/)
[![Tech Stack](https://img.shields.io/badge/Stack-LangGraph_+_FastAPI_+_Next.js-green?style=for-the-badge)](/)

</div>

---

## 🎯 ¿Qué es ABOKA AI?

ABOKA AI es un **asistente inteligente** que ayuda a gestionar el ciclo completo de una reforma inmobiliaria a través de **conversación natural** (texto o voz). Automatiza:

- 📊 **Estudio Económico** - Control de costes estimados vs reales con ROI automático
- 📁 **Armario Digital** - Organización inteligente de documentos por categorías
- 💰 **Extracción Automática** - Los valores de facturas se extraen y añaden al Excel automáticamente
- 📧 **Envío por Email** - Comparte documentos o resúmenes con un mensaje
- 💬 **Consultas RAG** - Pregunta sobre el contenido de cualquier documento

**Caso de Uso:** Gestionar reformas inmobiliarias de principio a fin con control total de costes y documentación.

---

## ✨ Funcionalidades Principales

### **1. Estudio Económico**
Control financiero completo con dos columnas:
- **Estimado** - Valores previstos/presupuestados
- **Real** - Valores confirmados de facturas

| Categoría | Ejemplos de Conceptos |
|-----------|----------------------|
| **COMPRA** | Precio Compra, ITP, Notaría, Gestoría |
| **REFORMA** | Contrata Obra, Cocina, Baños, Aire Acond., Tarima |
| **FINANCIERO** | Hipoteca, Tasación, Intereses, Seguros |
| **GESTIONES** | IBI, Comunidad, Suministros, Plusvalía |
| **VENTA** | Precio Venta, Comisión Agencia |

**Métricas Automáticas:**
- Total Gastos (Estimado vs Real)
- Total Ingresos
- Beneficio Neto
- ROI %

### **2. Armario Digital**
Organización inteligente de documentos en "cajones":

```
📁 COMPRA (9 docs obligatorios)
   ├── Escritura propiedad
   ├── Nota simple
   ├── ITP/Impuestos
   └── ...

📁 REFORMA (21 docs)
   ├── Licencia obra
   ├── Presupuestos
   ├── Facturas materiales
   └── ...

📁 FINANCIERO (14 docs)
   ├── Escritura hipoteca
   ├── Tasación
   └── ...

📁 GESTIONES (7 docs)
📁 VENTA (9 docs)
📁 CIERRE (7 docs)
```

### **3. Extracción Automática de Facturas**
Cuando subes una factura:
1. GPT-4 Vision extrae automáticamente el valor total
2. El agente te propone añadirlo al Estudio Económico
3. Tú apruebas o rechazas
4. El valor se añade a la columna **Real**

```
📄 He detectado un valor en **factura_cocina.pdf**:
• Concepto: Mobiliario Cocina
• Importe: 8,500€
• Se añadirá a: Mobiliario Cocina + Electros (columna Real)

¿Lo añado?
```

### **4. Dashboard de Propiedad**
Vista resumen con:
- Progreso de documentación (X/70 docs)
- Documentos obligatorios completados
- Resumen financiero (Gastos, Ingresos, Beneficio, ROI)
- Estado por categoría

### **5. Envío de Documentos por Email**
```
Usuario: "Mándame la factura del aire acondicionado a cliente@email.com"
```
El agente busca el documento, lo adjunta y envía el email automáticamente.

### **6. Consultas RAG sobre Documentos**
```
Usuario: "¿Qué dice la factura de la cocina?"
Usuario: "¿Cuánto me costó el aire acondicionado según la factura?"
Usuario: "¿Qué materiales incluye el presupuesto?"
```
El agente lee el documento y responde basándose en su contenido.

### **7. Entrada por Voz**
- 🎤 Botón de micrófono estilo ChatGPT
- Transcripción con OpenAI Whisper
- Funciona para cualquier comando

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│  Next.js 14 + React + Tailwind CSS + TypeScript                 │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Dashboard   │  │   Estudio    │  │   Armario    │          │
│  │  Propiedad   │  │  Económico   │  │   Digital    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Chat Panel (Texto + Voz)                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓ HTTP/REST
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND API                                │
│  FastAPI + Python 3.12                                          │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   ORCHESTRATOR                              │ │
│  │  • Routing inteligente                                      │ │
│  │  • Gestión de sesiones por propiedad                       │ │
│  │  • Procesamiento de voz (Whisper)                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  PROPERTY AGENT                             │ │
│  │  Agente especializado en gestión de reformas               │ │
│  │  • Estudio Económico                                        │ │
│  │  • Armario Digital                                          │ │
│  │  • Extracción de facturas                                   │ │
│  │  • RAG sobre documentos                                     │ │
│  │  • Envío de emails                                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    HERRAMIENTAS                             │ │
│  │  • update_estudio_economico / get_estudio_economico        │ │
│  │  • search_armario_documents / send_armario_document_email  │ │
│  │  • query_armario_document (RAG)                            │ │
│  │  • get_pending_extractions / approve_extraction            │ │
│  │  • list_armario / get_armario_summary                      │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                     DATOS & ALMACENAMIENTO                       │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Supabase   │  │   OpenAI     │  │   Resend     │          │
│  │  (Postgres)  │  │   GPT-4o     │  │   (Email)    │          │
│  │              │  │   Whisper    │  │              │          │
│  │  properties  │  │   Vision     │  │              │          │
│  │  armario_doc │  │              │  │              │          │
│  │  financial_  │  │              │  │              │          │
│  │    items     │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐                                               │
│  │   Storage    │                                               │
│  │ (S3-compat)  │                                               │
│  │  Documentos  │                                               │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### **Backend**
- **Framework:** FastAPI (Python 3.12)
- **AI Orchestration:** LangGraph (LangChain)
- **LLMs:** GPT-4o-mini (agente), GPT-4 Vision (extracción)
- **Transcripción:** OpenAI Whisper
- **Database:** Supabase (PostgreSQL)
- **Storage:** Supabase Storage
- **Email:** Resend

### **Frontend**
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Icons:** Lucide React
- **Excel Export:** xlsx library

---

## 📦 Instalación

### **Requisitos**
- Python 3.12+
- Node.js 18+
- Cuenta Supabase
- API Key OpenAI
- API Key Resend (para emails)

### **1. Clonar Repositorio**
```bash
git clone https://github.com/mariasebarespersona/abokaAI.git
cd abokaAI
```

### **2. Backend**

```bash
# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env

# Editar .env con tus credenciales:
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
OPENAI_API_KEY=your_openai_api_key
RESEND_API_KEY=your_resend_api_key

# Iniciar servidor
uvicorn app:app --host 0.0.0.0 --port 8080
```

### **3. Frontend**

```bash
cd web

# Instalar dependencias
npm install

# Configurar API URL
echo "NEXT_PUBLIC_API_URL=http://localhost:8080" > .env.local

# Iniciar servidor de desarrollo
npm run dev
```

**Frontend:** http://localhost:3001  
**Backend:** http://localhost:8080

---

## 🚀 Uso Rápido

### **1. Crear Propiedad**
Haz clic en "Nueva Evaluación" y proporciona nombre y dirección.

### **2. Añadir Estimaciones**
```
Usuario: "El precio de compra es 800.000 euros"
Usuario: "La reforma costará unos 95.000 euros"
Usuario: "Queremos vender por 1.200.000"
```

### **3. Subir Documentos**
Ve al Armario Digital y sube facturas, presupuestos, escrituras...

### **4. Aprobar Extracciones**
Cuando subes una factura, el agente te propone añadir el valor al Excel:
```
Usuario: "Sí, añádelo"
```

### **5. Consultar Documentos**
```
Usuario: "¿Qué dice la factura del aire acondicionado?"
Usuario: "¿Cuánto me costó la cocina?"
```

### **6. Enviar por Email**
```
Usuario: "Mándame la factura de la cocina a cliente@email.com"
```

### **7. Exportar Excel**
Haz clic en el botón "Excel" en el Estudio Económico para descargar.

---

## 📊 Base de Datos

### **Tablas Principales**

#### **properties**
```sql
- id (uuid)
- name, address
- project_status, renovation_status
- acquisition_stage
- created_at, updated_at
```

#### **financial_items** (Estudio Económico)
```sql
- id (uuid)
- property_id (uuid)
- category (COMPRA, REFORMA, FINANCIERO, GESTIONES, VENTA)
- key (concepto normalizado)
- label (nombre visible)
- estimado (numeric)
- real (numeric)
- is_formula (boolean)
```

#### **armario_documents**
```sql
- id (uuid)
- property_id (uuid)
- cajon (COMPRA, REFORMA, FINANCIERO, GESTIONES, VENTA, CIERRE)
- subcajon (opcional)
- document_name
- is_required (boolean)
- is_uploaded (boolean)
- storage_path
- extracted_data (jsonb)
```

---

## 🎯 Comandos del Agente

### **Estudio Económico**
```
"El precio de compra es X euros"
"La reforma costará X"
"Añade X al concepto Y"
"¿Cuál es el beneficio esperado?"
"¿Cuánto llevo gastado?"
```

### **Documentos**
```
"¿Qué documentos tengo subidos?"
"¿Qué falta por subir?"
"¿Qué dice la factura de...?"
```

### **Email**
```
"Mándame la factura de X a email@ejemplo.com"
"Envía el presupuesto a..."
```

### **Extracciones**
```
"¿Hay facturas pendientes de aprobar?"
"Aprueba la extracción"
"Rechaza ese valor"
```

---

## 📝 Estructura del Proyecto

```
aboka-ai/
├── app.py                    # FastAPI main application
├── agents/
│   ├── property_agent.py     # Agente principal de reformas
│   └── base_agent.py         # Clase base para agentes
├── tools/
│   ├── registry.py           # Registro de todas las herramientas
│   ├── docs_tools.py         # Herramientas de documentos
│   ├── extraction_tools.py   # Extracción de facturas
│   ├── email_tool.py         # Envío de emails
│   └── supabase_client.py    # Cliente de base de datos
├── prompts/
│   └── agents/
│       └── property_agent/
│           └── _base.md      # Prompt del agente
├── web/                      # Frontend Next.js
│   └── src/
│       ├── app/
│       │   └── page.tsx      # Página principal
│       └── components/
│           └── aboka/
│               ├── AbokaExcel.tsx        # Estudio Económico
│               ├── ArmarioDigital.tsx    # Armario Digital
│               ├── PropertyDashboard.tsx # Dashboard
│               └── ChatPanel.tsx         # Panel de chat
└── requirements.txt
```

---

## 🔮 Roadmap

- [ ] **RAG con Embeddings** - Búsqueda vectorial para documentos grandes
- [ ] **Comparativa de Propiedades** - Analizar múltiples reformas
- [ ] **Alertas por Email** - Notificaciones de cambios
- [ ] **App Móvil** - iOS/Android
- [ ] **Multi-usuario** - Equipos de trabajo
- [ ] **Integraciones** - Bancos, inmobiliarias, APIs de mercado

---

## 📄 Licencia

Propietario - Todos los derechos reservados

---

<div align="center">

**ABOKA AI - Gestión de Reformas Inmobiliarias**  
**Versión 1.0 - Enero 2026**

🏗️ **Tu asistente de reformas con IA** 🏗️

</div>
