# 🔒 SECURITY REVIEW - ABOKA AI

> **Fecha:** Enero 2026  
> **Estado:** Análisis completado, implementación pendiente  
> **Prioridad:** Alta - implementar antes de producción con usuarios reales

---

## 📊 RESUMEN EJECUTIVO

| Área | Estado Actual | Riesgo | Prioridad |
|------|---------------|--------|-----------|
| **Autenticación** | ❌ No existe | 🔴 CRÍTICO | P0 |
| **Autorización** | ❌ No existe | 🔴 CRÍTICO | P0 |
| **Rate Limiting** | ❌ No implementado | 🟠 ALTO | P1 |
| **Input Validation** | ⚠️ Parcial | 🟠 ALTO | P1 |
| **CORS** | ⚠️ Muy permisivo | 🟡 MEDIO | P2 |
| **Secrets Management** | ✅ En .gitignore | 🟢 BAJO | ✓ |
| **SQL Injection** | ✅ Usa ORM/RPC | 🟢 BAJO | ✓ |
| **XSS** | ✅ No usa innerHTML | 🟢 BAJO | ✓ |
| **Security Headers** | ❌ No configurados | 🟡 MEDIO | P2 |
| **Logging/Monitoring** | ⚠️ Básico (Logfire) | 🟡 MEDIO | P3 |

---

## 🔴 VULNERABILIDADES CRÍTICAS

### 1. SIN AUTENTICACIÓN - CUALQUIERA PUEDE ACCEDER

**Estado actual:**
```python
# app.py - Todos los 84 endpoints son PÚBLICOS
@app.post("/ui_chat")  # ❌ Sin auth
@app.get("/api/properties")  # ❌ Sin auth
@app.post("/api/approvals/{id}/approve")  # ❌ Sin auth
```

**Impacto:** Un atacante puede:
- Ver TODAS las propiedades y datos financieros de todos los usuarios
- Modificar/eliminar cualquier documento
- Aprobar documentos sin autorización
- Acceder a información sensible (precios, contratos, facturas)

**Solución recomendada - Supabase Auth:**

```python
# Backend: app.py
from fastapi import Depends, HTTPException, Header
from supabase import create_client

async def verify_token(authorization: str = Header(...)):
    """Verify Supabase JWT token"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid token format")
    
    token = authorization.replace("Bearer ", "")
    
    # Verify with Supabase
    user = supabase.auth.get_user(token)
    if not user:
        raise HTTPException(401, "Invalid or expired token")
    
    return user

@app.get("/api/properties")
async def get_properties(user = Depends(verify_token)):
    # Solo devuelve propiedades de ESTE usuario
    return sb.table("properties").select("*").eq("user_id", user.id).execute()
```

```typescript
// Frontend: web/src/lib/supabase.ts
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

export const supabase = createClientComponentClient()

// Login
await supabase.auth.signInWithPassword({ email, password })

// All API calls include token automatically
```

### 2. SIN AUTORIZACIÓN - NO HAY OWNERSHIP CHECK

**Estado actual:**
```python
# Cualquiera puede ver cualquier propiedad
@app.get("/api/property/{property_id}")
async def get_property(property_id: str):
    return sb.table("properties").select("*").eq("id", property_id).execute()
    # ❌ No verifica si el usuario es dueño de esta propiedad
```

**Solución - Row Level Security (RLS) en Supabase:**

```sql
-- En Supabase SQL Editor:
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only see their own properties"
ON properties FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can only update their own properties"
ON properties FOR UPDATE
USING (auth.uid() = user_id);

CREATE POLICY "Users can only delete their own properties"
ON properties FOR DELETE
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own properties"
ON properties FOR INSERT
WITH CHECK (auth.uid() = user_id);
```

---

## 🟠 VULNERABILIDADES ALTAS

### 3. SIN RATE LIMITING

**Estado actual:** Sin límites - un atacante puede:
- Hacer 1000 requests/segundo
- Agotar la cuota de OpenAI ($$$)
- Crashear el servidor (DDoS)

**Solución:**

```python
# requirements.txt
slowapi==0.1.9

# app.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"error": "Too many requests. Please wait."}
    )

@app.post("/ui_chat")
@limiter.limit("10/minute")  # Max 10 mensajes por minuto
async def chat(request: Request):
    ...

@app.post("/api/email/inbound")
@limiter.limit("100/hour")  # Max 100 emails por hora
async def email_inbound(request: Request):
    ...
```

### 4. CORS MUY PERMISIVO

**Estado actual:**
```python
cors_origins = ["*"] if allow_all else cors_env.split(",")
# Y después añade "https://*.vercel.app" - ¡cualquier app en Vercel!
```

