"""
Extraction Tools - Auto-extract financial data from documents using GPT-4.

ABOKA AI: Automatically extracts values from invoices, receipts, and contracts
to populate the "Real" column of the Estudio Económico.

Flow:
1. User uploads document to Armario Digital
2. GPT-4 extracts: concept, value, date, provider
3. System maps concept to Estudio Económico item
4. Agent proposes to user via chat
5. If user approves → update Estudio Económico "Real" column
"""

from typing import Dict, Any, Optional, List
import logging
import json
import base64
from datetime import datetime

from openai import OpenAI
from .supabase_client import sb

logger = logging.getLogger(__name__)

# Initialize OpenAI client
try:
    import os
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    logger.warning(f"[extraction] Could not initialize OpenAI client: {e}")
    client = None


# ═══════════════════════════════════════════════════════════════════════════════
# MAPPING: Conceptos detectados → Items del Estudio Económico
# ═══════════════════════════════════════════════════════════════════════════════

CONCEPT_TO_ESTUDIO_KEY = {
    # COMPRA
    "escritura": "compra_precio",
    "compraventa": "compra_precio",
    "precio compra": "compra_precio",
    "itp": "compra_itp",
    "impuesto transmisiones": "compra_itp",
    "transmisiones patrimoniales": "compra_itp",
    "notaría": "compra_notaria",
    "notario": "compra_notaria",
    "registro": "compra_notaria",
    "gestoría": "compra_notaria",
    "ibi": "compra_ibi",
    
    # REFORMA - Licencias
    "arquitecto": "reforma_proyecto",
    "proyecto": "reforma_proyecto",
    "licencia obra": "reforma_licencia",
    "icio": "reforma_licencia",
    
    # REFORMA - Obra
    "reforma": "reforma_contrata",
    "contrata": "reforma_contrata",
    "obra": "reforma_contrata",
    "constructor": "reforma_contrata",
    "albañil": "reforma_contrata",
    
    # REFORMA - Materiales
    "cocina": "reforma_cocina",
    "electrodomésticos": "reforma_cocina",
    "electros": "reforma_cocina",
    "baño": "reforma_banos",
    "sanitarios": "reforma_banos",
    "grifería": "reforma_banos",
    "suelo": "reforma_suelos",
    "tarima": "reforma_suelos",
    "parquet": "reforma_suelos",
    "armario": "reforma_carpinteria",
    "carpintería": "reforma_carpinteria",
    "muebles": "reforma_carpinteria",
    "aire acondicionado": "reforma_ac",
    "climatización": "reforma_ac",
    "split": "reforma_ac",
    "aire": "reforma_ac",
    "home staging": "reforma_amueblamiento",
    "decoración": "reforma_amueblamiento",
    "amueblamiento": "reforma_amueblamiento",
    
    # FINANCIERO
    "hipoteca": "fin_constitucion",
    "préstamo": "fin_constitucion",
    "tasación": "fin_tasacion",
    "intereses": "fin_intereses",
    "cancelación": "fin_cancelacion",
    "seguro": "fin_seguro",
    "multirriesgo": "fin_seguro",
    
    # GESTIONES
    "comunidad": "gest_comunidad",
    "vecinos": "gest_comunidad",
    "suministros": "gest_suministros",
    "luz": "gest_suministros",
    "gas": "gest_suministros",
    "agua": "gest_suministros",
    "electricidad": "gest_suministros",
    "plusvalía": "gest_plusvalia",
    "comisión": "gest_comision",
    "inmobiliaria": "gest_comision",
    "agencia": "gest_comision",
    
    # VENTA
    "venta": "venta_precio",
    "precio venta": "venta_precio",
    "alquiler": "venta_alquileres",
    "renta": "venta_alquileres",
}

