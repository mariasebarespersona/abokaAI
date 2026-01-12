"""
Extraction Tools - Auto-extract structured data from documents using RAG.

This module provides functions to automatically extract structured information
(e.g., asking_price, market_value) from uploaded documents and store it for
later user confirmation.
"""

from typing import Dict, Any, Optional
import logging
import re
from datetime import datetime

from .rag_maninos import query_documents_maninos
from .supabase_client import sb

logger = logging.getLogger(__name__)


def _parse_price(text: str) -> Optional[float]:
    """
    Extract numeric price from text.
    
    Handles formats:
    - $32,500
    - 32500
    - $32.5k
    - 32.5K
    - treinta y dos mil quinientos (Spanish numbers - basic)
    """
    if not text:
        return None
    
    text = text.lower().strip()
    
    # Remove common words
    text = re.sub(r'\b(asking|price|valor|value|es|is|de|of)\b', '', text, flags=re.IGNORECASE)
    
    # Handle K/k suffix (thousands)
    k_match = re.search(r'(\d+\.?\d*)\s*k', text, re.IGNORECASE)
    if k_match:
        return float(k_match.group(1)) * 1000
    
    # Handle standard formats: $32,500 or 32500
    number_match = re.search(r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text)
    if number_match:
        number_str = number_match.group(1).replace(',', '')
        return float(number_str)
    
    return None


def _calculate_confidence(answer: str, query: str) -> float:
    """
    Calculate confidence score for extracted value.
    
    Based on:
    - Presence of numeric value (0.5)
    - Presence of currency symbol (0.1)
    - Explicit mention of query term (0.2)
    - Answer length (reasonable = 0.2)
    """
    score = 0.0
    
    # Has numeric value
    if re.search(r'\d+', answer):
        score += 0.5
    
    # Has currency symbol or word
    if '$' in answer or 'dollar' in answer.lower() or 'precio' in answer.lower():
        score += 0.1
    
    # Mentions query term
    query_lower = query.lower()
    answer_lower = answer.lower()
    if any(term in answer_lower for term in ['asking', 'price', 'precio', 'market', 'mercado', 'value', 'valor']):
        score += 0.2
    
    # Reasonable length (not too short, not too long)
    if 20 < len(answer) < 300:
        score += 0.2
    
    return min(score, 1.0)


def extract_listing_data(property_id: str, document_id: str) -> Dict[str, Any]:
    """
    Extract structured data from a property listing document.
    
    Uses RAG to query the document for:
    - asking_price
    - market_value
    
    Args:
        property_id: UUID of the property
        document_id: UUID of the document to extract from
    
    Returns:
        {
            "success": bool,
            "extracted": {
                "asking_price": {...},
                "market_value": {...}
            },
            "errors": [...]
        }
    """
    logger.info(f"[extract_listing_data] Starting extraction for property {property_id}, document {document_id}")
    
    result = {
        "success": False,
        "extracted": {},
        "errors": []
    }
    
    # Get document info
    try:
        doc_result = sb.table("maninos_documents").select("*").eq("id", document_id).single().execute()
        if not doc_result.data:
            result["errors"].append(f"Document {document_id} not found")
            return result
        
        doc = doc_result.data
        document_name = doc.get("document_name", "unknown")
        document_type = doc.get("document_type")
        
    except Exception as e:
        logger.error(f"[extract_listing_data] Error fetching document: {e}")
        result["errors"].append(str(e))
        return result
    
    # Define extraction queries
    queries = {
        "asking_price": "¿Cuál es el precio de venta (asking price) de la propiedad? Responde solo con el número.",
        "market_value": "¿Cuál es el valor de mercado (market value) estimado de la propiedad? Responde solo con el número."
    }
    
    extracted_at = datetime.utcnow().isoformat()
    
    # Extract each field
    for field, query in queries.items():
        try:
            logger.info(f"[extract_listing_data] Extracting {field} with query: {query}")
            
            # Query RAG system
            rag_result = query_documents_maninos(
                property_id=property_id,
                question=query,
                document_type=document_type,
                use_reranking=False  # Faster for extraction
            )
            
            answer = rag_result.get("answer", "")
            
            # Parse numeric value
            value = _parse_price(answer)
            
            if value and value > 0:
                confidence = _calculate_confidence(answer, query)
                
                result["extracted"][field] = {
                    "value": value,
                    "confidence": round(confidence, 2),
                    "source": document_name,
                    "extracted_at": extracted_at,
                    "raw_answer": answer[:200]  # Store first 200 chars for debugging
                }
                
                logger.info(f"[extract_listing_data] ✅ Extracted {field}: ${value} (confidence: {confidence:.2f})")
            else:
                logger.warning(f"[extract_listing_data] ⚠️ Could not extract {field} from answer: {answer[:100]}")
                result["errors"].append(f"Could not parse {field} from: {answer[:100]}")
        
        except Exception as e:
            logger.error(f"[extract_listing_data] Error extracting {field}: {e}")
            result["errors"].append(f"Error extracting {field}: {str(e)}")
    
    # Update property with extracted data
    if result["extracted"]:
        try:
            # Get current extracted_data
            prop_result = sb.table("properties").select("extracted_data").eq("id", property_id).single().execute()
            current_data = prop_result.data.get("extracted_data") or {}
            
            # Merge with new data
            updated_data = {**current_data, **result["extracted"]}
            
            # Update property
            sb.table("properties").update({"extracted_data": updated_data}).eq("id", property_id).execute()
            
            logger.info(f"[extract_listing_data] ✅ Saved extracted data to property {property_id}")
            result["success"] = True
            
        except Exception as e:
            logger.error(f"[extract_listing_data] Error saving extracted data: {e}")
            result["errors"].append(f"Error saving: {str(e)}")
    else:
        logger.warning(f"[extract_listing_data] No data extracted from document {document_name}")
    
    return result


