from __future__ import annotations
import io, mimetypes, os, re, datetime as dt
from typing import Dict, List, Optional, Tuple
from .supabase_client import sb, BUCKET
from .utils import docs_schema, utcnow_iso
from difflib import SequenceMatcher

# -------- Fuzzy Matching Helper --------
def _fuzzy_match_keywords(text: str, min_similarity: float = 0.7) -> Optional[Tuple[str, str, str]]:
    """
    Advanced fuzzy matching to find the best matching document group.
    
    Returns: (keyword, group, subgroup) or None if no match above threshold
    """
    import logging
    logger = logging.getLogger(__name__)
    
    text_lower = text.lower()
    best_match = None
    best_score = 0.0
    
    # Build a flat list of all (keyword, group, subgroup) tuples
    all_keywords = []
    for key, kws in DOC_GROUPS.items():
        parts = key.split(":")
        group = parts[0]
        subgroup = parts[1] if len(parts) > 1 else ""
        for kw in kws:
            all_keywords.append((kw, group, subgroup))
    
    # Try exact substring match first (highest priority)
    for kw, group, subgroup in all_keywords:
        if kw in text_lower:
            logger.info(f"🎯 [fuzzy_match] EXACT match: '{kw}' in '{text}' → {group}:{subgroup}")
            return (kw, group, subgroup)
    
    # Try fuzzy matching with SequenceMatcher
    for kw, group, subgroup in all_keywords:
        # Compare filename with keyword
        similarity = SequenceMatcher(None, text_lower, kw).ratio()
        
        # Also compare each word in filename with keyword
        words = text_lower.split()
        for word in words:
            word_similarity = SequenceMatcher(None, word, kw).ratio()
            similarity = max(similarity, word_similarity)
        
        if similarity > best_score:
            best_score = similarity
            best_match = (kw, group, subgroup)
    
    if best_score >= min_similarity:
        logger.info(f"🔍 [fuzzy_match] FUZZY match: '{text}' → '{best_match[0]}' (score: {best_score:.2f}) → {best_match[1]}:{best_match[2]}")
        return best_match
    
    logger.warning(f"⚠️ [fuzzy_match] No match found for '{text}' (best score: {best_score:.2f}, threshold: {min_similarity})")
    return None