# Nombres legibles para cada key
ESTUDIO_KEY_LABELS = {
    "compra_precio": "Precio Compra Activo",
    "compra_itp": "ITP (Impuesto Transmisiones)",
    "compra_notaria": "Notaría + Registro + Gestoría",
    "compra_ibi": "IBI Prorrateado",
    "compra_gestion": "Gestión ABOKA 1%",
    "reforma_proyecto": "Proyecto / Arquitecto",
    "reforma_licencia": "Licencia de Obra / ICIO",
    "reforma_contrata": "Contrata de Obra",
    "reforma_cocina": "Mobiliario Cocina + Electros",
    "reforma_banos": "Sanitarios Baños + Griferías",
    "reforma_suelos": "Tarima / Suelos",
    "reforma_carpinteria": "Armarios y Carpintería",
    "reforma_ac": "Aire Acondicionado",
    "reforma_otros": "Otros Materiales",
    "reforma_amueblamiento": "Amueblamiento / Home Staging",
    "reforma_contingencia": "Contingencia (5-10%)",
    "fin_constitucion": "Gastos Constitución Hipoteca",
    "fin_tasacion": "Tasación Oficial",
    "fin_intereses": "Intereses Soportados",
    "fin_cancelacion": "Gastos Cancelación Hipoteca",
    "fin_seguro": "Seguro Multirriesgo",
    "gest_comunidad": "Comunidad de Propietarios",
    "gest_ibi": "IBI Anual",
    "gest_suministros": "Suministros (Luz, Gas, Agua)",
    "gest_plusvalia": "Plusvalía Municipal",
    "gest_comision": "Comisión Agencia Venta",
    "venta_precio": "Precio Venta Vivienda",
    "venta_alquileres": "Alquileres Temporales",
}


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN EXTRACTION FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_document_data(
    file_bytes: bytes,
    filename: str,
    mime_type: str = "application/pdf"
) -> Dict[str, Any]:
    """
    Extract financial data from a document using GPT-4.
    
    Args:
        file_bytes: Raw bytes of the document
        filename: Original filename
        mime_type: MIME type of the file
    
    Returns:
        {
            "success": True/False,
            "data": {
                "tipo_documento": "factura",
                "concepto_detectado": "Instalación aire acondicionado",
                "valor_total": 5000.0,
                "fecha_documento": "2024-01-15",
                "proveedor": "Climatización SL",
                "numero_factura": "F-2024-0123",
                "confianza": 0.95
            },
            "error": None or error message
        }
    """
    if not client:
        return {"success": False, "data": None, "error": "OpenAI client not initialized"}
    
    logger.info(f"[extract_document_data] Processing {filename} ({mime_type})")
    
    try:
        # For images, use Vision API
        if mime_type.startswith("image/"):
            return _extract_from_image(file_bytes, filename, mime_type)
        
        # For PDFs, we need to extract text first or use a different approach
        # For now, we'll use a text-based approach with the filename as hint
        # In production, you'd use pdf2image + Vision or a PDF parser
        
        # Simplified: Use filename as context + generic extraction
        return _extract_with_gpt(file_bytes, filename, mime_type)
        
    except Exception as e:
        logger.error(f"[extract_document_data] Error: {e}", exc_info=True)
        return {"success": False, "data": None, "error": str(e)}


def _extract_from_image(file_bytes: bytes, filename: str, mime_type: str) -> Dict:
    """Extract data from image using GPT-4 Vision."""
    
    base64_image = base64.b64encode(file_bytes).decode('utf-8')
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """Eres un experto en análisis de documentos financieros inmobiliarios.
Tu tarea es extraer información estructurada de facturas, tickets, presupuestos y contratos.

SIEMPRE responde en JSON con este formato exacto:
{
    "tipo_documento": "factura" | "presupuesto" | "contrato" | "ticket" | "recibo" | "otro",
    "concepto_detectado": "descripción breve del concepto principal",
    "valor_total": número (solo el valor numérico, sin símbolo €),
    "valor_sin_iva": número o null,
    "iva_porcentaje": número o null,
    "fecha_documento": "YYYY-MM-DD" o null,
    "proveedor": "nombre del proveedor/empresa" o null,
    "numero_factura": "número de factura/ticket" o null,
    "confianza": número entre 0.0 y 1.0 (tu confianza en la extracción)
}

Reglas:
- El concepto debe ser breve y descriptivo (ej: "aire acondicionado", "reforma baño", "notaría")
- Si no puedes identificar un campo con certeza, usa null
- El valor_total SIEMPRE debe incluir IVA si es una factura española
- La confianza debe reflejar la claridad del documento"""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Analiza este documento ({filename}) y extrae la información financiera:"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ],
        max_tokens=1000,
        temperature=0.1
    )
    
    return _parse_extraction_response(response, filename)