def get_extracted_data(property_id: str) -> Dict[str, Any]:
    """
    Get extracted data for a property.
    
    Returns:
        {
            "asking_price": {...} or None,
            "market_value": {...} or None,
            ...
        }
    """
    try:
        result = sb.table("properties").select("extracted_data").eq("id", property_id).single().execute()
        return result.data.get("extracted_data") or {}
    except Exception as e:
        logger.error(f"[get_extracted_data] Error: {e}")
        return {}


def clear_extracted_field(property_id: str, field: str) -> bool:
    """
    Clear a specific extracted field (e.g., if user rejected it).
    
    Args:
        property_id: UUID of the property
        field: Field name (e.g., 'asking_price')
    
    Returns:
        True if successful
    """
    try:
        # Get current data
        result = sb.table("properties").select("extracted_data").eq("id", property_id).single().execute()
        current_data = result.data.get("extracted_data") or {}
        
        # Remove field
        if field in current_data:
            del current_data[field]
            
            # Update
            sb.table("properties").update({"extracted_data": current_data}).eq("id", property_id).execute()
            logger.info(f"[clear_extracted_field] Cleared {field} for property {property_id}")
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"[clear_extracted_field] Error: {e}")
        return False


# ============================================================================
# INVOICE EXTRACTION TOOLS - For Armario Digital / Estudio Económico
# ============================================================================

# Mapping from document concepts to Estudio Económico keys
CONCEPT_TO_ESTUDIO_MAP = {
    # Reforma items
    "aire acondicionado": "reforma_ac",
    "clima": "reforma_ac",
    "climatización": "reforma_ac",
    "fontanería": "reforma_fontaneria",
    "fontanero": "reforma_fontaneria",
    "electricidad": "reforma_electricidad",
    "electricista": "reforma_electricidad",
    "albañilería": "reforma_albanileria",
    "albañil": "reforma_albanileria",
    "obra": "reforma_albanileria",
    "pintura": "reforma_pintura",
    "pintor": "reforma_pintura",
    "cocina": "reforma_cocina",
    "muebles cocina": "reforma_cocina",
    "baño": "reforma_bano",
    "sanitarios": "reforma_bano",
    "suelo": "reforma_suelos",
    "suelos": "reforma_suelos",
    "parquet": "reforma_suelos",
    "ventanas": "reforma_ventanas",
    "carpintería": "reforma_carpinteria",
    "puertas": "reforma_carpinteria",
    "cerrajería": "reforma_cerrajeria",
    # Compra items
    "notaría": "compra_notaria",
    "notario": "compra_notaria",
    "registro": "compra_registro",
    "gestoría": "compra_gestoria",
    "gestor": "compra_gestoria",
    "itp": "compra_itp",
    "impuesto": "compra_itp",
    # Venta items
    "inmobiliaria": "venta_comision",
    "comisión venta": "venta_comision",
}