# -------- RAG-based Document Classification --------
def _rag_classify_document(file_bytes: bytes, filename: str) -> Optional[Tuple[str, str, str]]:
    """
    Use RAG to read the document content and classify it based on keywords.
    
    Returns: (keyword, group, subgroup) or None if RAG fails or no match
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Only try RAG for PDFs
        if not filename.lower().endswith('.pdf'):
            logger.debug(f"[rag_classify] Skipping non-PDF file: {filename}")
            return None
        
        # Extract text from PDF
        try:
            from pypdf import PdfReader
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            # Read first 3 pages only (for performance)
            for page in pdf_reader.pages[:3]:
                text += page.extract_text() or ""
            text = text.lower()[:2000]  # Limit to 2000 chars
            
            if len(text) < 20:
                logger.debug(f"[rag_classify] Not enough text extracted from {filename}")
                return None
            
            logger.info(f"📖 [rag_classify] Extracted {len(text)} chars from {filename}")
            
            # Search for keywords in extracted text
            all_keywords = []
            for key, kws in DOC_GROUPS.items():
                parts = key.split(":")
                group = parts[0]
                subgroup = parts[1] if len(parts) > 1 else ""
                for kw in kws:
                    all_keywords.append((kw, group, subgroup))
            
            # Sort by keyword length (longer = more specific)
            all_keywords.sort(key=lambda x: -len(x[0]))
            
            # Find best match
            for kw, group, subgroup in all_keywords:
                if kw in text:
                    logger.info(f"✅ [rag_classify] Found '{kw}' in document content → {group}:{subgroup}")
                    return (kw, group, subgroup)
            
            logger.warning(f"⚠️ [rag_classify] No keywords found in document content")
            return None
            
        except ImportError:
            logger.warning("[rag_classify] pypdf not installed, skipping RAG classification")
            return None
        except Exception as e:
            logger.error(f"❌ [rag_classify] Failed to extract text: {e}")
            return None
    
    except Exception as e:
        logger.error(f"❌ [rag_classify] Unexpected error: {e}")
        return None


# -------- ABOKA ARMARIO DIGITAL - Estructura de 6 Cajones -----
# Taxonomía alineada con el estudio económico de operaciones inmobiliarias ABOKA
# 
# CAJÓN 1: COMPRA DEL ACTIVO (Adquisición)
# CAJÓN 2: REFORMA Y OBRA (Transformación)  
# CAJÓN 3: GASTOS FINANCIEROS (Financiación)
# CAJÓN 4: GASTOS VARIOS (Gestión Recurrente)
# CAJÓN 5: VENTA Y COMERCIALIZACIÓN (Salida)
# CAJÓN 6: RESULTADO / CIERRE (Control Final)

DOC_GROUPS = {
    # ═══════════════════════════════════════════════════════════════════
    # CAJÓN 1: COMPRA DEL ACTIVO (Adquisición)
    # ═══════════════════════════════════════════════════════════════════
    "COMPRA:Due Diligence": [
        "nota simple", "referencia catastral", "catastro", "certificado deuda ibi",
        "certificado corriente comunidad", "certificado energético", "informe cargas"
    ],
    "COMPRA:Contrato": [
        "contrato arras", "señal", "arras", "contrato compraventa", 
        "escritura compraventa", "escritura pública compraventa"
    ],
    "COMPRA:Gastos": [
        "factura notaría cpvta", "notaría compra", "registro compra", "gestoría compra",
        "modelo 600", "itp", "impuesto transmisiones", "recibo ibi", "gastos gestión"
    ],
    
    # ═══════════════════════════════════════════════════════════════════
    # CAJÓN 2: REFORMA Y OBRA (Transformación)
    # ═══════════════════════════════════════════════════════════════════
    "REFORMA:Licencias": [
        "proyecto básico", "memoria técnica", "licencia de obra", "declaración responsable",
        "tasas icio", "tasas urbanísticas", "licencia ocupación vía pública", "arquitecto"
    ],
    "REFORMA:Contrata": [
        "contrato contrata", "contrato obra", "contrato constructor", "presupuesto obra",
        "factura contrata", "certificación obra"
    ],
    "REFORMA:Partidas": [
        "mobiliario baños", "griferías", "aire acondicionado", "tarima flotante",
        "cerámica baños", "armarios", "carpintería", "mobiliario cocina", "encimeras",
        "electrodomésticos", "puertas cristal", "contingencias", "factura material"
    ],
    "REFORMA:Amueblamiento": [
        "amueblamiento", "menaje", "decoración", "home staging", "factura muebles"
    ],
    "REFORMA:Certificados": [
        "boletín eléctrico", "cie", "boletín gas", "rite", "certificado final obra",
        "garantías materiales", "manual uso"
    ],
    
    # ═══════════════════════════════════════════════════════════════════
    # CAJÓN 3: GASTOS FINANCIEROS (Financiación)
    # ═══════════════════════════════════════════════════════════════════
    "FINANCIERO:Hipoteca": [
        "fein", "fiae", "oferta vinculante", "escritura préstamo hipotecario",
        "escritura hipoteca", "tasación eco", "tasación oficial"
    ],
    "FINANCIERO:Gastos Constitución": [
        "notaría préstamo hipotecario", "registro préstamo hipotecario",
        "itp ajd hipoteca", "gestoría préstamo hipotecario", "gastos constitución hipoteca"
    ],
    "FINANCIERO:Cancelación": [
        "certificado deuda cero", "cancelación hipoteca", "notaría cancelación",
        "registro cancelación", "modelo 601", "gastos cancelación"
    ],
    "FINANCIERO:Seguros": [
        "seguro multirriesgo", "póliza seguro", "seguro hogar", "seguro vinculación",
        "seguro responsabilidad civil"
    ],
    "FINANCIERO:Intereses": [
        "cuadro amortización", "intereses soportados", "justificante intereses",
        "extracto bancario", "recibo hipoteca"
    ],
    
    # ═══════════════════════════════════════════════════════════════════
    # CAJÓN 4: GASTOS VARIOS (Gestión Recurrente)
    # ═══════════════════════════════════════════════════════════════════
    "GESTIONES:Suministros": [
        "contrato luz", "contrato gas", "contrato fibra", "factura luz",
        "factura gas", "factura agua", "suministros"
    ],
    "GESTIONES:Comunidad": [
        "recibo comunidad", "comunidad propietarios", "certificado comunidad",
        "derrama", "acta junta"
    ],
    "GESTIONES:Impuestos": [
        "plusvalía municipal", "iivtnu", "plusvalía", "modelo 210"
    ],
    "GESTIONES:Comisiones": [
        "factura agencia inmobiliaria", "comisión venta", "comisión intermediación",
        "honorarios api"
    ],
    
    # ═══════════════════════════════════════════════════════════════════
    # CAJÓN 5: VENTA Y COMERCIALIZACIÓN (Salida)
    # ═══════════════════════════════════════════════════════════════════
    "VENTA:Dossier Comercial": [
        "render", "infografía", "fotografías profesionales", "plano comercial",
        "certificado energético nuevo", "home staging fotos"
    ],
    "VENTA:Cierre": [
        "contrato reserva", "oferta compra", "arras venta", "contrato arras venta",
        "escritura venta", "escritura pública venta"
    ],
    "VENTA:Alquileres": [
        "contrato alquiler temporal", "alquiler vacacional", "justificante alquiler",
        "recibo alquiler"
    ],
    
    # ═══════════════════════════════════════════════════════════════════
    # CAJÓN 6: RESULTADO / CIERRE (Control Final)
    # ═══════════════════════════════════════════════════════════════════
    "CIERRE:Liquidación": [
        "estudio económico", "informe final operación", "honorarios aboka",
        "factura aboka", "liquidación operación"
    ],
    "CIERRE:Fiscal": [
        "modelo 100", "irpf ganancias patrimoniales", "declaración is",
        "impuesto sociedades", "declaración renta"
    ],
    "CIERRE:Inversores": [
        "documento cierre inversores", "reparto beneficios", "acta cierre",
        "informe rentabilidad"
    ]
}

# Map keywords to canonical document names (exact cell names in DB)
# Estructura ABOKA - Armario Digital de 6 Cajones
KEYWORD_TO_DOCNAME = {
    # ═══════════════════════════════════════════════════════════════════
    # CAJÓN 1: COMPRA DEL ACTIVO
    # ═══════════════════════════════════════════════════════════════════
    # Due Diligence
    "nota simple": "Nota Simple Informativa",
    "referencia catastral": "Referencia Catastral",
    "catastro": "Referencia Catastral",
    "certificado deuda ibi": "Certificado Deuda IBI",
    "certificado corriente comunidad": "Certificado Corriente Comunidad",
    "certificado energético": "Certificado Energético Original",
    "informe cargas": "Informe de Cargas y Gravámenes",
    
    # Contrato de Compra
    "contrato arras": "Contrato de Arras / Señal",
    "señal": "Contrato de Arras / Señal",
    "arras": "Contrato de Arras / Señal",
    "contrato compraventa": "Contrato de Compraventa",
    "escritura compraventa": "Escritura Pública de Compraventa",
    "escritura pública compraventa": "Escritura Pública de Compraventa",
    
    # Gastos de Compra
    "factura notaría cpvta": "Factura Notaría + Registro + Gestoría CPVTA",
    "notaría compra": "Factura Notaría + Registro + Gestoría CPVTA",
    "registro compra": "Factura Notaría + Registro + Gestoría CPVTA",
    "gestoría compra": "Factura Notaría + Registro + Gestoría CPVTA",
    "modelo 600": "Modelo 600 ITP Presentado",
    "itp": "Modelo 600 ITP Presentado",
    "impuesto transmisiones": "Modelo 600 ITP Presentado",
    "recibo ibi": "Recibo IBI",
    "gastos gestión": "Gastos de Gestión 1%",
    
    # ═══════════════════════════════════════════════════════════════════
    # CAJÓN 2: REFORMA Y OBRA
    # ═══════════════════════════════════════════════════════════════════
    # Licencias
    "proyecto básico": "Proyecto Básico / Memoria Técnica",
    "memoria técnica": "Proyecto Básico / Memoria Técnica",
    "licencia de obra": "Licencia de Obra / Declaración Responsable",
    "declaración responsable": "Licencia de Obra / Declaración Responsable",
    "tasas icio": "Tasas Urbanísticas ICIO",
    "tasas urbanísticas": "Tasas Urbanísticas ICIO",
    "licencia ocupación vía pública": "Licencia Ocupación Vía Pública",
    "arquitecto": "Contrato y Facturas Arquitecto",
    
    # Contrata
    "contrato contrata": "Contrato Contrata de Obra",
    "contrato obra": "Contrato Contrata de Obra",
    "contrato constructor": "Contrato Contrata de Obra",
    "presupuesto obra": "Presupuesto de Obra",
    "factura contrata": "Facturas Contrata de Obra",
    "certificación obra": "Certificaciones de Obra",
    
    # Partidas de Materiales
    "mobiliario baños": "Factura Mobiliario Baños + Griferías",
    "griferías": "Factura Mobiliario Baños + Griferías",
    "aire acondicionado": "Factura Aire Acondicionado",
    "tarima flotante": "Factura Tarima Flotante",
    "cerámica baños": "Factura Cerámica Baños",
    "armarios": "Factura Armarios y Carpintería",
    "carpintería": "Factura Armarios y Carpintería",
    "mobiliario cocina": "Factura Mobiliario Cocina + Encimeras + Electros",
    "encimeras": "Factura Mobiliario Cocina + Encimeras + Electros",
    "electrodomésticos": "Factura Mobiliario Cocina + Encimeras + Electros",
    "puertas cristal": "Factura Puertas Cristal Interiores",
    "contingencias": "Factura Contingencias y Otros",
    "factura material": "Facturas Materiales Varios",
    
    # Amueblamiento
    "amueblamiento": "Facturas Amueblamiento y Menaje",
    "menaje": "Facturas Amueblamiento y Menaje",
    "decoración": "Facturas Decoración",
    "home staging": "Facturas Home Staging",
    "factura muebles": "Facturas Amueblamiento y Menaje",
    
    # Certificados Técnicos
    "boletín eléctrico": "Boletín Eléctrico (CIE)",
    "cie": "Boletín Eléctrico (CIE)",
    "boletín gas": "Boletín Gas / RITE",
    "rite": "Boletín Gas / RITE",
    "certificado final obra": "Certificado Final de Obra",
    "garantías materiales": "Garantías de Materiales",
    "manual uso": "Manuales de Uso",
    
    # ═══════════════════════════════════════════════════════════════════
    # CAJÓN 3: GASTOS FINANCIEROS
    # ═══════════════════════════════════════════════════════════════════
    # Hipoteca
    "fein": "FEIN / FIAE Oferta Vinculante",
    "fiae": "FEIN / FIAE Oferta Vinculante",
    "oferta vinculante": "FEIN / FIAE Oferta Vinculante",
    "escritura préstamo hipotecario": "Escritura Préstamo Hipotecario",
    "escritura hipoteca": "Escritura Préstamo Hipotecario",
    "tasación eco": "Tasación Oficial ECO",
    "tasación oficial": "Tasación Oficial ECO",
    
    # Gastos Constitución
    "notaría préstamo hipotecario": "Gastos Constitución Hipoteca - Notaría",
    "registro préstamo hipotecario": "Gastos Constitución Hipoteca - Registro",
    "itp ajd hipoteca": "Gastos Constitución Hipoteca - ITP AJD",
    "gestoría préstamo hipotecario": "Gastos Constitución Hipoteca - Gestoría",
    "gastos constitución hipoteca": "Gastos Constitución Hipoteca (Total)",
    
    # Cancelación
    "certificado deuda cero": "Certificado Deuda Cero Banco",
    "cancelación hipoteca": "Gastos Cancelación Hipoteca",
    "notaría cancelación": "Gastos Cancelación - Notaría",
    "registro cancelación": "Gastos Cancelación - Registro",
    "modelo 601": "Modelo 601 AJD Cancelación",
    "gastos cancelación": "Gastos Cancelación Hipoteca (Total)",
    
    # Seguros
    "seguro multirriesgo": "Póliza Seguro Multirriesgo + Vinculación",
    "póliza seguro": "Póliza Seguro Multirriesgo + Vinculación",
    "seguro hogar": "Póliza Seguro Multirriesgo + Vinculación",
    "seguro vinculación": "Póliza Seguro Multirriesgo + Vinculación",
    "seguro responsabilidad civil": "Seguro Responsabilidad Civil",
    
    # Intereses
    "cuadro amortización": "Cuadro de Amortización",
    "intereses soportados": "Justificantes Intereses Soportados",
    "justificante intereses": "Justificantes Intereses Soportados",
    "extracto bancario": "Extractos Bancarios Hipoteca",
    "recibo hipoteca": "Recibos Mensuales Hipoteca",
    
    # ═══════════════════════════════════════════════════════════════════
    # CAJÓN 4: GASTOS VARIOS
    # ═══════════════════════════════════════════════════════════════════
    # Suministros
    "contrato luz": "Contrato Suministro Luz",
    "contrato gas": "Contrato Suministro Gas",
    "contrato fibra": "Contrato Suministro Fibra/Internet",
    "factura luz": "Facturas Mensuales Luz",
    "factura gas": "Facturas Mensuales Gas",
    "factura agua": "Facturas Mensuales Agua",
    "suministros": "Facturas Suministros Varios",
    
    # Comunidad
    "recibo comunidad": "Recibos Comunidad de Propietarios",
    "comunidad propietarios": "Recibos Comunidad de Propietarios",
    "certificado comunidad": "Certificado Corriente Comunidad",
    "derrama": "Certificado y Derramas",
    "acta junta": "Actas Junta de Propietarios",
    
    # Impuestos
    "plusvalía municipal": "Plusvalía Municipal IIVTNU",
    "iivtnu": "Plusvalía Municipal IIVTNU",
    "plusvalía": "Plusvalía Municipal IIVTNU",
    "modelo 210": "Modelo 210 (No Residentes)",
    
    # Comisiones
    "factura agencia inmobiliaria": "Factura Comisión Agencia Inmobiliaria",
    "comisión venta": "Factura Comisión Agencia Inmobiliaria",
    "comisión intermediación": "Factura Comisión Agencia Inmobiliaria",
    "honorarios api": "Factura Honorarios API",
    
    # ═══════════════════════════════════════════════════════════════════
    # CAJÓN 5: VENTA Y COMERCIALIZACIÓN
    # ═══════════════════════════════════════════════════════════════════
    # Dossier Comercial
    "render": "Renders / Infografías 3D",
    "infografía": "Renders / Infografías 3D",
    "fotografías profesionales": "Fotografías Profesionales",
    "plano comercial": "Plano Comercial de Venta",
    "certificado energético nuevo": "Certificado Energético Nuevo",
    "home staging fotos": "Fotografías Home Staging",
    
    # Cierre de Venta
    "contrato reserva": "Contrato de Reserva / Oferta",
    "oferta compra": "Contrato de Reserva / Oferta",
    "arras venta": "Contrato de Arras (Venta)",
    "contrato arras venta": "Contrato de Arras (Venta)",
    "escritura venta": "Escritura Pública de Venta",
    "escritura pública venta": "Escritura Pública de Venta",
    
    # Alquileres
    "contrato alquiler temporal": "Contratos Alquiler Temporal",
    "alquiler vacacional": "Contratos Alquiler Temporal",
    "justificante alquiler": "Justificantes Pago Alquileres",
    "recibo alquiler": "Justificantes Pago Alquileres",
    
    # ═══════════════════════════════════════════════════════════════════
    # CAJÓN 6: RESULTADO / CIERRE
    # ═══════════════════════════════════════════════════════════════════
    # Liquidación
    "estudio económico": "Estudio Económico de la Operación",
    "informe final operación": "Informe Final de Operación",
    "honorarios aboka": "Factura Honorarios ABOKA",
    "factura aboka": "Factura Honorarios ABOKA",
    "liquidación operación": "Documento Liquidación Operación",
    
    # Fiscal
    "modelo 100": "Modelo 100 IRPF",
    "irpf ganancias patrimoniales": "Declaración IRPF Ganancias Patrimoniales",
    "declaración is": "Declaración Impuesto Sociedades",
    "impuesto sociedades": "Declaración Impuesto Sociedades",
    "declaración renta": "Declaración IRPF",
    
    # Inversores
    "documento cierre inversores": "Documento Cierre con Inversores",
    "reparto beneficios": "Documento Reparto de Beneficios",
    "acta cierre": "Acta de Cierre Operación",
    "informe rentabilidad": "Informe de Rentabilidad Final",
}

# Docs that should spawn factura placeholders when uploaded
# Key: (Group, Subgroup, Name) - Estructura ABOKA Armario Digital
FACTURABLE_DOCS = {
    # CAJÓN 2: REFORMA - Contratos que generan facturas recurrentes
    ("REFORMA", "Contrata", "Contrato Contrata de Obra"): "Facturas Contrata de Obra",
    ("REFORMA", "Licencias", "Contrato y Facturas Arquitecto"): "Facturas Arquitecto",
    
    # CAJÓN 3: FINANCIERO - Documentos con pagos recurrentes
    ("FINANCIERO", "Hipoteca", "Escritura Préstamo Hipotecario"): "Recibos Mensuales Hipoteca",
    ("FINANCIERO", "Seguros", "Póliza Seguro Multirriesgo + Vinculación"): "Recibos Seguro Anual",
    
    # CAJÓN 4: GESTIONES - Suministros con facturas mensuales
    ("GESTIONES", "Suministros", "Contrato Suministro Luz"): "Facturas Mensuales Luz",
    ("GESTIONES", "Suministros", "Contrato Suministro Gas"): "Facturas Mensuales Gas",
    ("GESTIONES", "Comunidad", "Recibos Comunidad de Propietarios"): "Recibos Mensuales Comunidad",
    
    # CAJÓN 5: VENTA - Alquileres temporales
    ("VENTA", "Alquileres", "Contratos Alquiler Temporal"): "Justificantes Pago Alquileres",
}

def _normalize(text: str) -> str:
    t = (text or "").lower()
    return re.sub(r"[^a-z0-9áéíóúüñ]+", " ", t)

def propose_slot(filename: str, text_hint: str = "", property_id: str = "", file_bytes: Optional[bytes] = None) -> Dict:
    import logging
    logger = logging.getLogger(__name__)
    
    date_match = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})|(\d{1,2}[-/]\d{1,2}[-/]\d{4})", filename)
    extracted_date = date_match.group(0).replace("/", "-") if date_match else None
    
    fn = _normalize(filename)
    hint = _normalize(text_hint)
    combined = fn + " " + hint
    
    is_factura = "factura" in combined or "invoice" in combined
    
    if is_factura and property_id:
        try:
            all_docs = list_docs(property_id)
            if extracted_date:
                for doc in all_docs:
                    if (doc.get("document_kind") == "factura" 
                        and doc.get("placeholder") 
                        and doc.get("due_date")):
                        doc_name = doc.get("document_name", "")
                        if extracted_date in doc_name:
                            return {
                                "document_group": doc.get("document_group"),
                                "document_subgroup": doc.get("document_subgroup") or "",
                                "document_name": doc_name,
                                "is_placeholder_replacement": True
                            }
            
            for parent_key, factura_title in FACTURABLE_DOCS.items():
                parent_name = parent_key[2].lower()
                if parent_name.split()[0] in combined:
                    for doc in all_docs:
                        if (doc.get("document_kind") == "factura"
                            and doc.get("placeholder")
                            and factura_title.lower() in doc.get("document_name", "").lower()
                            and not doc.get("storage_key")):
                            return {
                                "document_group": doc.get("document_group"),
                                "document_subgroup": doc.get("document_subgroup") or "",
                                "document_name": doc.get("document_name"),
                                "is_placeholder_replacement": True
                            }
        except Exception:
            pass
    
    # STEP 1: Try exact keyword matching (original logic)
    all_keywords = []
    for key, kws in DOC_GROUPS.items():
        for kw in kws:
            parts = key.split(":")
            group = parts[0]
            subgroup = parts[1] if len(parts) > 1 else ""
            all_keywords.append((kw, group, subgroup))
    
    all_keywords.sort(key=lambda x: -len(x[0]))
    
    for kw, group, subgroup in all_keywords:
        if kw in combined:
            doc_name = KEYWORD_TO_DOCNAME.get(kw, kw.title())
            logger.info(f"✅ [propose_slot] EXACT match: '{kw}' → {group}:{subgroup}")
            return {"document_group": group, "document_subgroup": subgroup, "document_name": doc_name}
    
    # STEP 2: Try fuzzy matching on filename
    logger.info(f"🔍 [propose_slot] No exact match, trying fuzzy matching for: {filename}")
    fuzzy_result = _fuzzy_match_keywords(combined, min_similarity=0.65)
    if fuzzy_result:
        kw, group, subgroup = fuzzy_result
        doc_name = KEYWORD_TO_DOCNAME.get(kw, kw.title())
        logger.info(f"✅ [propose_slot] FUZZY match: '{filename}' → {group}:{subgroup} (via keyword '{kw}')")
        return {"document_group": group, "document_subgroup": subgroup, "document_name": doc_name}
    
    # STEP 3: Try RAG to read document content (if file bytes available)
    if file_bytes:
        logger.info(f"📖 [propose_slot] Trying RAG classification for: {filename}")
        rag_result = _rag_classify_document(file_bytes, filename)
        if rag_result:
            kw, group, subgroup = rag_result
            doc_name = KEYWORD_TO_DOCNAME.get(kw, kw.title())
            logger.info(f"✅ [propose_slot] RAG match: '{filename}' → {group}:{subgroup} (found keyword '{kw}' in content)")
            return {"document_group": group, "document_subgroup": subgroup, "document_name": doc_name}
        logger.warning(f"⚠️ [propose_slot] RAG classification failed for: {filename}")
    else:
        logger.debug(f"⚠️ [propose_slot] No file_bytes provided, skipping RAG classification")
    
    logger.warning(f"⚠️ [propose_slot] All classification methods failed for: {filename}")
    logger.warning(f"   Available groups: {list(DOC_GROUPS.keys())}")
    
    # STEP 4: Last resort - ask the agent to clarify with the user
    return {
        "error": "Could not determine document category",
        "message": f"No pude identificar a qué cajón del armario pertenece '{filename}'. Los cajones disponibles son: COMPRA (Due Diligence, Contrato, Gastos), REFORMA (Licencias, Contrata, Partidas), FINANCIERO (Hipoteca, Seguros), GESTIONES (Suministros, Comunidad), VENTA (Dossier, Cierre), CIERRE (Liquidación, Fiscal). ¿Puedes indicarme el cajón?",
        "available_groups": list(DOC_GROUPS.keys()),
        "suggestion": "Intenta usar palabras clave como: nota simple, escritura, contrato, factura, licencia, hipoteca, comunidad, etc.",
        "document_group": None,  # Force agent to handle error
        "document_subgroup": None,
        "document_name": None
    }

def upload_and_link(property_id: str, file_bytes: bytes, filename: str,
                    document_group: str, document_subgroup: str, document_name: str,
                    metadata: Dict | None = None) -> Dict:
    import logging
    logger = logging.getLogger(__name__)
    
    key = f"property/{property_id}/{document_group}/{filename}"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    
    sb.storage.from_(BUCKET).upload(key, file_bytes, {"content-type": content_type, "upsert": "true"})
    signed = sb.storage.from_(BUCKET).create_signed_url(key, 3600)
    
    schema = docs_schema(property_id)
    sg = document_subgroup or ""
    expires_at = utcnow_iso()

    upd = {
        "storage_key": key,
        "content_type": content_type,
        "metadata": metadata or {},
        "last_signed_url": signed.get("signedURL"),
        "signed_url_expires_at": expires_at,
    }

    existing = []
    try:
        all_docs = sb.rpc("list_property_documents", {"p_id": property_id}).execute().data or []
        existing = [
            d for d in all_docs
            if d.get("document_group") == document_group
            and (d.get("document_subgroup") or "") == sg
            and d.get("document_name") == document_name
        ]
        if not existing:
            # Logic for auto-seeding with V3 structure
            try:
                logger.info(f"⚠️ Cell not found, initializing V3 schema for {property_id}")
                sb.rpc("ensure_documents_schema_v2", {"p_id": property_id}).execute()
                sb.rpc("seed_documents_v3", {"p_id": property_id}).execute()
                logger.info("✅ V3 schema initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize V3 schema: {e}")
                pass
        
        payload = {
            "p_id": property_id,
            "g": document_group,
            "sg": sg,
            "n": document_name,
            "storage_key": key,
            "content_type": content_type,
            "metadata": metadata or {},
            "signed_url": signed.get("signedURL"),
            "expires_at": expires_at,
        }
        sb.rpc("update_property_document_link", payload).execute()
        
    except Exception as e:
        raise Exception(f"Failed to update database: {e}")

    facturas_info = {}
    try:
        facturas_info = _maybe_generate_facturas(property_id, document_group, sg, document_name, existing[0]["id"] if existing else None)
    except Exception:
        pass

    result = {"storage_key": key, "signed_url": signed.get("signedURL"), "document_name": document_name}
    if facturas_info:
        result["facturas_generated"] = facturas_info
    return result

def _month_sequence(start_date: dt.date, count: int, day_of_month: int, step: int = 1) -> List[dt.date]:
    dates: List[dt.date] = []
    dom = max(1, min(28, int(day_of_month)))
    y, m = start_date.year, start_date.month
    for i in range(count):
        month = m + (i * step)
        year = y + (month - 1) // 12
        mm = ((month - 1) % 12) + 1
        dates.append(dt.date(year, mm, dom))
    return dates

def _maybe_generate_facturas(property_id: str, group: str, subgroup: str, name: str, parent_id: Optional[str]) -> Dict:
    key = (group, subgroup or "", name)
    if key not in FACTURABLE_DOCS:
        return {"status": "not_facturable"}

    try:
        from .rag_tool import qa_payment_schedule
    except Exception:
        return {"status": "rag_unavailable"}

    info = qa_payment_schedule(property_id, group, subgroup, name)
    extracted = info.get("extracted", {}) if isinstance(info, dict) else {}
    frequency = extracted.get("frequency")
    day_of_month = extracted.get("day_of_month")
    total_payments = extracted.get("total_payments")
    contract_years = extracted.get("contract_years")
    
    if (not day_of_month) and info.get("next_due_date"):
        try:
            dom = int(str(info.get("next_due_date")).split("-")[-1])
            if 1 <= dom <= 28:
                day_of_month = dom
                frequency = frequency or "monthly"
        except Exception:
            pass
    
    if not frequency or not day_of_month:
        return {"status": "rag_failed", "info": info}
    
    if total_payments:
        count = int(total_payments)
    elif frequency == "yearly":
        count = contract_years if contract_years else 1
    elif frequency == "quarterly":
        count = (contract_years * 4) if contract_years else 4
    elif frequency == "monthly":
        count = (contract_years * 12) if contract_years else 12
    elif frequency == "every_15_days":
        count = (contract_years * 24) if contract_years else 24
    else:
        count = 12
    
    count = min(count, 36)
    start = dt.date.today()
    
    if frequency == "monthly":
        seq = _month_sequence(start, count, int(day_of_month))
    elif frequency == "quarterly":
        seq = _month_sequence(start, count, int(day_of_month), step=3)
    elif frequency == "yearly":
        seq = _month_sequence(start, count, int(day_of_month), step=12)
    else:
        seq = _month_sequence(start, count, int(day_of_month))

    base_title = FACTURABLE_DOCS[key]
    created = 0
    for d in seq:
        factura_name = f"{base_title} — {d.isoformat()}"
        try:
            sb.rpc("insert_property_document", {
                "p_id": property_id,
                "g": group,
                "sg": subgroup or "",
                "n": factura_name,
                "doc_kind": "factura",
                "parent_id": parent_id,
                "due_date": d.isoformat(),
                "is_placeholder": True,
                "is_auto_generated": True,
                "metadata": {"generated_from": name}
            }).execute()
            created += 1
        except Exception:
            pass
    return {"status": "created", "count": created, "day": int(day_of_month), "frequency": frequency}

def seed_facturas_for(property_id: str, document_group: str, document_subgroup: str, document_name: str,
                      day_of_month: int, months: int = 12, start_date: Optional[str] = None) -> Dict:
    sg = document_subgroup or ""
    all_docs = sb.rpc("list_property_documents", {"p_id": property_id}).execute().data or []
    parent_id = None
    for d in all_docs:
        if (d.get("document_group") == document_group
            and (d.get("document_subgroup") or "") == sg
            and d.get("document_name") == document_name):
            parent_id = d.get("id")
            break
    if not parent_id:
        return {"created": 0, "error": "parent_not_found"}
    base_title = FACTURABLE_DOCS.get((document_group, sg, document_name), "Facturas")
    start = dt.date.fromisoformat(start_date) if start_date else dt.date.today()
    seq = _month_sequence(start, max(1, int(months)), max(1, min(28, int(day_of_month))))
    created = 0
    for d in seq:
        factura_name = f"{base_title} — {d.isoformat()}"
        try:
            sb.rpc("insert_property_document", {
                "p_id": property_id,
                "g": document_group,
                "sg": sg,
                "n": factura_name,
                "doc_kind": "factura",
                "parent_id": parent_id,
                "due_date": d.isoformat(),
                "is_placeholder": True,
                "is_auto_generated": True,
                "metadata": {"generated_from": document_name, "seeded": True}
            }).execute()
            created += 1
        except Exception:
            pass
    return {"created": created}

def list_docs(property_id: str) -> List[Dict]:
    """List all documents associated with a property."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # MANINOS: Read directly from maninos_documents table (simple approach)
        result = sb.table("maninos_documents").select("*").eq("property_id", property_id).execute()
        documents = result.data or []
        
        logger.info(f"✅ [list_docs] Found {len(documents)} documents for property {property_id}")
        
        # Return list of documents with storage_key indicating they're uploaded
        return documents
        
    except Exception as e:
        logger.error(f"❌ [list_docs] Error reading from maninos_documents: {e}")
        # Return empty list if table doesn't exist or other error
        return []

