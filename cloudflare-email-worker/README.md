# Cloudflare Email Worker para ABOKA AI

Este worker procesa emails entrantes en `docs@tumai.us` y extrae los attachments para enviarlos al backend.

## Configuración paso a paso

### 1. Instalar Wrangler CLI

```bash
npm install -g wrangler
```

### 2. Autenticarte en Cloudflare

```bash
wrangler login
```

### 3. Crear el Worker

Desde esta carpeta:

```bash
cd cloudflare-email-worker
wrangler deploy
```

### 4. Configurar Variables de Entorno

Ve a **Cloudflare Dashboard → Workers & Pages → aboka-email-worker → Settings → Variables**

Añade estas variables:

| Variable | Valor |
|----------|-------|
| `BACKEND_URL` | `https://aboka-ai-production.up.railway.app` |
| `FALLBACK_EMAIL` | `mariasebares9@gmail.com` |
| `WEBHOOK_SECRET` | (opcional) un secret para verificar requests |

### 5. Configurar Email Routing

1. Ve a **Cloudflare Dashboard → tumai.us → Email → Email Routing**
2. Habilita Email Routing si no está habilitado
3. Ve a **Routing Rules**
4. Crea una regla:
   - **Catch-all address** o **Custom address**: `docs@tumai.us`
   - **Action**: "Send to a Worker"
   - **Destination**: `aboka-email-worker`

### 6. Verificar DNS

Asegúrate de que los registros MX de Cloudflare están configurados:

```
MX  tumai.us  route1.mx.cloudflare.net  priority 69
MX  tumai.us  route2.mx.cloudflare.net  priority 12
MX  tumai.us  route3.mx.cloudflare.net  priority 93
```

## Probar

1. Envía un email a `docs@tumai.us` con un PDF adjunto
2. El asunto debe incluir el nombre de la propiedad (ej: "Casa Alberto - Factura cocina")
3. Revisa los logs del Worker en Cloudflare Dashboard
4. El documento debería aparecer en "Aprobaciones" de la app

## Troubleshooting

### Ver logs del Worker
Cloudflare Dashboard → Workers & Pages → aboka-email-worker → Logs

### Ver logs del Backend
Railway Dashboard → Logs

### Verificar que Email Routing está activo
Cloudflare Dashboard → tumai.us → Email → debe mostrar "Active"