# Human-readable labels for estudio keys
ESTUDIO_LABELS = {
    "reforma_ac": "Aire Acondicionado",
    "reforma_fontaneria": "Fontanería",
    "reforma_electricidad": "Electricidad",
    "reforma_albanileria": "Albañilería",
    "reforma_pintura": "Pintura",
    "reforma_cocina": "Cocina",
    "reforma_bano": "Baño",
    "reforma_suelos": "Suelos",
    "reforma_ventanas": "Ventanas",
    "reforma_carpinteria": "Carpintería",
    "reforma_cerrajeria": "Cerrajería",
    "compra_notaria": "Notaría (Compra)",
    "compra_registro": "Registro (Compra)",
    "compra_gestoria": "Gestoría (Compra)",
    "compra_itp": "ITP",
    "venta_comision": "Comisión Inmobiliaria",
}


def get_estudio_label(estudio_key: str) -> str:
    """Get human-readable label for estudio key."""
    return ESTUDIO_LABELS.get(estudio_key, estudio_key.replace("_", " ").title())


def map_concept_to_estudio(concept: str) -> Optional[str]:
    """
    Map a document concept (e.g., 'aire acondicionado') to Estudio Económico key.
    
    Returns:
        estudio_key (e.g., 'reforma_ac') or None if no match
    """
    concept_lower = concept.lower().strip()
    
    # Direct match
    if concept_lower in CONCEPT_TO_ESTUDIO_MAP:
        return CONCEPT_TO_ESTUDIO_MAP[concept_lower]
    
    # Partial match
    for key, value in CONCEPT_TO_ESTUDIO_MAP.items():
        if key in concept_lower or concept_lower in key:
            return value
    
    return None