def signed_url_for(property_id: str, document_group: str, document_subgroup: str, document_name: str, expires: int = 31536000) -> str:
    import logging
    logger = logging.getLogger(__name__)
    
    sg = document_subgroup or ""
    
    # Try exact match first
    key = sb.rpc(
        "get_property_document_storage_key",
        {"p_id": property_id, "g": document_group, "sg": sg, "n": document_name}
    ).execute().data
    
    if key:
        return sb.storage.from_(BUCKET).create_signed_url(key, expires)["signedURL"]
    
    # If exact match fails, try fuzzy matching on all documents in this group/subgroup
    logger.info(f"[signed_url_for] Exact match failed for '{document_name}', trying fuzzy match...")
    all_rows = sb.rpc("list_property_documents", {"p_id": property_id}).execute().data or []
    
    # First, filter documents in the same group/subgroup that have a file
    candidates = [
        r for r in all_rows
        if r.get("document_group") == document_group
        and (r.get("document_subgroup") or "") == sg
        and (r.get("storage_key") or r.get("file_storage_key"))  # Only documents with uploaded files
    ]
    
    # If no candidates in the exact subgroup, expand search to the entire group
    if not candidates:
        logger.info(f"[signed_url_for] No documents in {document_group}/{sg}, expanding search to entire {document_group} group...")
        # Debug: log all documents in this property
        logger.info(f"[signed_url_for] DEBUG: Total documents in property: {len(all_rows)}")
        for r in all_rows:
            has_file = bool(r.get("storage_key") or r.get("file_storage_key"))
            # Verbose debug logging disabled - causes log bloat with 60+ documents
            # logger.debug(f"[signed_url_for] doc='{r.get('document_name')}', group={r.get('document_group')}, subgroup='{r.get('document_subgroup')}', has_file={has_file}")
        
        candidates = [
            r for r in all_rows
            if r.get("document_group") == document_group
            and (r.get("storage_key") or r.get("file_storage_key"))  # Only documents with uploaded files (ignore subgroup)
        ]
        logger.info(f"[signed_url_for] DEBUG: Found {len(candidates)} candidates in {document_group} group")
    
    # Check if any candidate contains the requested name (fuzzy match)
    # e.g., "Contrato arquitecto" matches "Contrato arquitecto + facturas arquitecto"
    normalized_request = document_name.lower().strip()
    for candidate in candidates:
        candidate_name = candidate.get("document_name", "").lower().strip()
        if normalized_request in candidate_name or candidate_name in normalized_request:
            matched_name = candidate.get("document_name")
            matched_subgroup = candidate.get("document_subgroup") or ""
            logger.info(f"[signed_url_for] ✅ Fuzzy match: '{document_name}' → '{matched_name}' (subgroup: '{matched_subgroup}')")
            # Now get the signed URL for the matched document using the CORRECT subgroup from the candidate
            key = sb.rpc(
                "get_property_document_storage_key",
                {"p_id": property_id, "g": document_group, "sg": matched_subgroup, "n": matched_name}
            ).execute().data
            if key:
                return sb.storage.from_(BUCKET).create_signed_url(key, expires)["signedURL"]
    
    # If no fuzzy match found, raise error
    candidate_names = [c.get("document_name") for c in candidates]
    logger.error(f"[signed_url_for] ❌ No match for '{document_name}' in {document_group}/{sg}. Candidates: {candidate_names}")
    raise ValueError(f"No file stored for '{document_name}'. Available: {', '.join(candidate_names) if candidate_names else 'none'}")