**Solución:**
```python
# Solo dominios específicos
ALLOWED_ORIGINS = [
    "https://aboka-ai.vercel.app",  # Producción
    "https://aboka-ai-git-main-*.vercel.app",  # Solo TUS previews
]

if os.getenv("ENVIRONMENT") == "development":
    ALLOWED_ORIGINS.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

## 🟡 MEJORAS DE SEGURIDAD IMPORTANTES

### 5. Security Headers

```javascript
// web/next.config.js
const securityHeaders = [
  {
    key: 'X-DNS-Prefetch-Control',
    value: 'on'
  },
  {
    key: 'Strict-Transport-Security',
    value: 'max-age=63072000; includeSubDomains; preload'
  },
  {
    key: 'X-Frame-Options',
    value: 'SAMEORIGIN'
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  },
  {
    key: 'Referrer-Policy',
    value: 'origin-when-cross-origin'
  },
  {
    key: 'Content-Security-Policy',
    value: "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:;"
  }
];

module.exports = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: securityHeaders,
      },
    ]
  }
}
```

### 6. Input Validation con Pydantic

```python
from pydantic import BaseModel, EmailStr, constr, validator
from uuid import UUID
from typing import Optional

class ApproveDocumentRequest(BaseModel):
    cajon: constr(max_length=50)
    subcajon: constr(max_length=50)
    document_name: constr(max_length=200)
    
    @validator('cajon')
    def validate_cajon(cls, v):
        allowed = ['COMPRA', 'REFORMA', 'FINANCIERO', 'GESTIONES', 'VENTA', 'CIERRE']
        if v not in allowed:
            raise ValueError(f'cajon must be one of {allowed}')
        return v

class CreatePropertyRequest(BaseModel):
    name: constr(min_length=1, max_length=200)
    address: Optional[constr(max_length=500)] = None

@app.post("/api/approvals/{approval_id}/approve")
async def approve(
    approval_id: UUID, 
    body: ApproveDocumentRequest, 
    user = Depends(verify_token)
):
    ...