def extract_document_data(
    property_id: str,
    document_id: str,
    storage_path: str,
    file_bytes: bytes = None
) -> Dict[str, Any]:
    """
    Extract structured data from an invoice/factura document.
    
    Uses RAG/LLM to extract:
    - concepto_detectado: What the invoice is for
    - valor_total: Total amount
    - proveedor: Vendor/supplier name
    - fecha: Invoice date
    
    Args:
        property_id: UUID of the property
        document_id: UUID of the armario_document
        storage_path: Path in Supabase storage
        file_bytes: Optional - raw file content (if not provided, downloads from storage)
    
    Returns:
        {
            "success": bool,
            "extracted_data": {
                "concepto_detectado": str,
                "valor_total": float,
                "proveedor": str,
                "fecha": str
            },
            "mapped_estudio_key": str or None,
            "confidence": float,
            "error": str or None
        }
    """
    from .rag_tool import _extract_text
    import openai
    import json
    
    result = {
        "success": False,
        "extracted_data": {},
        "mapped_estudio_key": None,
        "confidence": 0.0,
        "error": None
    }
    
    try:
        # Download file if not provided
        if not file_bytes:
            from .supabase_client import BUCKET
            file_bytes = sb.storage.from_(BUCKET).download(storage_path)
        
        if not file_bytes or len(file_bytes) == 0:
            result["error"] = "Empty file"
            return result
        
        # Extract text from document
        content_type = "application/pdf" if storage_path.lower().endswith(".pdf") else "application/octet-stream"
        text = _extract_text(file_bytes, content_type, storage_path)
        
        if not text or len(text) < 20:
            result["error"] = "Could not extract text from document"
            return result
        
        # Truncate text for LLM
        text = text[:4000]
        
        # Use LLM to extract structured data
        client = openai.OpenAI()
        
        extraction_prompt = f"""Analiza esta factura y extrae la siguiente información en formato JSON:

TEXTO DE LA FACTURA:
{text}

Responde SOLO con un JSON válido con estos campos:
{{
    "concepto_detectado": "descripción breve del concepto principal de la factura",
    "valor_total": número (solo el número, sin símbolo de moneda),
    "proveedor": "nombre de la empresa o proveedor",
    "fecha": "fecha en formato YYYY-MM-DD si está disponible, o null"
}}

Si no puedes extraer algún campo, usa null.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0,
            max_tokens=500
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        extracted = json.loads(response_text)
        
        # Validate and clean
        valor_total = extracted.get("valor_total")
        if isinstance(valor_total, str):
            valor_total = _parse_price(valor_total)
        
        result["extracted_data"] = {
            "concepto_detectado": extracted.get("concepto_detectado"),
            "valor_total": valor_total,
            "proveedor": extracted.get("proveedor"),
            "fecha": extracted.get("fecha")
        }
        
        # Map to Estudio Económico
        concepto = extracted.get("concepto_detectado", "")
        if concepto:
            result["mapped_estudio_key"] = map_concept_to_estudio(concepto)
        
        # Calculate confidence
        confidence = 0.5  # Base confidence
        if valor_total and valor_total > 0:
            confidence += 0.3
        if result["mapped_estudio_key"]:
            confidence += 0.2
        result["confidence"] = min(confidence, 1.0)
        
        result["success"] = True
        logger.info(f"[extract_document_data] ✅ Extracted: {result['extracted_data']}, mapped to: {result['mapped_estudio_key']}")
        
    except json.JSONDecodeError as e:
        result["error"] = f"Failed to parse LLM response: {e}"
        logger.error(f"[extract_document_data] JSON parse error: {e}")
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"[extract_document_data] Error: {e}")
    
    return result


def save_extraction_result(
    document_id: str,
    property_id: str,
    extracted_data: Dict,
    mapped_estudio_key: Optional[str],
    confidence: float,
    original_approval_id: Optional[str] = None
) -> Dict:
    """
    Save extraction result to armario_documents and optionally create a pending value extraction.
    
    Args:
        document_id: UUID of the armario_document
        property_id: UUID of the property
        extracted_data: The extracted data dict
        mapped_estudio_key: The estudio key this maps to (or None)
        confidence: Confidence score 0-1
        original_approval_id: UUID of the original document approval (for linking)
    
    Returns:
        {"success": bool, "extraction_id": str or None, "error": str or None}
    """
    try:
        # Update armario_documents with extraction
        update_data = {
            "extracted_data": extracted_data,
            "mapped_estudio_key": mapped_estudio_key,
            "extraction_confidence": confidence,
            "extraction_status": "pending_approval" if confidence >= 0.5 else "low_confidence",
            "extracted_at": datetime.utcnow().isoformat()
        }
        
        sb.table("armario_documents")\
            .update(update_data)\
            .eq("id", document_id)\
            .execute()
        
        logger.info(f"[save_extraction_result] ✅ Saved extraction for document {document_id}")
        
        return {
            "success": True,
            "document_id": document_id,
            "extraction_status": update_data["extraction_status"]
        }
        
    except Exception as e:
        logger.error(f"[save_extraction_result] Error: {e}")
        return {"success": False, "error": str(e)}


def get_pending_extractions(property_id: str) -> list:
    """
    Get all documents with pending extraction approvals for a property.
    
    Returns list of documents with their extracted values waiting for user confirmation.
    """
    try:
        result = sb.table("armario_documents")\
            .select("id, document_name, original_filename, cajon, subcajon, extracted_data, mapped_estudio_key, extraction_confidence, extracted_at")\
            .eq("property_id", property_id)\
            .eq("extraction_status", "pending_approval")\
            .order("extracted_at", desc=True)\
            .execute()
        
        return [
            {
                "document_id": doc["id"],
                "document_name": doc["document_name"],
                "original_filename": doc["original_filename"],
                "cajon": doc["cajon"],
                "subcajon": doc["subcajon"],
                "extracted_data": doc["extracted_data"] or {},
                "mapped_estudio_key": doc["mapped_estudio_key"],
                "extraction_confidence": doc["extraction_confidence"],
                "extracted_at": doc["extracted_at"]
            }
            for doc in result.data
        ]
    except Exception as e:
        logger.error(f"[get_pending_extractions] Error: {e}")
        return []


def approve_extraction(document_id: str, estudio_key: Optional[str] = None) -> Dict:
    """
    Approve an extraction and add the value to the Estudio Económico (Real column).
    
    Args:
        document_id: UUID of the armario_document
        estudio_key: Optional override for the estudio key (if user wants different mapping)
    
    Returns:
        {"ok": bool, "message": str, "estudio_key": str, "valor": float, "error": str or None}
    """
    try:
        # Get document with extraction
        doc_result = sb.table("armario_documents")\
            .select("*")\
            .eq("id", document_id)\
            .single()\
            .execute()
        
        if not doc_result.data:
            return {"ok": False, "error": "Document not found"}
        
        doc = doc_result.data
        
        if doc.get("extraction_status") != "pending_approval":
            return {"ok": False, "error": "No pending extraction for this document"}
        
        extracted_data = doc.get("extracted_data") or {}
        valor = extracted_data.get("valor_total")
        
        if not valor:
            return {"ok": False, "error": "No value extracted from document"}
        
        # Use override key or mapped key
        final_key = estudio_key or doc.get("mapped_estudio_key")
        
        if not final_key:
            return {"ok": False, "error": "No estudio key mapped for this document"}
        
        property_id = doc.get("property_id")
        
        # Update Estudio Económico - add to Real column
        # Get current estudio
        estudio_result = sb.rpc("get_estudio_economico", {"p_property_id": property_id}).execute()
        
        if estudio_result.data and estudio_result.data.get("ok"):
            items = estudio_result.data.get("items", [])
            
            # Find the matching item and update
            for item in items:
                if item.get("item_key") == final_key:
                    current_real = item.get("real") or 0
                    new_real = current_real + valor
                    
                    # Update via RPC
                    sb.rpc("update_estudio_item", {
                        "p_property_id": property_id,
                        "p_item_key": final_key,
                        "p_real": new_real
                    }).execute()
                    
                    break
        
        # Update document status
        sb.table("armario_documents")\
            .update({
                "extraction_status": "approved",
                "approved_at": datetime.utcnow().isoformat()
            })\
            .eq("id", document_id)\
            .execute()
        
        label = get_estudio_label(final_key)
        logger.info(f"[approve_extraction] ✅ Added {valor}€ to {label} for property {property_id}")
        
        return {
            "ok": True,
            "message": f"Valor de {valor}€ añadido a {label}",
            "estudio_key": final_key,
            "valor": valor
        }
        
    except Exception as e:
        logger.error(f"[approve_extraction] Error: {e}")
        return {"ok": False, "error": str(e)}


def reject_extraction(document_id: str) -> Dict:
    """
    Reject an extraction proposal.
    
    Args:
        document_id: UUID of the armario_document
    
    Returns:
        {"ok": bool, "message": str}
    """
    try:
        sb.table("armario_documents")\
            .update({
                "extraction_status": "rejected",
                "rejected_at": datetime.utcnow().isoformat()
            })\
            .eq("id", document_id)\
            .execute()
        
        logger.info(f"[reject_extraction] Document {document_id} extraction rejected")
        
        return {"ok": True, "message": "Extracción rechazada"}
        
    except Exception as e:
        logger.error(f"[reject_extraction] Error: {e}")
        return {"ok": False, "error": str(e)}


def format_extraction_proposal(extracted_data: Dict, mapped_estudio_key: Optional[str]) -> str:
    """
    Format an extraction proposal for user-friendly display.
    
    Returns a markdown-formatted string proposing the extracted value.
    """
    concepto = extracted_data.get("concepto_detectado", "Desconocido")
    valor = extracted_data.get("valor_total")
    proveedor = extracted_data.get("proveedor", "")
    fecha = extracted_data.get("fecha", "")
    
    valor_str = f"{valor:,.2f}€" if valor else "No detectado"
    estudio_label = get_estudio_label(mapped_estudio_key) if mapped_estudio_key else "Sin asignar"
    
    msg = f"""📄 He analizado el documento:

• **Concepto**: {concepto}
• **Importe**: {valor_str}"""
    
    if proveedor:
        msg += f"\n• **Proveedor**: {proveedor}"
    if fecha:
        msg += f"\n• **Fecha**: {fecha}"
    
    if mapped_estudio_key:
        msg += f"""

→ Se añadiría a: **{estudio_label}** (columna Real)

¿Lo añado al Estudio Económico como gasto **REAL**?"""
    else:
        msg += """

⚠️ No he podido mapear automáticamente este concepto al Estudio Económico.
¿A qué partida quieres añadir este valor?"""
    
    return msg