def slot_exists(property_id: str, document_group: str, document_subgroup: str, document_name: str) -> Dict:
    sg = document_subgroup or ""
    rows = sb.rpc("list_property_documents", {"p_id": property_id}).execute().data or []
    names = [r["document_name"] for r in rows if r.get("document_group") == document_group and (r.get("document_subgroup") or "") == sg]
    return {"exists": document_name in names, "candidates": names}

def list_related_facturas(property_id: str, document_group: str, document_subgroup: str, document_name: str) -> List[Dict]:
    sg = document_subgroup or ""
    try:
        sb.postgrest.schema = "public"
        all_rows = sb.rpc("list_property_documents", {"p_id": property_id}).execute().data or []
        parent_id = None
        for r in all_rows:
            if (
                r.get("document_group") == document_group
                and (r.get("document_subgroup") or "") == sg
                and r.get("document_name") == document_name
            ):
                parent_id = r.get("id")
                break
        rel: List[Dict] = []
        for r in all_rows:
            if (
                r.get("document_group") == document_group
                and (r.get("document_subgroup") or "") == sg
                and r.get("document_kind") == "factura"
                and (not parent_id or r.get("parent_document_id") == parent_id)
            ):
                rel.append({
                    "document_name": r.get("document_name"),
                    "due_date": r.get("due_date"),
                    "placeholder": r.get("placeholder"),
                    "storage_key": r.get("storage_key"),
                    "metadata": r.get("metadata"),
                })
        return rel
    except Exception:
        return []