def _extract_with_gpt(file_bytes: bytes, filename: str, mime_type: str) -> Dict:
    """Extract data using GPT-4 with text content or filename hints."""
    
    # Try to extract text from PDF
    text_content = ""
    if mime_type == "application/pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                text_content += page.get_text()
            doc.close()
        except ImportError:
            logger.warning("[extract_with_gpt] PyMuPDF not installed, using filename only")
        except Exception as e:
            logger.warning(f"[extract_with_gpt] Could not extract PDF text: {e}")
    
    # Build prompt
    if text_content:
        user_content = f"""Analiza este documento y extrae la información financiera.

Nombre del archivo: {filename}

Contenido del documento:
---
{text_content[:8000]}
---

Extrae la información en formato JSON."""
    else:
        user_content = f"""Basándote en el nombre del archivo, intenta inferir qué tipo de documento es y qué información podría contener.

Nombre del archivo: {filename}

Nota: No tengo acceso al contenido del documento, solo al nombre. 
Si no puedes inferir información del nombre, responde con confianza muy baja (0.1-0.3).

Responde en formato JSON."""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """Eres un experto en análisis de documentos financieros inmobiliarios.
Tu tarea es extraer información estructurada de facturas, tickets, presupuestos y contratos.

SIEMPRE responde en JSON con este formato exacto:
{
    "tipo_documento": "factura" | "presupuesto" | "contrato" | "ticket" | "recibo" | "otro",
    "concepto_detectado": "descripción breve del concepto principal",
    "valor_total": número (solo el valor numérico, sin símbolo €) o null si no se puede determinar,
    "valor_sin_iva": número o null,
    "iva_porcentaje": número o null,
    "fecha_documento": "YYYY-MM-DD" o null,
    "proveedor": "nombre del proveedor/empresa" o null,
    "numero_factura": "número de factura/ticket" o null,
    "confianza": número entre 0.0 y 1.0 (tu confianza en la extracción)
}

Reglas:
- El concepto debe ser breve y descriptivo (ej: "aire acondicionado", "reforma baño", "notaría")
- Si no puedes identificar un campo con certeza, usa null
- Si solo tienes el nombre del archivo y no el contenido, la confianza debe ser baja (< 0.5)"""
            },
            {
                "role": "user",
                "content": user_content
            }
        ],
        max_tokens=1000,
        temperature=0.1
    )
    
    return _parse_extraction_response(response, filename)