```

### 7. Webhook Signature Verification

```python
import hmac
import hashlib

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC signature from webhook"""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.post("/api/email/inbound-cloudflare")
async def email_webhook(request: Request):
    signature = request.headers.get("X-Webhook-Signature")
    body = await request.body()
    
    if not verify_webhook_signature(body, signature, WEBHOOK_SECRET):
        raise HTTPException(401, "Invalid webhook signature")
    
    # Process webhook...
```

---

## 🏗️ ARQUITECTURA DE SEGURIDAD RECOMENDADA

```
┌─────────────────────────────────────────────────────────────────┐
│                         USUARIOS                                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CLOUDFLARE (CDN + WAF)                       │
│  • DDoS Protection (automático)                                 │
│  • Bot Protection                                               │
│  • Rate Limiting a nivel DNS                                    │
│  • SSL/TLS termination                                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│   VERCEL (Frontend) │         │  RAILWAY (Backend)  │
│   ✅ HTTPS only     │         │  ✅ HTTPS only      │
│   ✅ CSP headers    │         │  ✅ Rate limiting   │
│   ✅ Auth UI        │◄───────►│  ✅ JWT validation  │
└─────────────────────┘         └──────────┬──────────┘
                                           │
                                           ▼
                               ┌─────────────────────┐
                               │     SUPABASE        │
                               │  ✅ RLS enabled     │
                               │  ✅ Auth service    │
                               │  ✅ Encrypted data  │
                               │  ✅ Backup diario   │
                               └─────────────────────┘
```

---

## 📋 PLAN DE IMPLEMENTACIÓN

### FASE 1 - Crítico (1-2 semanas)

| Task | Esfuerzo | Impacto |
|------|----------|---------|
| Implementar Supabase Auth | 3-4 días | 🔴 Bloquea acceso no autorizado |
| Añadir RLS a todas las tablas | 1-2 días | 🔴 Aísla datos por usuario |
| Verificar ownership en endpoints | 1 día | 🔴 Previene acceso horizontal |

**Tablas que necesitan RLS:**
- `properties` - user_id
- `armario_documents` - via property_id → user_id
- `financial_items` - via property_id → user_id
- `property_photos` - via property_id → user_id
- `pending_document_approvals` - via property_id → user_id
- `push_subscriptions` - user_identifier

### FASE 2 - Alto (1 semana)

| Task | Esfuerzo | Impacto |
|------|----------|---------|
| Implementar rate limiting | 1 día | 🟠 Previene abuse |
| Webhook signature verification | 1 día | 🟠 Previene spoofing |
| Input validation con Pydantic | 2 días | 🟠 Previene injection |

### FASE 3 - Medio (ongoing)

| Task | Esfuerzo | Impacto |
|------|----------|---------|
| Security headers | 2 horas | 🟡 Hardening |
| Restringir CORS | 1 hora | 🟡 Reduce superficie |
| Audit logging | 1 día | 🟡 Forensics |
| Dependency scanning (Snyk/Dependabot) | 2 horas | 🟡 Supply chain |

---

## 💰 COSTOS DE SEGURIDAD

| Servicio | Costo Actual | Con Seguridad |
|----------|--------------|---------------|
| Supabase | Free/Pro $25 | Mismo (Auth incluido) |
| Cloudflare | Free | Free (WAF Pro = $20/mes opcional) |
| Railway | ~$5-20 | Mismo |
| Vercel | Free/Pro | Mismo |

**Total adicional:** $0-20/mes (la seguridad básica es GRATIS con Supabase Auth + RLS)

---

## 🏆 COMPARATIVA DE STACKS - SILICON VALLEY

### Qué usan las startups exitosas:

| Empresa | Stack | Valoración |
|---------|-------|------------|
| **Linear** | Supabase → PostgreSQL | $400M+ |
| **Resend** | PostgreSQL + Clerk | $100M+ |
| **Vercel** | PlanetScale + Clerk | $2.5B |
| **Cal.com** | PlanetScale + Next-Auth | $100M+ |

### Comparativa de opciones:

#### SUPABASE ✅ (Recomendado - Ya lo usamos)

```
PROS:
✅ PostgreSQL real (no propietario) - puedes migrar cuando quieras
✅ Auth, Storage, Realtime incluidos - todo en uno
✅ RLS (Row Level Security) nativo - seguridad declarativa
✅ Open source - puedes self-host si creces
✅ $25/mes tier Pro - muy económico
✅ Edge Functions (Deno)
✅ Backups automáticos
✅ Comunidad activa, buena documentación

CONTRAS:
⚠️ Cold starts en funciones (mejorando)
⚠️ Límites en free tier (500MB, 50K MAU)
⚠️ No tan maduro como AWS/GCP (pero suficiente para 99% de startups)
```

#### FIREBASE (Google)

```
PROS:
✅ Muy maduro, battle-tested
✅ Real-time excelente
✅ Auth muy pulido

CONTRAS:
❌ NoSQL (Firestore) - difícil para queries complejos
❌ Vendor lock-in total - NO puedes migrar fácilmente
❌ Pricing confuso y puede explotar
❌ No tienes SQL real
```

**Veredicto:** Bueno para apps móviles simples, MALO para apps con datos relacionales.

#### CLERK + PostgreSQL (Tendencia 2025-2026)

```
PROS:
✅ Auth PREMIUM - la mejor UX de login
✅ Webhooks, organizations, MFA out-of-the-box
✅ Separación de concerns (auth ≠ database)

CONTRAS:
⚠️ $25/mes + PostgreSQL separado = más caro
⚠️ Más complejidad (2 servicios en vez de 1)
```

**Veredicto:** Excelente si necesitas auth empresarial (SSO, SAML), overkill para etapa actual.

#### AWS (RDS + Cognito + S3)

```
PROS:
✅ Infinitamente escalable
✅ Compliance (HIPAA, SOC2, etc.)

CONTRAS:
❌ COMPLEJIDAD EXTREMA - necesitas DevOps dedicado
❌ Pricing impredecible
❌ 10x más tiempo de desarrollo
```

**Veredicto:** Para cuando tengas $10M+ en funding y un equipo de DevOps.

---

## 📈 PATH DE CRECIMIENTO TÍPICO

```
ETAPA 1: MVP / Pre-Seed ($0-$500K ARR)
├── Database: Supabase / Firebase / PlanetScale
├── Auth: Supabase Auth / Firebase Auth / Clerk
├── Hosting: Vercel + Railway
└── Costo: ~$50-100/mes

ETAPA 2: Product-Market Fit / Seed ($500K-$2M ARR)
├── Database: Supabase Pro / RDS PostgreSQL
├── Auth: Supabase Auth / Clerk
├── Hosting: Vercel Pro + Railway
└── Costo: ~$200-500/mes

ETAPA 3: Scaling / Series A ($2M-$10M ARR)
├── Database: RDS + Read Replicas + Redis
├── Auth: Clerk / Auth0 / Custom
├── Hosting: AWS/GCP + Kubernetes
└── Costo: ~$2K-10K/mes

ETAPA 4: Enterprise / Series B+ ($10M+ ARR)
├── Database: Aurora + ElastiCache + Data Warehouse
├── Auth: Custom + SSO/SAML
├── Hosting: Multi-region, dedicated DevOps team
└── Costo: ~$20K-100K+/mes
```

---

## ✅ CONCLUSIÓN

**Supabase es la elección CORRECTA para la etapa actual de Aboka AI.**

Es exactamente lo que una startup bien asesorada de Silicon Valley usaría:
- ✅ Rápido de desarrollar
- ✅ Seguro (con RLS habilitado)
- ✅ Económico
- ✅ Escalable hasta $2-5M ARR sin problemas
- ✅ Migratable cuando sea necesario (PostgreSQL estándar)

**Próximos pasos cuando estés lista:**
1. Habilitar Supabase Auth (ya lo tienes, solo hay que usarlo)
2. Configurar RLS en todas las tablas (SQL policies)
3. Verificar JWT en el backend FastAPI
4. Implementar rate limiting con slowapi

---

## 📚 RECURSOS ADICIONALES

- [Supabase Auth Docs](https://supabase.com/docs/guides/auth)
- [Supabase RLS Docs](https://supabase.com/docs/guides/auth/row-level-security)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [slowapi Rate Limiting](https://github.com/laurentS/slowapi)