def purge_property_documents(property_id: str) -> dict:
    rows = list_docs(property_id)
    removed = 0
    cleared = 0
    for r in rows:
        key = r.get("storage_key")
        if key:
            try:
                sb.storage.from_(BUCKET).remove([key])
                removed += 1
            except Exception:
                pass
            try:
                payload = {
                    "p_id": property_id,
                    "g": r.get("document_group"),
                    "sg": r.get("document_subgroup") or "",
                    "n": r.get("document_name"),
                    "storage_key": None,  # Use None to store NULL in DB
                    "content_type": None,
                    "metadata": {},
                    "signed_url": None,
                    "expires_at": None,
                }
                sb.rpc("update_property_document_link", payload).execute()
                cleared += 1
            except Exception:
                pass
    return {"removed_files": removed, "cleared_rows": cleared}

def purge_all_documents() -> dict:
    props = (sb.table("properties").select("id,name").execute()).data
    total_removed = 0
    total_cleared = 0
    for p in props or []:
        res = purge_property_documents(p["id"])
        total_removed += res.get("removed_files", 0)
        total_cleared += res.get("cleared_rows", 0)
    return {"properties": len(props or []), "removed_files": total_removed, "cleared_rows": total_cleared}

def seed_mock_documents(property_id: str, index_after: bool = True) -> dict:
    import re
    seeded = 0
    errors: List[str] = []
    rows = list_docs(property_id)
    for r in rows:
        if r.get("storage_key"):
            continue
        group = r.get("document_group", "")
        subgroup = r.get("document_subgroup", "") or ""
        name = r.get("document_name", "Documento")
        base = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_") or "doc"
        filename = f"mock_{base}.txt"
        content = (
            f"DOCUMENTO SIMULADO PARA PRUEBAS\n\n"
            f"Propiedad: {property_id}\nGrupo: {group}\nSubgrupo: {subgroup}\nNombre: {name}\n\n"
            "Este archivo es un placeholder generado automáticamente para permitir el prototipado del framework de resumen.\n"
        ).encode("utf-8")
        try:
            upload_and_link(property_id, content, filename, group, subgroup, name, metadata={"mock": True})
            if index_after:
                try:
                    from .rag_index import index_document
                    index_document(property_id, group, subgroup, name)
                except Exception:
                    pass
            seeded += 1
        except Exception as e:
            errors.append(f"{group}/{subgroup}/{name}: {e}")
    return {"seeded": seeded, "errors": errors}

# NEW TOOL for Strategy Management
def set_property_strategy(property_id: str, strategy: str) -> str:
    """Set the management strategy for a property (R2B, PROMOCION, R2B_VENTA, R2B_PM).
    This unlocks the corresponding document sections.
    """
    valid_strategies = ["R2B", "PROMOCION", "R2B_VENTA", "R2B_PM"]
    if strategy not in valid_strategies:
        return f"Error: Invalid strategy. Must be one of {valid_strategies}"
    
    try:
        sb.rpc("set_property_strategy", {"p_id": property_id, "new_strategy": strategy}).execute()
        return f"Success: Property strategy set to {strategy}"
    except Exception as e:
        return f"Error setting strategy: {e}"