def _parse_extraction_response(response, filename: str) -> Dict:
    """Parse GPT response and return structured data."""
    try:
        content = response.choices[0].message.content
        
        # Extract JSON from response (may be wrapped in markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        data = json.loads(content.strip())
        
        # Validate required fields
        if not data.get("concepto_detectado"):
            return {"success": False, "data": None, "error": "No concept detected"}
        
        # Add metadata
        data["modelo_extraccion"] = "gpt-4o"
        data["timestamp_extraccion"] = datetime.utcnow().isoformat()
        data["archivo_origen"] = filename
        
        logger.info(f"[extract] Extracted: {data.get('concepto_detectado')} = {data.get('valor_total')} (conf: {data.get('confianza')})")
        
        return {"success": True, "data": data, "error": None}
    except Exception as e:
        logger.error(f"[extract] Error parsing response: {e}")
        return {"success": False, "data": None, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# INTELLIGENT MAPPING FUNCTION (GPT-powered)
# ═══════════════════════════════════════════════════════════════════════════════

def map_concept_to_estudio(
    concepto: str, 
    property_id: str = None,
    cajon: str = None,
    subcajon: str = None
) -> tuple[Optional[str], float]:
    """
    Map a detected concept to an Estudio Económico item_key using GPT.
    
    Uses context (cajón, subcajón) to improve accuracy.
    
    Args:
        concepto: The concept detected from the document
        property_id: Optional property ID
        cajon: The cajón where the document was uploaded (e.g., 'REFORMA')
        subcajon: The subcajón (e.g., 'Partidas')
    
    Returns:
        tuple: (item_key, confidence) - e.g., ('reforma_ac', 0.95)
    """
    if not concepto:
        return None, 0.0
    
    if not client:
        logger.warning("[map_concept] OpenAI client not available, using fallback")
        return _fallback_keyword_mapping(concepto)
    
    try:
        # Build context string
        context_parts = []
        if cajon:
            context_parts.append(f"Cajón del armario: {cajon}")
        if subcajon:
            context_parts.append(f"Subcajón: {subcajon}")
        
        context_str = "\n".join(context_parts) if context_parts else "Sin contexto adicional"
        
        # Build the mapping prompt
        categories_json = json.dumps(ESTUDIO_KEY_LABELS, ensure_ascii=False, indent=2)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""Eres un experto en contabilidad de reformas inmobiliarias.

Tu tarea es mapear el concepto de una factura/documento a la categoría correcta del Estudio Económico.

CATEGORÍAS DISPONIBLES (key → nombre):
{categories_json}

REGLAS:
1. Responde SIEMPRE en JSON: {{"key": "xxx", "confidence": 0.X}}
2. "key" debe ser una de las keys exactas del diccionario
3. "confidence" es un número entre 0.0 y 1.0:
   - 0.9-1.0: Match muy claro (ej: "factura aire acondicionado" → reforma_ac)
   - 0.7-0.89: Match probable (ej: "instalación clima" → reforma_ac)
   - 0.5-0.69: Match posible pero dudoso
   - <0.5: No hay match claro → responde {{"key": null, "confidence": 0.0}}

EJEMPLOS:
- "Factura aire acondicionado" → {{"key": "reforma_ac", "confidence": 0.95}}
- "Instalación de splits" → {{"key": "reforma_ac", "confidence": 0.90}}
- "Reforma integral baño" → {{"key": "reforma_banos", "confidence": 0.85}}
- "Trabajos de fontanería" → {{"key": "reforma_contrata", "confidence": 0.70}}
- "Documento desconocido" → {{"key": null, "confidence": 0.0}}"""
                },
                {
                    "role": "user",
                    "content": f"""Concepto de la factura: {concepto}

{context_str}

Responde en JSON:"""
                }
            ],
            max_tokens=100,
            temperature=0.0
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON response
        if "```" in content:
            content = content.split("```")[1].replace("json", "").strip()
        
        result = json.loads(content)
        key = result.get("key")
        confidence = float(result.get("confidence", 0.0))
        
        if key and key in ESTUDIO_KEY_LABELS:
            logger.info(f"[map_concept] GPT mapped '{concepto}' → '{key}' (confidence: {confidence})")
            return key, confidence
        else:
            logger.info(f"[map_concept] GPT found no match for '{concepto}'")
            return None, 0.0
            
    except json.JSONDecodeError as e:
        logger.warning(f"[map_concept] Failed to parse GPT response: {e}")
        return _fallback_keyword_mapping(concepto)
    except Exception as e:
        logger.warning(f"[map_concept] GPT mapping failed: {e}")
        return _fallback_keyword_mapping(concepto)


def _fallback_keyword_mapping(concepto: str) -> tuple[Optional[str], float]:
    """Fallback to keyword matching if GPT is unavailable."""
    concepto_lower = concepto.lower().strip()
    
    # Sort keywords by length (longest first)
    sorted_keywords = sorted(CONCEPT_TO_ESTUDIO_KEY.items(), key=lambda x: len(x[0]), reverse=True)
    
    for keyword, key in sorted_keywords:
        if keyword in concepto_lower:
            logger.info(f"[map_concept] Fallback mapped '{concepto}' → '{key}' (keyword: {keyword})")
            return key, 0.7  # Lower confidence for keyword matching
    
    return None, 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def save_extraction_result(
    document_id: str,
    extraction_data: Dict,
    mapped_key: Optional[str] = None
) -> Dict:
    """
    Save extraction results to armario_documents.
    
    Args:
        document_id: UUID of the document
        extraction_data: The extracted data from GPT
        mapped_key: The mapped estudio_key (optional)
    
    Returns:
        {"ok": True/False, "error": ...}
    """
    try:
        update_data = {
            "extracted_data": extraction_data,
            "extraction_status": "pending_approval" if extraction_data.get("valor_total") else "extracted",
            "extraction_confidence": extraction_data.get("confianza", 0),
            "extracted_at": datetime.utcnow().isoformat()
        }
        
        if mapped_key:
            update_data["mapped_estudio_key"] = mapped_key
        
        result = sb.table("armario_documents")\
            .update(update_data)\
            .eq("id", document_id)\
            .execute()
        
        if result.data:
            logger.info(f"[save_extraction] ✅ Saved extraction for document {document_id}")
            return {"ok": True, "data": result.data[0]}
        else:
            return {"ok": False, "error": "Document not found"}
            
    except Exception as e:
        logger.error(f"[save_extraction] Error: {e}")
        return {"ok": False, "error": str(e)}


def get_pending_extractions(property_id: str) -> List[Dict]:
    """
    Get all documents with pending extraction approval.
    
    Returns list of documents with their extracted data.
    """
    try:
        result = sb.rpc('get_pending_extractions', {'p_property_id': property_id}).execute()
        
        if result.data:
            return result.data.get('documents', [])
        return []
        
    except Exception as e:
        logger.error(f"[get_pending_extractions] Error: {e}")
        return []


def approve_extraction(document_id: str, estudio_key: str = None) -> Dict:
    """
    Approve an extraction and update the Estudio Económico.
    
    Args:
        document_id: UUID of the document
        estudio_key: Override the mapped key (optional)
    
    Returns:
        {"ok": True/False, "message": ..., "valor": ...}
    """
    try:
        result = sb.rpc('approve_extraction', {
            'p_document_id': document_id,
            'p_estudio_key': estudio_key
        }).execute()
        
        return result.data or {"ok": False, "error": "Unknown error"}
        
    except Exception as e:
        logger.error(f"[approve_extraction] Error: {e}")
        return {"ok": False, "error": str(e)}


def reject_extraction(document_id: str) -> Dict:
    """
    Reject an extraction proposal.
    """
    try:
        result = sb.rpc('reject_extraction', {'p_document_id': document_id}).execute()
        return result.data or {"ok": False, "error": "Unknown error"}
    
    except Exception as e:
        logger.error(f"[reject_extraction] Error: {e}")
        return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_estudio_label(key: str) -> str:
    """Get the human-readable label for an estudio key."""
    return ESTUDIO_KEY_LABELS.get(key, key)


def format_extraction_proposal(extraction_data: Dict, mapped_key: str = None) -> str:
    """
    Format an extraction for user-friendly display.
    
    Returns a message like:
    "📄 He analizado 'factura_clima.pdf':
     • Concepto: Aire Acondicionado
     • Importe: 5,000€
     • Proveedor: Climatización SL
     
     ¿Lo añado al Estudio Económico como gasto REAL?"
    """
    concepto = extraction_data.get("concepto_detectado", "Desconocido")
    valor = extraction_data.get("valor_total")
    proveedor = extraction_data.get("proveedor")
    fecha = extraction_data.get("fecha_documento")
    archivo = extraction_data.get("archivo_origen", "documento")
    
    msg = f"📄 He analizado **{archivo}**:\n\n"
    msg += f"• **Concepto**: {concepto}\n"
    
    if valor:
        msg += f"• **Importe**: {valor:,.0f}€\n"
    
    if proveedor:
        msg += f"• **Proveedor**: {proveedor}\n"
    
    if fecha:
        msg += f"• **Fecha**: {fecha}\n"
    
    if mapped_key:
        label = get_estudio_label(mapped_key)
        msg += f"\n→ Se añadiría a: **{label}** (columna Real)\n"
    
    msg += "\n¿Lo añado al Estudio Económico como gasto **REAL**?"
    
    return msg