def get_property_strategy(property_id: str) -> str:
    try:
        res = sb.rpc("get_property_strategy", {"p_id": property_id}).execute()
        return res.data or "PENDING"
    except Exception:
        return "UNKNOWN"


def delete_document(property_id: str, document_name: str, document_group: str = "", document_subgroup: str = "", confirmed: bool = False) -> Dict:
    """
    Delete a document from a SPECIFIC property.
    
    CRITICAL: This only deletes the document from the specified property_id.
    It does NOT affect documents in other properties.
    
    TWO-STEP PROCESS:
    1. First call WITHOUT confirmed=True: Returns document details for user confirmation
    2. Second call WITH confirmed=True + exact group/subgroup: Executes deletion
    
    Args:
        property_id: UUID of the property (REQUIRED - ensures we only delete from THIS property)
        document_name: Name of the document to delete (can be partial for fuzzy matching)
        document_group: Optional - filter by group (COMPRA, R2B, Promoción). REQUIRED for confirmed=True
        document_subgroup: Optional - filter by subgroup (Diseño, Venta, etc.)
        confirmed: If True, execute deletion. If False, return document details for confirmation.
    
    Returns:
        - If confirmed=False: {"needs_confirmation": True, "document": {...}, "message": "..."}
        - If confirmed=True: {"success": True, "deleted_document": "...", ...}
        - On error: {"success": False, "error": "..."}
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not property_id:
        return {"success": False, "error": "property_id is required to delete a document"}
    
    logger.info(f"🗑️ [delete_document] Searching for '{document_name}' in property {property_id}")
    
    # Get all documents for this property
    all_docs = list_docs(property_id)
    if not all_docs:
        return {"success": False, "error": f"No documents found for property {property_id}"}
    
    # Find matching document(s) - fuzzy match on name
    # CRITICAL: Prioritize documents with storage_key (actually uploaded files)
    normalized_search = document_name.lower().strip()
    matches = []
    fuzzy_matches = []  # Store (doc, similarity_score) for fuzzy matching
    
    for doc in all_docs:
        doc_name = doc.get("document_name", "").lower().strip()
        doc_group = doc.get("document_group", "")
        doc_subgroup = doc.get("document_subgroup", "") or ""
        has_file = bool(doc.get("storage_key") or doc.get("file_storage_key"))
        
        # If group/subgroup filters provided, check them too
        group_matches = not document_group or doc_group.lower() == document_group.lower()
        subgroup_matches = not document_subgroup or doc_subgroup.lower() == document_subgroup.lower()
        
        if not (group_matches and subgroup_matches):
            continue
        
        # Check for exact or partial substring match first
        if normalized_search in doc_name or doc_name in normalized_search:
            matches.append((doc, has_file))
            continue
        
        # Fuzzy matching using SequenceMatcher
        # "impuesto de venta" vs "impuestos de venta" should match
        similarity = SequenceMatcher(None, normalized_search, doc_name).ratio()
        
        # Also check word-by-word similarity (helps with singular/plural)
        search_words = set(normalized_search.split())
        doc_words = set(doc_name.split())
        common_words = search_words & doc_words
        word_overlap = len(common_words) / max(len(search_words), 1)
        
        # Combined score: similarity + word overlap bonus
        combined_score = similarity + (word_overlap * 0.3)
        
        if combined_score >= 0.75:  # Threshold for fuzzy match
            fuzzy_matches.append((doc, combined_score, has_file))
            logger.info(f"🔍 [delete_document] Fuzzy match: '{normalized_search}' ~ '{doc_name}' (score: {combined_score:.2f}, has_file: {has_file})")
    
    # If no exact matches, use fuzzy matches
    if not matches and fuzzy_matches:
        # Sort by: 1) has_file (True first), 2) score (highest first)
        fuzzy_matches.sort(key=lambda x: (x[2], x[1]), reverse=True)
        best_match = fuzzy_matches[0]
        matches.append((best_match[0], best_match[2]))
        logger.info(f"✅ [delete_document] Using best fuzzy match: {best_match[0].get('document_name')} (score: {best_match[1]:.2f}, has_file: {best_match[2]})")
    
    # CRITICAL: Prioritize documents with files over empty placeholders
    # Sort matches: documents with storage_key first
    if matches:
        matches.sort(key=lambda x: x[1], reverse=True)  # has_file=True first
        # Extract just the docs
        matches = [m[0] for m in matches]
    
    if not matches:
        # List available documents to help user
        available = [d.get("document_name") for d in all_docs if d.get("storage_key")]
        return {
            "success": False, 
            "error": f"No document matching '{document_name}' found in this property",
            "available_documents": available[:10]  # Show first 10
        }
    
    if len(matches) > 1:
        # Multiple matches - show all options for user to choose
        match_info = []
        for m in matches:
            has_file = bool(m.get("storage_key") or m.get("file_storage_key"))
            match_info.append({
                "document_name": m.get("document_name"),
                "document_group": m.get("document_group"),
                "document_subgroup": m.get("document_subgroup") or "",
                "has_file": has_file,
                "display": f"{m.get('document_group')}/{m.get('document_subgroup') or ''}{'/' if m.get('document_subgroup') else ''}{m.get('document_name')} {'✅' if has_file else '⏳'}"
            })
        return {
            "success": False,
            "needs_selection": True,
            "error": f"Encontré {len(matches)} documentos que coinciden con '{document_name}':",
            "matches": match_info,
            "message": "Por favor, especifica cuál quieres eliminar indicando el grupo (ej: 'R2B/Venta/Impuestos de venta')."
        }
    
    # Single match found
    doc_to_delete = matches[0]
    doc_id = doc_to_delete.get("id")
    storage_key = doc_to_delete.get("storage_key") or doc_to_delete.get("file_storage_key")
    full_name = doc_to_delete.get("document_name")
    group = doc_to_delete.get("document_group")
    subgroup = doc_to_delete.get("document_subgroup") or ""
    has_file = bool(storage_key)
    
    # Build display path for confirmation
    display_path = f"{group}"
    if subgroup:
        display_path += f" → {subgroup}"
    display_path += f" → {full_name}"
    
    logger.info(f"🗑️ [delete_document] Found document: {full_name} in {group}/{subgroup} (has_file={has_file}, confirmed={confirmed})")
    
    # ============================================================
    # STEP 1: If not confirmed, return details for user confirmation
    # ============================================================
    if not confirmed:
        return {
            "success": True,
            "needs_confirmation": True,
            "document": {
                "document_name": full_name,
                "document_group": group,
                "document_subgroup": subgroup,
                "has_file": has_file,
                "display_path": display_path
            },
            "message": f"¿Confirmas que quieres eliminar el documento '{full_name}' del grupo **{display_path}**? {'(Tiene archivo subido ✅)' if has_file else '(Sin archivo ⏳)'}",
            "instruction": "Para confirmar, llama delete_document con confirmed=True y los mismos parámetros."
        }
    
    # ============================================================
    # STEP 2: Confirmed - proceed with deletion
    # ============================================================
    
    # Warn if trying to delete a document without a file
    if not storage_key:
        logger.warning(f"⚠️ [delete_document] Document '{full_name}' has no file (storage_key=None). Nothing to delete from storage.")
    
    # Delete from storage if file exists
    if storage_key:
        try:
            sb.storage.from_(BUCKET).remove([storage_key])
            logger.info(f"✅ [delete_document] Removed file from storage: {storage_key}")
        except Exception as e:
            logger.warning(f"⚠️ [delete_document] Could not remove file from storage: {e}")
    
    # Clear the document link (set storage_key to NULL, keep the schema cell)
    try:
        payload = {
            "p_id": property_id,
            "g": group,
            "sg": subgroup,
            "n": full_name,
            "storage_key": None,
            "content_type": None,
            "metadata": {},
            "signed_url": None,
            "expires_at": None,
        }
        sb.rpc("update_property_document_link", payload).execute()
        logger.info(f"✅ [delete_document] Cleared document link in database (storage_key=NULL)")
    except Exception as e:
        logger.error(f"❌ [delete_document] Failed to clear document link: {e}")
        return {"success": False, "error": f"Failed to update database: {e}"}
    
    return {
        "success": True,
        "deleted_document": full_name,
        "document_group": group,
        "document_subgroup": subgroup,
        "property_id": property_id,
        "message": f"✅ Documento '{full_name}' eliminado correctamente del grupo {display_path}."
    }


# ============================================================
# MANINOS AI: Email Document Tool
# ============================================================

def get_document_for_email(property_id: str, document_id: str = "", document_type: str = "") -> Dict:
    """
    Get document content (binary) for sending by email.
    
    For MANINOS AI: Retrieves documents from maninos_documents table.
    
    Args:
        property_id: UUID of the property (REQUIRED)
        document_id: UUID of the specific document (optional - use if you know the exact document ID)
        document_type: Type of document ('title_status', 'property_listing', 'property_photos') - optional
    
    Returns:
        {
            "success": True,
            "filename": "title_status.pdf",
            "content": bytes,  # Binary content ready for email attachment
            "content_type": "application/pdf",
            "document_type": "title_status",
            "document_name": "1_title_status_example.txt"
        }
        
        OR on error:
        {
            "success": False,
            "error": "Error message"
        }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not property_id:
        return {"success": False, "error": "property_id is required"}
    
    logger.info(f"📧 [get_document_for_email] Fetching document for property {property_id}, document_id={document_id}, document_type={document_type}")
    
    try:
        # Query maninos_documents table
        query = sb.table("maninos_documents").select("*").eq("property_id", property_id)
        
        if document_id:
            query = query.eq("id", document_id)
        elif document_type:
            query = query.eq("document_type", document_type)
        else:
            return {"success": False, "error": "Either document_id or document_type is required"}
        
        result = query.execute()
        
        if not result.data or len(result.data) == 0:
            return {
                "success": False,
                "error": f"No document found for property_id={property_id}, document_id={document_id}, document_type={document_type}"
            }
        
        # Get first matching document
        doc = result.data[0]
        # Try both storage_path (new) and storage_key (legacy) for compatibility
        storage_path = doc.get("storage_path") or doc.get("storage_key")
        document_name = doc.get("document_name", "document")
        content_type = doc.get("content_type", "application/octet-stream")
        doc_type = doc.get("document_type", "")
        doc_id = doc.get("id", "")
        
        if not storage_path:
            return {
                "success": False,
                "error": f"Document '{document_name}' has no storage_path (not uploaded yet)"
            }
        
        logger.info(f"📥 [get_document_for_email] Downloading file from storage: {storage_path}")
        
        # Download file content from Supabase Storage
        try:
            file_bytes = sb.storage.from_(BUCKET).download(storage_path)
            logger.info(f"✅ [get_document_for_email] Downloaded {len(file_bytes)} bytes")
            
            return {
                "success": True,
                "filename": document_name,
                "content": file_bytes,
                "content_type": content_type,
                "document_type": doc_type,
                "document_id": doc_id,
                "document_name": document_name,
                "size_bytes": len(file_bytes)
            }
        
        except Exception as download_error:
            logger.error(f"❌ [get_document_for_email] Failed to download from storage: {download_error}")
            return {
                "success": False,
                "error": f"Failed to download document from storage: {str(download_error)}",
                "storage_path": storage_path
            }
    
    except Exception as e:
        logger.error(f"❌ [get_document_for_email] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Database error: {str(e)}"
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ARMARIO DIGITAL ABOKA - Funciones para la nueva estructura de 6 cajones
# ═══════════════════════════════════════════════════════════════════════════════

def list_armario(property_id: str, cajon: str = None) -> List[Dict]:
    """
    Lista todos los documentos del armario digital de una propiedad.
    
    Args:
        property_id: UUID de la propiedad
        cajon: Opcional - filtrar por cajón (COMPRA, REFORMA, FINANCIERO, GESTIONES, VENTA, CIERRE)
    
    Returns:
        Lista de documentos con su estado (subido/pendiente)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        params = {"p_property_id": property_id}
        if cajon:
            params["p_cajon"] = cajon
        
        result = sb.rpc("list_armario_documents", params).execute()
        documents = result.data or []
        
        logger.info(f"✅ [list_armario] Found {len(documents)} documents for property {property_id}" + 
                   (f" in cajón {cajon}" if cajon else ""))
        
        return documents
        
    except Exception as e:
        logger.error(f"❌ [list_armario] Error: {e}")
        return []


def get_armario_summary(property_id: str) -> List[Dict]:
    """
    Obtiene un resumen del progreso del armario por cajón.
    
    Returns:
        Lista con estadísticas por cajón:
        - cajon: Nombre del cajón
        - total_docs: Total de documentos
        - uploaded_docs: Documentos subidos
        - required_docs: Documentos obligatorios
        - required_uploaded: Obligatorios subidos
        - completion_percentage: % completado de obligatorios
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        result = sb.rpc("get_armario_summary", {"p_property_id": property_id}).execute()
        summary = result.data or []
        
        logger.info(f"✅ [get_armario_summary] Got summary for property {property_id}: {len(summary)} cajones")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ [get_armario_summary] Error: {e}")
        return []


def upload_to_armario(
    property_id: str,
    file_bytes: bytes,
    filename: str,
    cajon: str,
    subcajon: str,
    document_name: str,
    importe: float = None,
    fecha_documento: str = None
) -> Dict:
    """
    Sube un documento al armario digital.
    
    Args:
        property_id: UUID de la propiedad
        file_bytes: Contenido binario del archivo
        filename: Nombre original del archivo
        cajon: Cajón destino (COMPRA, REFORMA, FINANCIERO, GESTIONES, VENTA, CIERRE)
        subcajon: Subcajón destino (ej: "Due Diligence", "Contrata", etc.)
        document_name: Nombre canónico del documento
        importe: Opcional - importe asociado (para facturas)
        fecha_documento: Opcional - fecha del documento (ISO format: YYYY-MM-DD)
    
    Returns:
        {"success": True, "document_id": "...", "storage_path": "...", ...}
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 1. Subir archivo a Supabase Storage
        storage_path = f"armario/{property_id}/{cajon}/{subcajon}/{filename}"
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        
        sb.storage.from_(BUCKET).upload(
            storage_path, 
            file_bytes, 
            {"content-type": content_type, "upsert": "true"}
        )
        
        logger.info(f"✅ [upload_to_armario] File uploaded to storage: {storage_path}")
        
        # 2. Registrar en la tabla armario_documents via RPC
        params = {
            "p_property_id": property_id,
            "p_cajon": cajon,
            "p_subcajon": subcajon,
            "p_document_name": document_name,
            "p_storage_path": storage_path,
            "p_content_type": content_type,
            "p_original_filename": filename,
        }
        
        if importe is not None:
            params["p_importe"] = importe
        if fecha_documento:
            params["p_fecha_documento"] = fecha_documento
        
        result = sb.rpc("upload_armario_document", params).execute()
        
        if result.data:
            logger.info(f"✅ [upload_to_armario] Document registered: {document_name} in {cajon}/{subcajon}")
            # Ensure we return document_id
            response = result.data
            if isinstance(response, dict) and not response.get("document_id"):
                # Try to get document_id from database by storage_path
                doc_result = sb.table("armario_documents")\
                    .select("id")\
                    .eq("property_id", property_id)\
                    .eq("storage_path", storage_path)\
                    .single()\
                    .execute()
                if doc_result.data:
                    response["document_id"] = doc_result.data["id"]
            response["storage_path"] = storage_path
            return response
        else:
            # RPC returned no data, try to get document_id directly
            doc_result = sb.table("armario_documents")\
                .select("id")\
                .eq("property_id", property_id)\
                .eq("storage_path", storage_path)\
                .single()\
                .execute()
            document_id = doc_result.data["id"] if doc_result.data else None
            return {
                "success": True, 
                "storage_path": storage_path, 
                "document_id": document_id,
                "message": "Uploaded but RPC returned no data"
            }
        
    except Exception as e:
        logger.error(f"❌ [upload_to_armario] Error: {e}")
        return {"success": False, "error": str(e)}


def seed_armario(property_id: str) -> Dict:
    """
    Inicializa el armario digital de una propiedad con todas las celdas vacías.
    
    Normalmente esto se hace automáticamente al crear una propiedad (trigger),
    pero esta función permite hacerlo manualmente para propiedades existentes.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        result = sb.rpc("seed_armario_digital", {"p_property_id": property_id}).execute()
        
        if result.data:
            logger.info(f"✅ [seed_armario] Armario initialized: {result.data}")
            return result.data
        else:
            return {"success": True, "message": "Seed completed"}
        
    except Exception as e:
        logger.error(f"❌ [seed_armario] Error: {e}")
        return {"success": False, "error": str(e)}


def classify_for_armario(filename: str, text_hint: str = "", file_bytes: bytes = None) -> Dict:
    """
    Clasifica un documento para determinar en qué cajón/subcajón del armario debe ir.
    
    Usa las palabras clave de DOC_GROUPS para clasificar automáticamente.
    
    Args:
        filename: Nombre del archivo
        text_hint: Pista adicional del usuario (ej: "esto es la nota simple")
        file_bytes: Opcional - contenido del archivo para clasificación RAG
    
    Returns:
        {
            "cajon": "COMPRA",
            "subcajon": "Due Diligence", 
            "document_name": "Nota Simple Informativa"
        }
        
        O en caso de error:
        {
            "error": "...",
            "available_cajones": ["COMPRA", "REFORMA", ...],
            "cajon": None
        }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    fn = _normalize(filename)
    hint = _normalize(text_hint)
    combined = fn + " " + hint
    
    # STEP 1: Try exact keyword matching
    all_keywords = []
    for key, kws in DOC_GROUPS.items():
        for kw in kws:
            parts = key.split(":")
            cajon = parts[0]
            subcajon = parts[1] if len(parts) > 1 else ""
            all_keywords.append((kw, cajon, subcajon))
    
    # Sort by keyword length (longer = more specific)
    all_keywords.sort(key=lambda x: -len(x[0]))
    
    for kw, cajon, subcajon in all_keywords:
        if kw in combined:
            doc_name = KEYWORD_TO_DOCNAME.get(kw, kw.title())
            logger.info(f"✅ [classify_for_armario] EXACT match: '{kw}' → {cajon}/{subcajon}")
            return {
                "cajon": cajon,
                "subcajon": subcajon,
                "document_name": doc_name
            }
    
    # STEP 2: Try fuzzy matching
    logger.info(f"🔍 [classify_for_armario] No exact match, trying fuzzy for: {filename}")
    fuzzy_result = _fuzzy_match_keywords(combined, min_similarity=0.65)
    if fuzzy_result:
        kw, cajon, subcajon = fuzzy_result
        doc_name = KEYWORD_TO_DOCNAME.get(kw, kw.title())
        logger.info(f"✅ [classify_for_armario] FUZZY match: '{filename}' → {cajon}/{subcajon}")
        return {
            "cajon": cajon,
            "subcajon": subcajon,
            "document_name": doc_name
        }
    
    # STEP 3: Try RAG classification if file bytes available
    if file_bytes:
        logger.info(f"📖 [classify_for_armario] Trying RAG classification for: {filename}")
        rag_result = _rag_classify_document(file_bytes, filename)
        if rag_result:
            kw, cajon, subcajon = rag_result
            doc_name = KEYWORD_TO_DOCNAME.get(kw, kw.title())
            logger.info(f"✅ [classify_for_armario] RAG match: '{filename}' → {cajon}/{subcajon}")
            return {
                "cajon": cajon,
                "subcajon": subcajon,
                "document_name": doc_name
            }
    
    # STEP 4: Could not classify
    available_cajones = ["COMPRA", "REFORMA", "FINANCIERO", "GESTIONES", "VENTA", "CIERRE"]
    logger.warning(f"⚠️ [classify_for_armario] Could not classify: {filename}")
    
    return {
        "error": "No pude clasificar automáticamente este documento",
        "message": f"No encontré palabras clave para '{filename}'. Por favor indica el cajón y subcajón.",
        "available_cajones": available_cajones,
        "cajon": None,
        "subcajon": None,
        "document_name": None
    }


def get_armario_document_url(property_id: str, cajon: str, subcajon: str, document_name: str, expires: int = 3600) -> str:
    """
    Genera una URL firmada para descargar un documento del armario.
    
    Args:
        property_id: UUID de la propiedad
        cajon: Cajón del documento
        subcajon: Subcajón del documento
        document_name: Nombre del documento
        expires: Segundos de validez de la URL (default: 1 hora)
    
    Returns:
        URL firmada o None si el documento no existe
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Buscar el documento en la tabla
        docs = list_armario(property_id, cajon)
        
        for doc in docs:
            if (doc.get("subcajon") == subcajon and 
                doc.get("document_name") == document_name and
                doc.get("storage_path")):
                
                storage_path = doc["storage_path"]
                signed = sb.storage.from_(BUCKET).create_signed_url(storage_path, expires)
                
                logger.info(f"✅ [get_armario_document_url] Generated URL for {document_name}")
                return signed.get("signedURL")
        
        logger.warning(f"⚠️ [get_armario_document_url] Document not found or not uploaded: {document_name}")
        return None
        
    except Exception as e:
        logger.error(f"❌ [get_armario_document_url] Error: {e}")
        return None


def classify_document_with_llm(property_id: str, document_hint: str, filename: str = "") -> Dict:
    """
    Intelligent document classification using LLM with full Armario Digital context.
    
    Instead of simple keyword matching, this function:
    1. Fetches ALL documents from the property's Armario Digital
    2. Sends them to the LLM with the document hint
    3. LLM picks the best matching document slot
    
    Args:
        property_id: UUID of the property
        document_hint: Description from email (e.g., "Factura Puerta Cristal Interior")
        filename: Original filename (optional, helps with classification)
    
    Returns:
        {
            "cajon": "REFORMA",
            "subcajon": "Partidas",
            "document_name": "Factura Puertas Cristal Interiores",
            "document_id": "uuid-of-the-document-slot",
            "confidence": 0.95,
            "reasoning": "El documento menciona 'puerta cristal' y existe un slot exacto..."
        }
    """
    import logging
    import openai
    import json
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[classify_document_with_llm] Starting for property {property_id}, hint='{document_hint}'")
        
        # Step 1: Get ALL documents from the Armario Digital
        all_docs = list_armario(property_id)
        
        if not all_docs:
            logger.warning(f"[classify_document_with_llm] No documents found for property {property_id}")
            return {"error": "No documents in Armario Digital"}
        
        # Step 2: Format documents for LLM (group by cajón)
        docs_by_cajon = {}
        for doc in all_docs:
            cajon = doc.get("cajon", "OTROS")
            if cajon not in docs_by_cajon:
                docs_by_cajon[cajon] = []
            docs_by_cajon[cajon].append({
                "id": doc.get("id"),
                "document_name": doc.get("document_name"),
                "subcajon": doc.get("subcajon"),
                "is_uploaded": doc.get("is_uploaded", False)
            })
        
        # Build a readable list for the LLM
        docs_list = ""
        for cajon, docs in docs_by_cajon.items():
            docs_list += f"\n## {cajon}\n"
            for doc in docs:
                status = "✅ ya subido" if doc["is_uploaded"] else "⬚ vacío"
                docs_list += f"  - [{status}] {doc['subcajon']} > {doc['document_name']} (id: {doc['id']})\n"
        
        # Step 3: Ask LLM to pick the best match
        prompt = f"""Eres un experto en clasificación de documentos para reformas inmobiliarias.

DOCUMENTO A CLASIFICAR:
- Descripción: "{document_hint}"
- Archivo: "{filename}"

ARMARIO DIGITAL DE LA PROPIEDAD (todos los slots disponibles):
{docs_list}

Tu tarea: Encuentra el slot del Armario Digital donde MEJOR encaja este documento.

Reglas importantes:
1. Las facturas de materiales de construcción (puertas, ventanas, suelos, cocina, baños, etc.) van en REFORMA > Partidas
2. Las facturas de servicios recurrentes (luz, agua, gas, comunidad) van en GESTIONES > Suministros
3. Los documentos de compra (escrituras, notas simples) van en COMPRA
4. Busca coincidencias por nombre similar (ej: "Factura Puerta Cristal" → "Factura Puertas Cristal Interiores")
5. Prefiere slots vacíos (⬚) sobre slots ya ocupados (✅) si hay match similar

Responde SOLO con un JSON válido:
{{
    "document_id": "el-uuid-del-slot-elegido",
    "document_name": "nombre exacto del slot",
    "cajon": "nombre del cajón",
    "subcajon": "nombre del subcajón",
    "confidence": 0.0-1.0,
    "reasoning": "explicación breve de por qué elegiste este slot"
}}
"""

        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        result = json.loads(response_text)
        
        logger.info(f"[classify_document_with_llm] ✅ LLM chose: {result.get('cajon')}/{result.get('subcajon')}/{result.get('document_name')}")
        logger.info(f"[classify_document_with_llm] Reasoning: {result.get('reasoning')}")
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"[classify_document_with_llm] JSON parse error: {e}, response: {response_text[:200]}")
        return {"error": f"Could not parse LLM response: {e}"}
    except Exception as e:
        logger.error(f"[classify_document_with_llm] Error: {e}")
        return {"error": str(e)}
