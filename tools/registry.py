# tools/registry.py
from __future__ import annotations
from typing import List, Dict, Optional, Union
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)

# import your pure functions
from .property_tools import add_property as _add_property, list_frameworks as _list_frameworks
from .property_tools import get_property as _get_property, find_property as _find_property, list_properties as _list_properties
from .property_tools import search_properties as _search_properties
from .property_tools import delete_property as _delete_property, delete_properties as _delete_properties
from .property_tools import update_property_fields as _update_property_fields
from .docs_tools import (
    propose_slot as _propose_slot,
    upload_and_link as _upload_and_link,
    list_docs as _list_docs,
    signed_url_for as _signed_url_for,
    slot_exists as _slot_exists,
    list_related_facturas as _list_related_facturas,
    seed_facturas_for as _seed_facturas_for,
    seed_mock_documents as _seed_mock_documents,
    purge_property_documents as _purge_property_documents,
    purge_all_documents as _purge_all_documents,
    set_property_strategy as _set_property_strategy,
    get_property_strategy as _get_property_strategy,
    delete_document as _delete_document,
    get_document_for_email as _get_document_for_email,
    # ARMARIO DIGITAL - Nuevas funciones (6 cajones)
    list_armario as _list_armario,
    get_armario_summary as _get_armario_summary,
    upload_to_armario as _upload_to_armario,
    seed_armario as _seed_armario,
    classify_for_armario as _classify_for_armario,
    get_armario_document_url as _get_armario_document_url,
)
# ABOKA AI: numbers_tools now has ABOKA-specific functions
from .numbers_tools import (
    init_financial_template as _init_financial_template,
    get_aboka_financials as _get_aboka_financials,
    update_financial_item as _update_financial_item,
    update_financial_by_name as _update_financial_by_name,
)
from .numbers_agent import (
    compute_and_log as _numbers_compute_and_log,
    generate_numbers_excel as _numbers_excel,
    generate_numbers_table_excel as _numbers_table_excel,
    what_if as _numbers_what_if,
    sensitivity_grid as _numbers_sensitivity,
    break_even_precio as _numbers_break_even,
    chart_waterfall as _numbers_chart_waterfall,
    chart_cost_stack as _numbers_chart_cost_stack,
    chart_sensitivity_heatmap as _numbers_chart_sensitivity,
)
from .summary_tools import get_summary_spec as _get_summary_spec, upsert_summary_value as _upsert_summary_value, compute_summary as _compute_summary
from .summary_ppt import build_summary_ppt as _build_summary_ppt
from .email_tool import send_email as _send_email
from .voice_tool import transcribe_google_wav as _transcribe_google_wav, tts_google as _tts_google, process_voice_input as _process_voice_input, create_voice_response as _create_voice_response
from .rag_tool import summarize_document as _summarize_document, qa_document as _qa_document, qa_payment_schedule as _qa_payment_schedule
from .rag_index import index_document as _index_document, qa_with_citations as _qa_with_citations, index_all_documents as _index_all_documents
from .rag_maninos import query_documents_maninos as _query_documents_maninos, index_document_maninos as _index_document_maninos, index_all_documents_maninos as _index_all_documents_maninos
from .extraction_tools import (
    extract_document_data as _extract_document_data,
    map_concept_to_estudio as _map_concept_to_estudio,
    save_extraction_result as _save_extraction_result,
    get_pending_extractions as _get_pending_extractions,
    approve_extraction as _approve_extraction,
    reject_extraction as _reject_extraction,
    format_extraction_proposal as _format_extraction_proposal,
    get_estudio_label as _get_estudio_label,
)
from .reminders_tools import create_reminder as _create_reminder, extract_payment_date_from_document as _extract_payment_date, list_reminders as _list_reminders, cancel_reminder as _cancel_reminder
# ---------- Set current property (LLM-controlled) ----------
class SetCurrentPropertyInput(BaseModel):
    property_id: str = Field(..., description="UUID of the property to set as current")

@tool("set_current_property")
def set_current_property_tool(property_id: str) -> Dict:
    """Fix the current working property explicitly. LLM must call this after selecting a property. Returns {property_id, property_name}."""
    row = _get_property(property_id)
    if not row:
        return {"error": "property_not_found", "property_id": property_id}
    return {"property_id": row.get("id"), "property_name": row.get("name")}

# ---------- Schemas ----------

class AddPropertyInput(BaseModel):
    name: str = Field(..., description="Property name as shown to user")
    address: str = Field(..., description="Property full address")

@tool("add_property")
def add_property_tool(name: str, address: str) -> Dict:
    """Create a new property in Supabase (triggers provisioning of 3 frameworks)."""
    return _add_property(name, address)


class ListFrameworksInput(BaseModel):
    property_id: str = Field(..., description="UUID of the property")

@tool("list_frameworks")
def list_frameworks_tool(property_id: str) -> Dict:
    """Return schema names for the property's three frameworks."""
    return _list_frameworks(property_id)


class DeletePropertyInput(BaseModel):
    property_id: str = Field(..., description="UUID of the property to delete")
    purge_docs_first: bool = Field(True, description="Whether to purge uploaded documents before deletion")

@tool("delete_property")
def delete_property_tool(property_id: str, purge_docs_first: bool = True) -> Dict:
    """Delete/remove a property (soft-delete) and optionally purge its uploaded documents. 
    Use this when user says "borra la propiedad", "elimina esta propiedad", "delete this property", etc.
    The property_id should be the currently active property unless user specifies a different one.
    Returns {"deleted": True} on success. After deletion, property_id will be automatically cleared from context."""
    return _delete_property(property_id, purge_docs_first)


class DeletePropertiesInput(BaseModel):
    property_ids: List[str] = Field(..., description="List of property UUIDs to delete")
    purge_docs_first: bool = True

@tool("delete_properties")
def delete_properties_tool(property_ids: List[str], purge_docs_first: bool = True) -> Dict:
    """Delete multiple properties (soft-delete) in sequence. Returns per-id results and total deleted.
    Use when the user asks to remove several properties at once, e.g. "borra Casa Demo 2 y Casa Demo 3".
    The LLM should resolve names to ids first using `search_properties` or a prior list.
    """
    return _delete_properties(property_ids, purge_docs_first)


@tool("update_property_fields")
def update_property_fields_tool(property_id: str, fields: Optional[Dict] = None) -> Dict:
    """Update one or more fields of a property.
    
    IMPORTANT: You MUST provide the 'fields' parameter with at least one field to update.
    If you don't have specific fields to update, use calculate_maninos_deal() instead.
    
    Common use cases:
    - Update acquisition_stage: update_property_fields(property_id, {"acquisition_stage": "initial"})
    - Update title_status: update_property_fields(property_id, {"title_status": "Clean/Blue"})
    - Update multiple fields: update_property_fields(property_id, {"arv": 150000, "status": "Ready to Buy"})
    
    Returns {"ok": True, "updated": {...}} on success.
    """
    return _update_property_fields(property_id, fields)


class ProposeDocInput(BaseModel):
    filename: str
    hint: str = Field("", description="Optional free text / user hint to help classification")
    property_id: str = Field("", description="Optional property_id to help match facturas with placeholders")

@tool("propose_doc_slot")
def propose_doc_slot_tool(filename: str, hint: str = "", property_id: str = "", bytes_b64: str = "") -> Dict:
    """Propose where a document should live in the documents framework.
    
    ADVANCED CLASSIFICATION:
    1. Tries exact keyword matching from filename
    2. Tries fuzzy matching (similarity >= 0.65)
    3. If bytes_b64 provided: Reads PDF content with RAG to find keywords
    4. If all fail: Returns error asking user for clarification
    
    Args:
        filename: Name of the file (e.g., "escrituraNotarial.pdf")
        hint: Optional user hint about document type
        property_id: Property UUID (optional, for context)
        bytes_b64: Base64-encoded file bytes (optional, enables RAG classification)
    
    CRITICAL: If this returns an 'error' key, DO NOT proceed with upload. ASK the user for clarification.
    
    Returns:
    - Success: {"document_group": "...", "document_subgroup": "...", "document_name": "..."}
    - Error: {"error": "...", "message": "...", "document_group": None, "document_subgroup": None, "document_name": None}
    
    If you receive an error, you MUST:
    1. Tell the user the error message
    2. Ask for clarification about the document category
    3. DO NOT call upload_and_link with None values
    
    EXAMPLE - Fuzzy match:
    Input: "escrituraNotarial.pdf"
    → Fuzzy matches "escritura notarial" (score 0.85)
    → Returns: {"document_group": "COMPRA", "document_subgroup": "", "document_name": "Escritura notarial de compraventa"}
    
    EXAMPLE - RAG match:
    Input: "documento123.pdf" (with bytes_b64)
    → Reads PDF content: "...licencia de obra...acometidas..."
    → Finds keyword "licencia de obra" in content
    → Returns: {"document_group": "R2B", "document_subgroup": "Diseño", "document_name": "Licencia de obra y acometidas + facturas"}"""
    import base64
    file_bytes = None
    if bytes_b64:
        try:
            file_bytes = base64.b64decode(bytes_b64)
        except Exception:
            pass
    return _propose_slot(filename, hint, property_id, file_bytes)


class UploadAndLinkInput(BaseModel):
    property_id: str
    filename: str
    bytes_b64: str = Field(..., description="Base64 of the file to upload")
    document_group: str
    document_subgroup: str = ""
    document_name: str
    metadata: Dict = {}

@tool("upload_and_link")
def upload_and_link_tool(property_id: str, filename: str, bytes_b64: str,
                         document_group: str, document_subgroup: str, document_name: str,
                         metadata: Dict) -> Dict:
    """Upload the file to Storage and link it to the correct row in docs framework."""
    import base64
    file_bytes = base64.b64decode(bytes_b64)
    return _upload_and_link(property_id, file_bytes, filename,
                            document_group, document_subgroup, document_name, metadata)


class ListDocsInput(BaseModel):
    property_id: str

@tool("list_docs")
def list_docs_tool(property_id: str) -> Dict:
    """List all document rows for this property in REAL-TIME from the database.
    
    CRITICAL: ALWAYS call this tool when user asks to list/show/see documents. DO NOT rely on memory or previous calls.
    
    Args:
        property_id: The UUID of the property (e.g., '27d0e06b-e678-4262-b51f-5134a4ec62ef').
                     NEVER use the property name (e.g., '15Panes'). Always use the UUID from context.
    
    Returns: Dict with explicit categorization to prevent misinterpretation:
    {
        "uploaded": [...],  # Documents with storage_key (ACTUALLY UPLOADED)
        "pending": [...],   # Documents without storage_key (NOT YET UPLOADED)
        "total_uploaded": N,
        "total_pending": M,
        "summary": "Human-readable summary"
    }
    
    Each document has: document_name, document_type, storage_key, uploaded_at."""
    import logging
    logger = logging.getLogger(__name__)
    
    docs = _list_docs(property_id)
    
    # For MANINOS: All documents in maninos_documents table have storage_key (they're all uploaded)
    # There's no concept of "pending" documents in this simplified structure
    uploaded_docs = docs  # All documents from maninos_documents are uploaded
    pending_docs = []
    
    total_uploaded = len(uploaded_docs)
    total_pending = 0
    
    logger.info(f"🔍 [list_docs_tool] Property {property_id[:8]}...")
    logger.info(f"   - Total docs: {len(docs)}")
    logger.info(f"   - Uploaded (with storage_key): {total_uploaded}")
    logger.info(f"   - Pending (no storage_key): {total_pending}")
    
    # Create explicit summary to prevent agent confusion
    if total_uploaded == 0:
        summary = "No hay documentos subidos."
    elif total_uploaded == 1:
        summary = f"Hay 1 documento subido: {uploaded_docs[0].get('document_name', 'Unknown')}"
    elif total_uploaded == 2:
        summary = f"Hay 2 documentos subidos: {uploaded_docs[0].get('document_name', '')} y {uploaded_docs[1].get('document_name', '')}"
    else:
        summary = f"Hay {total_uploaded} documentos subidos."
    
    # Log all uploaded documents for verification
    if uploaded_docs:
        logger.info(f"   - Uploaded documents:")
        for doc in uploaded_docs:
            doc_type = doc.get('document_type', 'Unknown')
            doc_name = doc.get('document_name', 'Unknown')
            logger.info(f"     * [{doc_type}] {doc_name}")
    
    # Return structured data that's IMPOSSIBLE to misinterpret
    return {
        "uploaded": uploaded_docs,
        "pending": pending_docs,
        "total_uploaded": total_uploaded,
        "total_pending": total_pending,
        "summary": summary,
        "all_docs": docs  # Backwards compatibility
    }
    
    return docs


class SignedUrlInput(BaseModel):
    property_id: str
    document_group: str
    document_subgroup: str = ""
    document_name: str

@tool("signed_url_for")
def signed_url_for_tool(property_id: str, document_group: str, document_subgroup: str, document_name: str) -> Dict:
    """Create a signed URL for a stored document. The URL is valid for 24 hours (86400 seconds).
    Use this when you need to send a document link by email.
    Returns: {"signed_url": "https://..."}"""
    # Use 24 hours expiration (86400 seconds) for email links
    url = _signed_url_for(property_id, document_group, document_subgroup, document_name, expires=86400)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[signed_url_for_tool] Generated URL for {document_name}, expires in 24h: {url[:50]}...")
    return {"signed_url": url}


class SlotExistsInput(BaseModel):
    property_id: str
    document_group: str
    document_subgroup: str = ""
    document_name: str

@tool("slot_exists")
def slot_exists_tool(property_id: str, document_group: str, document_subgroup: str, document_name: str) -> Dict:
    """Check if a document slot exists in the per-property documents framework (and list available names)."""
    return _slot_exists(property_id, document_group, document_subgroup, document_name)


# --- Related facturas ---
class ListRelatedFacturasInput(BaseModel):
    property_id: str
    document_group: str
    document_subgroup: str = ""
    document_name: str

@tool("list_related_facturas")
def list_related_facturas_tool(property_id: str, document_group: str, document_subgroup: str, document_name: str) -> List[Dict]:
    """List invoice placeholders/children for a given document (returns name, due_date, placeholder, storage_key)."""
    return _list_related_facturas(property_id, document_group, document_subgroup, document_name)


class SeedFacturasForInput(BaseModel):
    property_id: str
    document_group: str
    document_subgroup: str = ""
    document_name: str
    day_of_month: int = Field(..., ge=1, le=28)
    months: int = Field(12, ge=1, le=24)
    start_date: Optional[str] = Field(None, description="YYYY-MM-DD; default today")

@tool("seed_facturas_for")
def seed_facturas_for_tool(property_id: str, document_group: str, document_subgroup: str, document_name: str,
                           day_of_month: int, months: int = 12, start_date: Optional[str] = None) -> Dict:
    """Create monthly factura placeholders (children) for a parent document. Use when extraction fails or user provides a day. Idempotent."""
    return _seed_facturas_for(property_id, document_group, document_subgroup, document_name, day_of_month, months, start_date)


# --- seed mock docs for prototyping ---
class SeedMockDocsInput(BaseModel):
    property_id: str
    index_after: bool = True

@tool("seed_mock_documents")
def seed_mock_documents_tool(property_id: str, index_after: bool = True) -> Dict:
    """Create placeholder text files for all missing documents of a property. For prototyping only (marks metadata mock=True)."""
    return _seed_mock_documents(property_id, index_after)


# --- Purge documents ---
class PurgePropertyDocsInput(BaseModel):
    property_id: str

@tool("purge_property_documents")
def purge_property_documents_tool(property_id: str) -> Dict:
    """Delete all uploaded files for a single property and clear the document links."""
    return _purge_property_documents(property_id)


@tool("purge_all_documents")
def purge_all_documents_tool() -> Dict:
    """Delete all uploaded files for all properties and clear links."""
    return _purge_all_documents()

# --- Strategy Management (NEW) ---
class SetPropertyStrategyInput(BaseModel):
    property_id: str
    strategy: str = Field(..., description="Strategy: 'R2B', 'PROMOCION', 'R2B_VENTA', 'R2B_PM'")

@tool("set_property_strategy")
def set_property_strategy_tool(property_id: str, strategy: str) -> str:
    """Set the management strategy for a property (R2B, PROMOCION, R2B_VENTA, R2B_PM).
    This unlocks the corresponding document sections.
    """
    return _set_property_strategy(property_id, strategy)

class GetPropertyStrategyInput(BaseModel):
    property_id: str

@tool("get_property_strategy")
def get_property_strategy_tool(property_id: str) -> str:
    """Get the current management strategy for a property."""
    return _get_property_strategy(property_id)


# --- Delete Document (NEW) ---
class DeleteDocumentInput(BaseModel):
    property_id: str = Field(..., description="UUID of the property (REQUIRED)")
    document_name: str = Field(..., description="Name of the document to delete (can be partial for fuzzy matching)")
    document_group: str = Field("", description="Optional - filter by group (COMPRA, R2B, Promoción)")
    document_subgroup: str = Field("", description="Optional - filter by subgroup (Diseño, Venta, etc.)")
    confirmed: bool = Field(False, description="If True, execute deletion. If False, return document details for confirmation.")

@tool("delete_document")
def delete_document_tool(property_id: str, document_name: str, document_group: str = "", document_subgroup: str = "", confirmed: bool = False) -> Dict:
    """Delete a document from a SPECIFIC property. TWO-STEP PROCESS WITH CONFIRMATION.
    
    🚨 WORKFLOW (MUST FOLLOW):
    
    **STEP 1 - Search (confirmed=False):**
    Call with document_name and confirmed=False (default).
    Returns: {"needs_confirmation": True, "document": {...}, "message": "¿Confirmas...?"}
    → Show the confirmation message to user and WAIT for their response.
    
    **STEP 2 - Execute (confirmed=True):**
    After user confirms with "si/sí/confirmo", call AGAIN with:
    - Same document_name
    - document_group and document_subgroup from Step 1 response
    - confirmed=True
    Returns: {"success": True, "deleted_document": "...", "message": "✅ Eliminado..."}
    
    🚨 CRITICAL RULES:
    - NEVER call with confirmed=True on first attempt
    - ALWAYS show confirmation message to user first
    - ALWAYS wait for user to confirm before calling with confirmed=True
    - Use document_group/document_subgroup from Step 1 to ensure correct document
    
    Example flow:
    1. User: "borra el documento impuestos de venta"
    2. You: delete_document(property_id="...", document_name="impuestos de venta")
    3. Tool returns: {"needs_confirmation": True, "document": {"document_group": "R2B", "document_subgroup": "Venta", ...}, "message": "¿Confirmas...?"}
    4. You: "¿Confirmas que quieres eliminar 'Impuestos de venta' del grupo R2B → Venta?"
    5. User: "si"
    6. You: delete_document(property_id="...", document_name="Impuestos de venta", document_group="R2B", document_subgroup="Venta", confirmed=True)
    7. Tool returns: {"success": True, "message": "✅ Eliminado..."}
    """
    return _delete_document(property_id, document_name, document_group, document_subgroup, confirmed)


# --- Get Document For Email (NEW - MANINOS AI) ---
class GetDocumentForEmailInput(BaseModel):
    property_id: str = Field(..., description="UUID of the property (REQUIRED)")
    document_id: str = Field("", description="UUID of the specific document (optional - use if you know the exact document ID)")
    document_type: str = Field("", description="Type of document: 'title_status', 'property_listing', or 'property_photos' (optional)")

@tool("get_document_for_email")
def get_document_for_email_tool(property_id: str, document_id: str = "", document_type: str = "") -> Dict:
    """Get document content (binary) for sending by email attachment.
    
    For MANINOS AI: Retrieves documents from the uploaded documents collection.
    
    Args:
        property_id: UUID of the property (REQUIRED)
        document_id: UUID of the specific document (optional - use if you know the exact document ID)
        document_type: Type of document - 'title_status', 'property_listing', or 'property_photos' (optional)
    
    Returns:
        On success: {
            "success": True,
            "filename": "title_status.pdf",
            "content": bytes,  # Binary content ready for email attachment
            "content_type": "application/pdf",
            "document_type": "title_status",
            "size_bytes": 12345
        }
        
        On error: {
            "success": False,
            "error": "Error message"
        }
    
    Example usage:
        1. User: "Send me the title status document by email"
        2. You: get_document_for_email(property_id="...", document_type="title_status")
        3. Tool returns: {"success": True, "filename": "1_title_status_example.txt", "content": bytes(...), ...}
        4. You: send_email(to=["user@example.com"], subject="Title Status Document", html="<p>Attached is the title status document.</p>", attachments=[("1_title_status_example.txt", bytes(...))])
    """
    return _get_document_for_email(property_id, document_id, document_type)


# ═══════════════════════════════════════════════════════════════════════════════
# ARMARIO DIGITAL ABOKA - Herramientas para gestión de documentos (6 cajones)
# ═══════════════════════════════════════════════════════════════════════════════

class ListArmarioInput(BaseModel):
    property_id: str = Field(..., description="UUID of the property")
    cajon: Optional[str] = Field(None, description="Optional: filter by cajón (COMPRA, REFORMA, FINANCIERO, GESTIONES, VENTA, CIERRE)")

@tool("list_armario")
def list_armario_tool(property_id: str, cajon: str = None) -> List[Dict]:
    """List all documents in the Armario Digital for a property.
    
    The Armario Digital has 6 cajones (drawers):
    - COMPRA: Due Diligence, Contrato, Gastos (acquisition docs)
    - REFORMA: Licencias, Contrata, Partidas, Amueblamiento, Certificados (renovation docs)
    - FINANCIERO: Hipoteca, Gastos Constitución, Cancelación, Seguros, Intereses (financing docs)
    - GESTIONES: Suministros, Comunidad, Impuestos, Comisiones (recurring expenses)
    - VENTA: Dossier Comercial, Cierre, Alquileres (sale docs)
    - CIERRE: Liquidación, Fiscal, Inversores (closing docs)
    
    Each document has:
    - is_uploaded: True if file has been uploaded
    - is_required: True if mandatory document
    - storage_path: Path in storage (null if not uploaded yet)
    
    Returns list of all documents with their upload status.
    """
    return _list_armario(property_id, cajon)


class GetArmarioSummaryInput(BaseModel):
    property_id: str = Field(..., description="UUID of the property")

@tool("get_armario_summary")
def get_armario_summary_tool(property_id: str) -> List[Dict]:
    """Get a summary of document completion progress per cajón.
    
    Returns statistics for each of the 6 cajones:
    - cajon: Name (COMPRA, REFORMA, etc.)
    - total_docs: Total document slots
    - uploaded_docs: Documents already uploaded
    - required_docs: Mandatory documents
    - required_uploaded: Mandatory docs that are uploaded
    - completion_percentage: % of required docs completed
    
    Useful to show users their overall documentation progress.
    """
    return _get_armario_summary(property_id)


class ClassifyForArmarioInput(BaseModel):
    filename: str = Field(..., description="Filename to classify")
    text_hint: str = Field("", description="Optional hint from user about the document type")

@tool("classify_for_armario")
def classify_for_armario_tool(filename: str, text_hint: str = "") -> Dict:
    """Classify a document to determine which cajón/subcajón it belongs to.
    
    Uses keyword matching to automatically determine where to file a document.
    
    Examples:
    - "nota_simple.pdf" → COMPRA / Due Diligence / Nota Simple Informativa
    - "factura_arquitecto.pdf" → REFORMA / Licencias / Contrato y Facturas Arquitecto
    - "recibo_comunidad.pdf" → GESTIONES / Comunidad / Recibos Comunidad
    
    Returns:
    - Success: {"cajon": "...", "subcajon": "...", "document_name": "..."}
    - Error: {"error": "...", "available_cajones": [...], "cajon": None}
    """
    return _classify_for_armario(filename, text_hint)


class UploadToArmarioInput(BaseModel):
    property_id: str = Field(..., description="UUID of the property")
    filename: str = Field(..., description="Original filename")
    bytes_b64: str = Field(..., description="Base64-encoded file content")
    cajon: str = Field(..., description="Target cajón: COMPRA, REFORMA, FINANCIERO, GESTIONES, VENTA, CIERRE")
    subcajon: str = Field(..., description="Target subcajón (e.g., Due Diligence, Contrata, Hipoteca)")
    document_name: str = Field(..., description="Canonical document name in the armario")
    importe: Optional[float] = Field(None, description="Optional: amount associated with document (for invoices)")

@tool("upload_to_armario")
def upload_to_armario_tool(
    property_id: str,
    filename: str,
    bytes_b64: str,
    cajon: str,
    subcajon: str,
    document_name: str,
    importe: float = None
) -> Dict:
    """Upload a document to a specific slot in the Armario Digital.
    
    Workflow:
    1. First call classify_for_armario() to determine cajon/subcajon/document_name
    2. Then call this function with the classification result
    
    The document will be stored in Supabase Storage and linked to the armario_documents table.
    
    Returns:
    - Success: {"success": True, "document_id": "...", "storage_path": "...", "cajon": "...", ...}
    - Error: {"success": False, "error": "..."}
    """
    import base64
    file_bytes = base64.b64decode(bytes_b64)
    return _upload_to_armario(property_id, file_bytes, filename, cajon, subcajon, document_name, importe)


class SeedArmarioInput(BaseModel):
    property_id: str = Field(..., description="UUID of the property to initialize")

@tool("seed_armario")
def seed_armario_tool(property_id: str) -> Dict:
    """Initialize the Armario Digital for an existing property.
    
    Creates all empty document slots (placeholders) for the 6 cajones.
    This is normally done automatically when a property is created.
    
    Use this only for properties that were created before the Armario Digital was implemented.
    
    Returns:
    - Success: {"success": True, "documents_seeded": 62, "message": "..."}
    """
    return _seed_armario(property_id)


class GetArmarioDocumentUrlInput(BaseModel):
    property_id: str = Field(..., description="UUID of the property")
    cajon: str = Field(..., description="Cajón of the document")
    subcajon: str = Field(..., description="Subcajón of the document")
    document_name: str = Field(..., description="Name of the document")

@tool("get_armario_document_url")
def get_armario_document_url_tool(property_id: str, cajon: str, subcajon: str, document_name: str) -> str:
    """Get a signed URL to download a document from the Armario Digital.
    
    The URL is valid for 1 hour.
    
    Returns:
    - Success: Signed URL string
    - Error: None if document not found or not uploaded
    """
    return _get_armario_document_url(property_id, cajon, subcajon, document_name)


class SearchArmarioDocumentsInput(BaseModel):
    property_id: str = Field(..., description="Property UUID")
    search_term: str = Field(..., description="Search term to find documents by name (case insensitive)")

@tool("search_armario_documents")
def search_armario_documents_tool(property_id: str, search_term: str) -> Dict:
    """Search for documents in the Armario Digital by name.
    
    Use this tool when user asks about a specific document or wants to send/download a document.
    The search is case insensitive and matches partial names.
    
    Args:
        property_id: Property UUID
        search_term: Text to search for in document names (e.g., "factura aire", "escritura")
    
    Returns:
        Dict with:
        - ok: bool
        - documents: List of matching documents with id, document_name, cajon, subcajon, is_uploaded, storage_path
        - count: Number of matches
    
    Example: search_armario_documents(property_id='...', search_term='factura aire')
    """
    from tools.supabase_client import sb
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[search_armario_documents] Searching for '{search_term}' in property {property_id}")
        
        # Search documents with partial match (ilike for case-insensitive)
        result = sb.table("armario_documents")\
            .select("id, document_name, cajon, subcajon, is_uploaded, storage_path, original_filename")\
            .eq("property_id", property_id)\
            .ilike("document_name", f"%{search_term}%")\
            .execute()
        
        documents = result.data or []
        
        # If no results by document_name, try original_filename
        if not documents:
            result = sb.table("armario_documents")\
                .select("id, document_name, cajon, subcajon, is_uploaded, storage_path, original_filename")\
                .eq("property_id", property_id)\
                .ilike("original_filename", f"%{search_term}%")\
                .execute()
            documents = result.data or []
        
        logger.info(f"[search_armario_documents] Found {len(documents)} documents matching '{search_term}'")
        
        return {
            "ok": True,
            "documents": documents,
            "count": len(documents)
        }
    except Exception as e:
        logger.error(f"[search_armario_documents] Error: {e}")
        return {"ok": False, "error": str(e), "documents": [], "count": 0}


class SendArmarioDocumentEmailInput(BaseModel):
    property_id: str = Field(..., description="Property UUID")
    document_id: str = Field(..., description="Document ID from armario_documents table")
    to_email: str = Field(..., description="Recipient email address")
    property_name: Optional[str] = Field(default=None, description="Property name for the email subject")

@tool("send_armario_document_email")
def send_armario_document_email_tool(property_id: str, document_id: str, to_email: str, property_name: Optional[str] = None) -> Dict:
    """Send a document from the Armario Digital via email.
    
    IMPORTANT: First use search_armario_documents to find the document_id, then use this tool.
    Only uploaded documents (is_uploaded=true) can be sent.
    
    Args:
        property_id: Property UUID
        document_id: Document ID (get this from search_armario_documents)
        to_email: Recipient's email address
        property_name: Optional property name for the email subject
    
    Returns:
        Dict with ok (bool) and message or error
    
    Example workflow:
    1. User: "manda la factura de aire acondicionado a test@example.com"
    2. Agent: search_armario_documents(property_id='...', search_term='factura aire')
    3. Agent: send_armario_document_email(property_id='...', document_id='uuid-from-search', to_email='test@example.com')
    """
    from tools.supabase_client import sb
    from tools.email_tool import send_email as _send_email_internal
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[send_armario_document_email] Sending document {document_id} to {to_email}")
        
        # Get the document
        doc_result = sb.table("armario_documents")\
            .select("id, document_name, original_filename, storage_path, is_uploaded, property_id")\
            .eq("id", document_id)\
            .eq("property_id", property_id)\
            .single()\
            .execute()
        
        if not doc_result.data:
            return {"ok": False, "error": "Documento no encontrado para esta propiedad"}
        
        doc = doc_result.data
        
        # Check if document is uploaded
        if not doc.get("is_uploaded") or not doc.get("storage_path"):
            return {"ok": False, "error": f"El documento '{doc.get('document_name')}' no está subido todavía. Solo se pueden enviar documentos que ya han sido cargados."}
        
        # Download the document content
        storage_path = doc["storage_path"]
        logger.info(f"[send_armario_document_email] Downloading from storage: {storage_path}")
        
        # Use the correct bucket name (property-docs, not documents)
        from tools.supabase_client import BUCKET
        download_result = sb.storage.from_(BUCKET).download(storage_path)
        
        if not download_result:
            return {"ok": False, "error": "No se pudo descargar el documento del almacenamiento"}
        
        # Determine filename
        filename = doc.get("original_filename") or f"{doc.get('document_name')}.pdf"
        
        # Prepare email
        prop_name = property_name or "Propiedad"
        subject = f"Documento: {doc.get('document_name')} - {prop_name}"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1e40af;">📄 Documento de ABOKA AI</h2>
            <p>Adjunto encontrarás el documento solicitado:</p>
            <ul>
                <li><strong>Documento:</strong> {doc.get('document_name')}</li>
                <li><strong>Propiedad:</strong> {prop_name}</li>
                <li><strong>Archivo:</strong> {filename}</li>
            </ul>
            <hr style="border: 1px solid #e5e7eb; margin: 20px 0;">
            <p style="color: #6b7280; font-size: 12px;">Este email fue enviado automáticamente desde ABOKA AI.</p>
        </div>
        """
        
        # Send email with attachment
        attachments = [(filename, download_result)]
        _send_email_internal(to=[to_email], subject=subject, html=html, attachments=attachments)
        
        logger.info(f"[send_armario_document_email] ✅ Email sent successfully to {to_email}")
        return {"ok": True, "message": f"Documento '{doc.get('document_name')}' enviado a {to_email}"}
        
    except Exception as e:
        logger.error(f"[send_armario_document_email] Error: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


class QueryArmarioDocumentInput(BaseModel):
    property_id: str = Field(..., description="Property UUID")
    search_term: str = Field(..., description="Document name or keywords to search")
    question: str = Field(..., description="Question about the document content")

@tool("query_armario_document")
def query_armario_document_tool(property_id: str, search_term: str, question: str) -> Dict:
    """Ask a question about a document in the Armario Digital.
    
    This tool searches for a document, downloads it, extracts the text, and answers your question.
    
    IMPORTANT: Use this for questions about document CONTENT like:
    - "¿Qué dice la factura del aire acondicionado?"
    - "¿Cuánto es el total de la factura de la cocina?"
    - "¿Qué materiales incluye el presupuesto?"
    
    Args:
        property_id: Property UUID
        search_term: Keywords to find the document (e.g., "factura aire", "presupuesto cocina")
        question: Your question about the document content
    
    Returns:
        Dict with answer and document info
    
    Example:
        query_armario_document(property_id='...', search_term='factura aire', question='¿Cuál es el importe total?')
    """
    from tools.supabase_client import sb, BUCKET
    import logging
    import base64
    import io
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[query_armario_document] Searching for '{search_term}' to answer: '{question}'")
        
        # 1. Search for the document
        result = sb.table("armario_documents")\
            .select("id, document_name, cajon, subcajon, is_uploaded, storage_path, original_filename, content_type, extracted_data")\
            .eq("property_id", property_id)\
            .ilike("document_name", f"%{search_term}%")\
            .execute()
        
        documents = result.data or []
        
        # Try original_filename if no match
        if not documents:
            result = sb.table("armario_documents")\
                .select("id, document_name, cajon, subcajon, is_uploaded, storage_path, original_filename, content_type, extracted_data")\
                .eq("property_id", property_id)\
                .ilike("original_filename", f"%{search_term}%")\
                .execute()
            documents = result.data or []
        
        if not documents:
            return {
                "ok": False, 
                "answer": f"No encontré ningún documento que coincida con '{search_term}' en el Armario Digital.",
                "document_found": False
            }
        
        # Get the first uploaded document
        doc = None
        for d in documents:
            if d.get("is_uploaded") and d.get("storage_path"):
                doc = d
                break
        
        if not doc:
            return {
                "ok": False,
                "answer": f"Encontré '{documents[0].get('document_name')}' pero no está subido todavía. Sube el documento primero.",
                "document_found": True,
                "is_uploaded": False
            }
        
        logger.info(f"[query_armario_document] Found document: {doc.get('document_name')}")
        
        # 2. Check if we already have extracted data with relevant info
        extracted_data = doc.get("extracted_data") or {}
        if extracted_data:
            # Build context from extracted data
            extracted_context = f"""
Datos extraídos del documento '{doc.get('document_name')}':
- Concepto: {extracted_data.get('concepto_detectado', 'No especificado')}
- Valor total: {extracted_data.get('valor_total', 'No especificado')}€
- Proveedor: {extracted_data.get('proveedor', 'No especificado')}
- Número factura: {extracted_data.get('numero_factura', 'No especificado')}
- Fecha documento: {extracted_data.get('fecha_documento', 'No especificada')}
"""
            logger.info(f"[query_armario_document] Using extracted data for answer")
        else:
            extracted_context = ""
        
        # 3. Download and extract text from the document
        storage_path = doc["storage_path"]
        content_type = doc.get("content_type", "application/pdf")
        
        try:
            file_bytes = sb.storage.from_(BUCKET).download(storage_path)
            logger.info(f"[query_armario_document] Downloaded {len(file_bytes)} bytes")
        except Exception as dl_err:
            logger.error(f"[query_armario_document] Download error: {dl_err}")
            # If we have extracted data, use that
            if extracted_context:
                pass  # Continue with extracted data only
            else:
                return {
                    "ok": False,
                    "answer": "No pude descargar el documento para leerlo.",
                    "document_found": True
                }
        
        # 4. Extract text based on content type
        document_text = ""
        if 'file_bytes' in dir() and file_bytes:
            if "pdf" in content_type.lower():
                try:
                    import fitz  # PyMuPDF
                    pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
                    for page in pdf_doc:
                        document_text += page.get_text()
                    pdf_doc.close()
                    logger.info(f"[query_armario_document] Extracted {len(document_text)} chars from PDF")
                except ImportError:
                    logger.warning("[query_armario_document] PyMuPDF not available, using extracted_data only")
                except Exception as pdf_err:
                    logger.warning(f"[query_armario_document] PDF extraction error: {pdf_err}")
        
        # 5. Build context and answer with GPT
        context = ""
        if document_text:
            # Truncate if too long
            max_chars = 8000
            if len(document_text) > max_chars:
                document_text = document_text[:max_chars] + "...[truncado]"
            context = f"Contenido del documento:\n{document_text}\n"
        
        if extracted_context:
            context += extracted_context
        
        if not context:
            return {
                "ok": False,
                "answer": "No pude extraer información del documento. Puede que sea una imagen o un PDF escaneado.",
                "document_found": True
            }
        
        # 6. Use GPT to answer the question
        from openai import OpenAI
        client = OpenAI()
        
        system_prompt = """Eres un asistente que responde preguntas sobre documentos.
Responde de forma clara y concisa basándote SOLO en la información del documento proporcionado.
Si la información no está en el documento, di que no la encuentras.
Responde en español."""
        
        user_prompt = f"""Documento: {doc.get('document_name')}
Ubicación: {doc.get('cajon')}/{doc.get('subcajon', '')}

{context}

Pregunta del usuario: {question}"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        answer = response.choices[0].message.content
        logger.info(f"[query_armario_document] Generated answer: {answer[:100]}...")
        
        return {
            "ok": True,
            "answer": answer,
            "document_name": doc.get("document_name"),
            "document_id": doc.get("id"),
            "cajon": doc.get("cajon"),
            "subcajon": doc.get("subcajon")
        }
        
    except Exception as e:
        logger.error(f"[query_armario_document] Error: {e}", exc_info=True)
        return {"ok": False, "answer": f"Error al consultar el documento: {str(e)}"}


# ═══════════════════════════════════════════════════════════════════════════════


class SetNumberInput(BaseModel):
    property_id: str
    item_key: str
    amount: Optional[float] = Field(None, description="Amount to set. Use None to clear/delete the value.")

@tool("set_number")
def set_number_tool(property_id: str, item_key: str, amount: Optional[float] = None) -> Dict:
    """Set a numeric input in the numbers framework. Use None to clear/delete a value."""
    return _set_number(property_id, item_key, amount)


class ClearNumberInput(BaseModel):
    property_id: str
    item_key: str

@tool("clear_number")
def clear_number_tool(property_id: str, item_key: str) -> Dict:
    """Clear/delete a specific number value in the numbers framework by setting it to None."""
    return _clear_number(property_id, item_key)


class FindItemByValueInput(BaseModel):
    property_id: str
    search_value: Optional[float] = Field(None, description="Value to search for (e.g., 10.0 for '10%')")
    search_label: Optional[str] = Field(None, description="Label text to search for (e.g., 'IVA', 'Precio de venta')")

@tool("find_item_by_value")
def find_item_by_value_tool(property_id: str, search_value: Optional[float] = None, search_label: Optional[str] = None) -> Optional[Dict]:
    """Find an item in the numbers framework by value or label. Useful for commands like 'borra IVA 10%'."""
    return _find_item_by_value(property_id, search_value, search_label)


# DEPRECATED: Old MANINOS numbers table tools - using ABOKA financial_items instead
# class SetNumbersTableCellInput(BaseModel):
#     property_id: str
#     template_key: str = Field(default="R2B", description="Template key (usually 'R2B')")
#     cell_address: str = Field(..., description="Excel cell address like 'B5', 'C10', etc.")
#     value: str = Field(..., description="Value to set in the cell (as string)")

# @tool("set_numbers_table_cell")
# def set_numbers_table_cell_tool(property_id: str, template_key: str, cell_address: str, value: str) -> Dict:
    """Set a cell value in the Numbers Table (R2B template) using Excel cell addresses like 'B5', 'C10', etc.
    
    🔥 CÁLCULO AUTOMÁTICO EN CASCADA:
    - Cuando actualizas una celda amarilla (input del usuario como B5, C5), todas las fórmulas dependientes 
      se calculan AUTOMÁTICAMENTE en cascada.
    - Ejemplo: B5=1000, C5=21 → D5 (=B5*C5/100) se calcula a 210, luego E5 (=B5+D5) se calcula a 1210
    - El resultado incluirá "auto_calculated" con las celdas recalculadas automáticamente.
    
    This is the correct tool to use when working with the Numbers Table Framework.
    Example: set_numbers_table_cell(property_id='...', template_key='R2B', cell_address='B5', value='5000')
    
    Returns:
        Dict with ok=True, cell details, and "auto_calculated" dict with automatically calculated cells
    """
    # return _set_numbers_table_cell(property_id, template_key, cell_address, value)
    return {"ok": False, "error": "DEPRECATED: Use ABOKA financial_items API instead"}


# class ClearNumbersTableCellInput(BaseModel):
#     property_id: str
#     template_key: str = Field(default="R2B", description="Template key (usually 'R2B')")
#     cell_address: str = Field(..., description="Excel cell address like 'B5', 'C10', etc.")

# @tool("clear_numbers_table_cell")
# def clear_numbers_table_cell_tool(property_id: str, template_key: str, cell_address: str) -> Dict:
#     """Clear/delete a cell value in the Numbers Table (R2B template) using Excel cell addresses.
#     This permanently removes the value from the database.
#     Example: clear_numbers_table_cell(property_id='...', template_key='R2B', cell_address='B7')
#     """
#     return _clear_numbers_table_cell(property_id, template_key, cell_address)


# @tool("delete_numbers_template")
# def delete_numbers_template_tool(property_id: str, template_key: str = "R2B") -> Dict:
#     """Delete the entire Numbers template (structure and all values) for a property.
#     
#     Use this when the user wants to:
#     - Remove the Numbers table completely
#     - Start fresh with a new template
#     - Fix issues by re-importing the template
#     
#     This will DELETE ALL data in the Numbers table for this property.
#     
#     Example: delete_numbers_template(property_id='...', template_key='R2B')
#     
#     Returns:
#         Dict with ok=True and counts of deleted records
#     """
#     return {"ok": False, "error": "DEPRECATED: Use ABOKA financial_items API instead"}


# class GetNumbersInput(BaseModel):
#     property_id: str

# @tool("get_numbers")
# def get_numbers_tool(property_id: str) -> List[Dict]:
#     """Return all inputs in numbers framework."""
#     return _get_numbers(property_id)


# class CalcNumbersInput(BaseModel):
#     property_id: str

# @tool("calc_numbers")
# def calc_numbers_tool(property_id: str) -> List[Dict]:
#     """Compute derived metrics using the schema-local calc() function."""
#     return _calc_numbers(property_id)


# --- Numbers Agent derived computation and Excel export ---
class NumbersComputeInput(BaseModel):
    property_id: str
    triggered_by: str = Field("agent")
    trigger_type: str = Field("manual")

@tool("numbers_compute")
def numbers_compute_tool(property_id: str, triggered_by: str = "agent", trigger_type: str = "manual") -> Dict:
    """Compute derived metrics (impuestos_total, costes_totales, net_profit, roi_pct, etc.) and persist calc_outputs + calc_log. NEVER invents numbers; uses current inputs only."""
    return _numbers_compute_and_log(property_id, triggered_by, trigger_type)


class NumbersExcelInput(BaseModel):
    property_id: str

@tool("numbers_excel_export")
def numbers_excel_export_tool(property_id: str) -> Dict:
    """Generate an Excel (.xlsx) for the current numbers framework (Inputs, Derived, Anomalies) and return {filename, bytes_b64}."""
    import base64
    data = _numbers_excel(property_id)
    return {"filename": "numbers_framework.xlsx", "bytes_b64": base64.b64encode(data).decode("utf-8")}


@tool("export_numbers_table")
def export_numbers_table_tool(property_id: str, template_key: str = "R2B") -> Dict:
    """Export the Numbers table as an Excel file with the exact structure (headers, labels, format, values).
    This recreates the original Excel template with all current values from the database.
    Returns {filename, bytes_b64}."""
    import base64
    data = _numbers_table_excel(property_id, template_key)
    return {"filename": f"numbers_table_{template_key}.xlsx", "bytes_b64": base64.b64encode(data).decode("utf-8")}


# --- Scenarios ---
class NumbersWhatIfInput(BaseModel):
    property_id: str
    deltas: Dict[str, float]
    name: Optional[str] = None

@tool("numbers_what_if")
def numbers_what_if_tool(property_id: str, deltas: Dict[str, float], name: Optional[str] = None) -> Dict:
    """Compute a what-if scenario over the current numbers (deltas are fractional: -0.1 means -10%). Persist snapshot and return inputs/outputs/anomalies."""
    return _numbers_what_if(property_id, deltas, name)


class NumbersSensitivityInput(BaseModel):
    property_id: str
    precio_vec: List[float]
    costes_vec: List[float]

@tool("numbers_sensitivity")
def numbers_sensitivity_tool(property_id: str, precio_vec: List[float], costes_vec: List[float]) -> Dict:
    """Compute a 2D sensitivity grid for net_profit over precio_venta and costes_construccion fractional vectors."""
    return _numbers_sensitivity(property_id, precio_vec, costes_vec)


class NumbersBreakEvenInput(BaseModel):
    property_id: str
    tol: Optional[float] = 1.0

@tool("numbers_break_even")
def numbers_break_even_tool(property_id: str, tol: Optional[float] = 1.0) -> Dict:
    """Solve for precio_venta such that net_profit ≈ 0. Returns precio_venta and net_profit."""
    return _numbers_break_even(property_id, tol or 1.0)


# --- Charts ---
class NumbersChartWaterfallInput(BaseModel):
    property_id: str

@tool("numbers_chart_waterfall")
def numbers_chart_waterfall_tool(property_id: str) -> Dict:
    """Generate a waterfall chart (PNG) and return {signed_url}."""
    return _numbers_chart_waterfall(property_id)


class NumbersChartStackInput(BaseModel):
    property_id: str

@tool("numbers_chart_stack")
def numbers_chart_stack_tool(property_id: str) -> Dict:
    """Generate a stacked 100% cost composition chart (PNG) and return {signed_url}."""
    return _numbers_chart_cost_stack(property_id)


class NumbersChartSensitivityInput(BaseModel):
    property_id: str
    precio_vec: List[float]
    costes_vec: List[float]

@tool("numbers_chart_sensitivity")
def numbers_chart_sensitivity_tool(property_id: str, precio_vec: List[float], costes_vec: List[float]) -> Dict:
    """Generate a sensitivity heatmap (PNG) using given vectors; return {signed_url}."""
    return _numbers_chart_sensitivity(property_id, precio_vec, costes_vec)


# ═══════════════════════════════════════════════════════════════════════════════
# ESTUDIO ECONÓMICO TOOLS (ABOKA)
# ═══════════════════════════════════════════════════════════════════════════════

class UpdateEstudioEconomicoInput(BaseModel):
    property_id: str = Field(..., description="UUID of the property")
    concepto: str = Field(..., description="Name of the item to update. Examples: 'Precio Compra Activo', 'ITP', 'Contrata de Obra', 'Precio Venta Vivienda'")
    valor: float = Field(..., description="The numeric value to set (in euros)")
    campo: str = Field(default="estimado", description="Which field to update: 'estimado' (estimation) or 'real' (actual)")

@tool("update_estudio_economico")
def update_estudio_economico_tool(property_id: str, concepto: str, valor: float, campo: str = "estimado") -> Dict:
    """Update a value in the Estudio Económico (financial study) for a property.
    
    Use this tool when the user wants to set or change financial values like:
    - Purchase price: "El precio de compra es 800.000€" → concepto="Precio Compra Activo"
    - ITP tax: "El ITP es 60.000€" → concepto="ITP (Impuesto Transmisiones)"
    - Reform costs: "La reforma costará 100.000€" → concepto="Contrata de Obra"
    - Sale price: "Queremos vender por 1.200.000€" → concepto="Precio Venta Vivienda"
    
    Valid concepts:
    COMPRA: Precio Compra Activo, ITP (Impuesto Transmisiones), Notaría + Registro + Gestoría, IBI Prorrateado, Gestión ABOKA 1%
    REFORMA: Proyecto / Arquitecto, Licencia de Obra / ICIO, Contrata de Obra, Mobiliario Cocina + Electros, etc.
    FINANCIERO: Gastos Constitución Hipoteca, Tasación Oficial, Intereses Soportados, etc.
    GESTIONES: Comunidad de Propietarios, IBI Anual, Suministros, Plusvalía Municipal, Comisión Agencia Venta
    VENTA: Precio Venta Vivienda, Alquileres Temporales
    
    Args:
        property_id: UUID of the property
        concepto: Name of the financial item (must match exactly or closely)
        valor: The value in euros (e.g., 800000 for 800k€)
        campo: 'estimado' for estimated values, 'real' for actual/confirmed values
    
    Returns:
        Dict with ok=True/False and updated data or error message
    """
    try:
        from .supabase_client import sb
        
        # Map campo to database column
        db_field = "estimated_amount" if campo == "estimado" else "real_amount"
        
        # IMPORTANT: Only update items that have item_key defined (seeded items)
        # This ensures we update the correct items that the frontend displays
        
        # First, get all items with item_key for this property
        items_result = sb.table("financial_items")\
            .select("id, item_key, item_name")\
            .eq("property_id", property_id)\
            .not_.is_("item_key", "null")\
            .execute()
        
        if not items_result.data:
            return {"ok": False, "error": "No hay items del estudio económico. Ejecuta la migración SQL primero."}
        
        # Try to find matching item by name (case-insensitive, partial match)
        concepto_lower = concepto.lower()
        matched_item = None
        
        for item in items_result.data:
            item_name_lower = item["item_name"].lower()
            # Exact match
            if item_name_lower == concepto_lower:
                matched_item = item
                break
            # Partial match (concepto contains item_name or vice versa)
            if concepto_lower in item_name_lower or item_name_lower in concepto_lower:
                matched_item = item
        
        if not matched_item:
            # List available concepts for user
            available = [i["item_name"] for i in items_result.data[:10]]
            return {
                "ok": False,
                "error": f"No se encontró '{concepto}'. Conceptos disponibles: {', '.join(available)}..."
            }
        
        # Update the matched item
        update_result = sb.table("financial_items")\
            .update({db_field: valor, "updated_at": "now()"})\
            .eq("id", matched_item["id"])\
            .execute()
        
        if update_result.data:
            return {
                "ok": True,
                "message": f"✅ {matched_item['item_name']} actualizado a {valor:,.0f}€ ({campo})",
                "matched_name": matched_item["item_name"],
                "item_key": matched_item["item_key"],
                "data": update_result.data[0]
            }
        else:
            return {"ok": False, "error": "Error al actualizar. Intenta de nuevo."}
            
    except Exception as e:
        logger.error(f"Error updating estudio económico: {e}")
        return {"ok": False, "error": str(e)}


class GetEstudioEconomicoInput(BaseModel):
    property_id: str = Field(..., description="UUID of the property")

@tool("get_estudio_economico")
def get_estudio_economico_tool(property_id: str) -> Dict:
    """Get the current Estudio Económico (financial study) data for a property.
    
    Returns all financial items grouped by category (COMPRA, REFORMA, FINANCIERO, GESTIONES, VENTA)
    with their estimated and real values.
    
    Use this to:
    - Show the user current values
    - Check what's already filled in
    - Calculate totals and ROI
    """
    try:
        items = _get_aboka_financials(property_id)
        
        if not items:
            return {
                "ok": True,
                "message": "El estudio económico está vacío. Puedes empezar a añadir valores.",
                "items": [],
                "totals": {}
            }
        
        # Group by category
        categories = {}
        for item in items:
            cat = item.get("category", "Otros")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "name": item.get("item_name"),
                "estimado": item.get("estimated_amount", 0),
                "real": item.get("real_amount", 0)
            })
        
        # Calculate totals
        total_gastos_est = sum(item.get("estimated_amount", 0) or 0 for item in items if item.get("category") != "VENTA")
        total_ingresos_est = sum(item.get("estimated_amount", 0) or 0 for item in items if item.get("category") == "VENTA")
        beneficio = total_ingresos_est - total_gastos_est
        roi = (beneficio / total_gastos_est * 100) if total_gastos_est > 0 else 0
        
        return {
            "ok": True,
            "categories": categories,
            "totals": {
                "total_gastos": total_gastos_est,
                "total_ingresos": total_ingresos_est,
                "beneficio_bruto": beneficio,
                "roi_percent": round(roi, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting estudio económico: {e}")
        return {"ok": False, "error": str(e)}


# --- Numbers template selection (session-level) ---
class SetNumbersTemplateInput(BaseModel):
    property_id: str
    template_key: str = Field(..., description="One of: R2B | R2B+PM | R2B+PM+Venta certs | Promocion")

@tool("set_numbers_template")
def set_numbers_template_tool(property_id: str, template_key: str) -> Dict:
    """Set the active Numbers template for this property/session. 
    If the template doesn't exist in the database, it will be automatically imported from Excel.
    This will clear all existing values and start fresh."""
    from .numbers_tools import clear_numbers, initialize_template_structure, get_numbers_table_structure, import_excel_template
    import os
    
    # Check if structure already exists in DB
    structure = get_numbers_table_structure(property_id, template_key)
    
    # If structure exists and has cells, we're done
    if structure and structure.get("cells"):
        logger.info(f"Template {template_key} already exists in DB for property {property_id}")
        # CRÍTICO: NO decir "values_cleared: True" si no borramos nada
        return {"property_id": property_id, "template_key": template_key, "values_cleared": False, "imported": False, "note": "Template already exists, values preserved"}
    
    # Structure doesn't exist - try to import or initialize
    # For R2B template, try to import from Excel file upload (user must upload via UI)
    # For other templates or if import not available, use legacy initialization
    if template_key == "R2B":
        logger.info(f"Template {template_key} not found in DB. User should upload Excel file via UI button.")
        # Don't try Graph API import - user should upload file directly
        # The UI will show upload button and handle import
    else:
        # For non-R2B templates, use legacy initialization
        try:
            logger.info(f"Using legacy initialization for template {template_key}")
            initialize_template_structure(property_id, template_key)
        except Exception as e:
            logger.warning(f"Legacy initialization failed: {e}")
    
    # Clear all existing number values when selecting a new template
    try:
        clear_numbers(property_id)
    except:
        # If clearing fails, continue anyway - template selection is the priority
        pass
    
    return {"property_id": property_id, "template_key": template_key, "values_cleared": True, "imported": structure is None or not structure.get("cells")}


class GetSummarySpecInput(BaseModel):
    property_id: str

@tool("get_summary_spec")
def get_summary_spec_tool(property_id: str) -> List[Dict]:
    """Return the summary spec rows (for the agent to compute later)."""
    return _get_summary_spec(property_id)


class UpsertSummaryValueInput(BaseModel):
    property_id: str
    item_key: str
    amount: float
    provenance: Dict = {}

@tool("upsert_summary_value")
def upsert_summary_value_tool(property_id: str, item_key: str, amount: float, provenance: Dict) -> Dict:
    """Write a summary result value for a given item_key."""
    return _upsert_summary_value(property_id, item_key, amount, provenance)


class SendEmailInput(BaseModel):
    to: List[str]
    subject: str
    html: str
    property_id: Optional[str] = Field(default=None, description="Property ID (required if attaching a document)")
    document_type: Optional[str] = Field(default=None, description="Document type to attach: 'title_status', 'property_listing', or 'property_photos'")

@tool("send_email")
def send_email_tool(to: List[str], subject: str, html: str, property_id: Optional[str] = None, document_type: Optional[str] = None) -> Dict:
    """Send an email with optional document attachment.
    
    Args:
        to: List of email addresses
        subject: Email subject line
        html: HTML email body
        property_id: Optional - Property ID (required if attaching a document)
        document_type: Optional - Document type to attach ('title_status', 'property_listing', 'property_photos')
    
    Example WITHOUT attachment:
        send_email(
            to=["user@example.com"],
            subject="Hello",
            html="<p>This is a test email.</p>"
        )
    
    Example WITH attachment:
        send_email(
            to=["user@example.com"],
            subject="Document: Title Status - Property",
            html="<p>Attached is the title status document you requested.</p>",
            property_id="813036f4-...",
            document_type="title_status"
        )
    
    CRITICAL: If you want to attach a document:
    1. Do NOT call get_document_for_email separately
    2. Just pass property_id and document_type to this function
    3. The backend will automatically fetch and attach the document
    """
    # If document_type is provided, fetch and attach the document
    attachments = None
    if property_id and document_type:
        from tools.docs_tools import get_document_for_email as _get_doc
        doc_result = _get_doc(property_id, document_type=document_type)
        if doc_result.get("success"):
            attachments = [(doc_result["filename"], doc_result["content"])]
    
    return _send_email(to, subject, html, attachments)


class SendNumbersTableEmailInput(BaseModel):
    property_id: str
    template_key: str = Field(default="R2B", description="Template key (usually 'R2B')")
    to: List[str] = Field(..., description="List of email addresses to send to")
    subject: Optional[str] = Field(default=None, description="Email subject (optional, will use default if not provided)")

@tool("send_numbers_table_email")
def send_numbers_table_email_tool(property_id: str, template_key: str, to: List[str], subject: Optional[str] = None) -> Dict:
    """Send the Numbers table Excel file by email.
    Generates the Excel file from the Numbers table and sends it as an attachment.
    Example: send_numbers_table_email(property_id='...', template_key='R2B', to=['user@example.com'], subject='Plantilla R2B')
    """
    import base64
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[send_numbers_table_email] Generating Excel for property_id={property_id}, template_key={template_key}")
        # Generate Excel file using the Numbers Table Framework
        excel_data = _numbers_table_excel(property_id, template_key)
        
        logger.info(f"[send_numbers_table_email] Excel generated successfully, size: {len(excel_data)} bytes")
        
        # Decode base64 if needed (export_numbers_table returns base64)
        # Actually, _numbers_table_excel returns bytes directly, not base64
        excel_bytes = excel_data
        
        # Generate filename
        filename = f"numbers_table_{template_key}.xlsx"
        
        # Default subject if not provided
        if not subject:
            subject = f"Plantilla de Números {template_key}"
        
        # Create HTML email body
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #3d7435;">📊 Plantilla de Números {template_key}</h2>
            <p>Adjunto encontrarás la plantilla de números {template_key} con todos los valores actuales.</p>
            <p>Este archivo Excel contiene la estructura completa de la plantilla y todos los valores guardados.</p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                Este email fue generado automáticamente por RAMA Country Living.
            </p>
        </body>
        </html>
        """
        
        # Send email with attachment
        result = _send_email(to, subject, html, attachments=[(filename, excel_bytes)])
        
        logger.info(f"✅ Numbers table Excel sent to {to}: {filename}")
        return {
            "ok": True,
            "sent": True,
            "to": to,
            "subject": subject,
            "filename": filename,
            "message": f"Plantilla de números {template_key} enviada por email a {', '.join(to)}"
        }
    except Exception as e:
        logger.error(f"Error sending Numbers table email: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e),
            "message": f"Error al enviar la plantilla por email: {str(e)}"
        }


# --- compute_summary tool ---
class ComputeSummaryInput(BaseModel):
    property_id: str
    only_items: Optional[List[str]] = Field(default=None, description="Optional list of item_keys to compute only those")

@tool("compute_summary")
def compute_summary_tool(property_id: str, only_items: Optional[List[str]] = None) -> Dict:
    """Compute summary_values per summary_spec: pulls from documents & numbers, evaluates formulas, upserts results."""
    return _compute_summary(property_id, only_items)


# --- Summary PowerPoint ---
class BuildSummaryPPTInput(BaseModel):
    property_id: str
    property_name: Optional[str] = None
    address: Optional[str] = None

@tool("build_summary_ppt")
def build_summary_ppt_tool(property_id: str, property_name: Optional[str] = None, address: Optional[str] = None, format: str = "pdf") -> Dict:
    """Build a summary presentation (PDF or PPTX) with fixed slides and upload to Supabase Storage. Returns {filename, signed_url} for download. Nunca inventa datos: usa números y docs existentes. Default format: PDF."""
    import base64
    from .supabase_client import sb
    
    data = _build_summary_ppt(property_id, property_name, address, format=format)
    ext = "pdf" if format.lower() == "pdf" else "pptx"
    filename = f"resumen_propiedad_{property_id[:8]}.{ext}"
    
    # Upload to Supabase Storage
    from .supabase_client import BUCKET
    bucket = BUCKET
    storage_key = f"summaries/{property_id}/{filename}"
    content_type = "application/pdf" if ext == "pdf" else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    
    try:
        # Upload with upsert to overwrite if exists
        sb.storage.from_(bucket).upload(storage_key, data, {"content-type": content_type, "upsert": "true"})
        
        # Generate signed URL (24 hours)
        signed = sb.storage.from_(bucket).create_signed_url(storage_key, 86400)
        signed_url = signed.get("signedURL")
        
        return {
            "filename": filename,
            "signed_url": signed_url,
            "storage_key": storage_key,
            "size_bytes": len(data)
        }
    except Exception as e:
        # Fallback: return base64 if storage fails
        return {
            "filename": filename,
            "bytes_b64": base64.b64encode(data).decode("utf-8"),
            "error": f"Storage upload failed: {str(e)}"
        }

# --- Reminders ---
class CreateReminderInput(BaseModel):
    property_id: str = Field(..., description="UUID de la propiedad")
    title: str = Field(..., description="Título del recordatorio (ej: 'Pago a arquitecto')")
    description: str = Field(..., description="Descripción detallada del recordatorio")
    reminder_date: str = Field(..., description="Fecha del recordatorio en formato DD/MM/YYYY o texto natural (ej: 'día 5', '15 de diciembre')")
    recipient_email: Optional[str] = Field(None, description="Email del destinatario (opcional)")
    document_reference: Optional[Dict] = Field(None, description="Referencia al documento relacionado")
    recurrence: Optional[str] = Field(None, description="Tipo de recurrencia: 'monthly' (mensual), 'yearly' (anual), o None para único")
    recurrence_count: Optional[int] = Field(None, description="Número de ocurrencias (default: 12 para monthly, 1 para None)")

@tool("create_reminder")
def create_reminder_tool(property_id: str, title: str, description: str, reminder_date: str, recipient_email: Optional[str] = None, document_reference: Optional[Dict] = None, recurrence: Optional[str] = None, recurrence_count: Optional[int] = None) -> Dict:
    """Crea un recordatorio (o múltiples si es recurrente). Si el usuario dice 'cada mes', usa recurrence='monthly' y recurrence_count=12. Si dice 'cada año', usa recurrence='yearly'. Para recordatorios únicos, deja recurrence=None."""
    return _create_reminder(property_id, title, description, reminder_date, recipient_email, document_reference, recurrence=recurrence, recurrence_count=recurrence_count)

class ExtractPaymentDateInput(BaseModel):
    property_id: str
    document_group: str
    document_subgroup: str
    document_name: str
    payment_concept: str = Field(..., description="Concepto del pago a buscar (ej: 'pago al arquitecto')")

@tool("extract_payment_date")
def extract_payment_date_tool(property_id: str, document_group: str, document_subgroup: str, document_name: str, payment_concept: str) -> Dict:
    """Extrae la fecha de pago de un documento específico usando análisis de contenido."""
    return _extract_payment_date(property_id, document_group, document_subgroup, document_name, payment_concept)

class ListRemindersInput(BaseModel):
    property_id: str
    status: Optional[str] = Field(None, description="Filtrar por estado: pending, sent, cancelled")

@tool("list_reminders")
def list_reminders_tool(property_id: str, status: Optional[str] = None) -> List[Dict]:
    """Lista todos los recordatorios de una propiedad. Muestra título, fecha, y estado."""
    return _list_reminders(property_id, status)

class CancelReminderInput(BaseModel):
    reminder_id: str = Field(..., description="UUID del recordatorio a cancelar")

@tool("cancel_reminder")
def cancel_reminder_tool(reminder_id: str) -> Dict:
    """Cancela un recordatorio existente."""
    return _cancel_reminder(reminder_id)

# --- Google voice tools ---
class TranscribeAudioInput(BaseModel):
    bytes_b64: str
    language_code: Optional[str] = None

@tool("transcribe_audio")
def transcribe_audio_tool(bytes_b64: str, language_code: Optional[str] = None) -> Dict:
    """Speech-to-Text using Google Cloud Speech. Returns {'text': ...}."""
    import base64
    text = _transcribe_google_wav(base64.b64decode(bytes_b64), language_code)
    return {"text": text}

class SynthesizeSpeechInput(BaseModel):
    text: str
    language_code: Optional[str] = None
    voice_name: Optional[str] = None

@tool("synthesize_speech")
def synthesize_speech_tool(text: str, language_code: Optional[str] = None, voice_name: Optional[str] = None) -> Dict:
    """Text-to-Speech using Google Cloud TTS. Returns {'audio_b64_mp3': ...}."""
    import base64
    audio = _tts_google(text, language_code, voice_name)
    return {"audio_b64_mp3": base64.b64encode(audio).decode("utf-8")}

class ProcessVoiceInputInput(BaseModel):
    audio_b64: str
    language_code: Optional[str] = None

@tool("process_voice_input")
def process_voice_input_tool(audio_b64: str, language_code: Optional[str] = None) -> Dict:
    """Process voice input from frontend. Returns structured response with transcribed text."""
    import base64
    audio_data = base64.b64decode(audio_b64)
    return _process_voice_input(audio_data, language_code)

class CreateVoiceResponseInput(BaseModel):
    text: str
    language_code: Optional[str] = None

@tool("create_voice_response")
def create_voice_response_tool(text: str, language_code: Optional[str] = None) -> Dict:
    """Create voice response for given text. Returns both text and audio data."""
    return _create_voice_response(text, language_code)

# --- property query tools ---
class GetPropertyInput(BaseModel):
    property_id: str

@tool("get_property")
def get_property_tool(property_id: str) -> Optional[Dict]:
    """Fetch a property row by UUID."""
    return _get_property(property_id)


class FindPropertyInput(BaseModel):
    name: str
    address: Optional[str] = None

@tool("find_property")
def find_property_tool(name: str, address: Optional[str] = None) -> Optional[Dict]:
    """Find a property by name and optionally address (case-insensitive search)."""
    return _find_property(name, address)


class ListPropertiesInput(BaseModel):
    limit: int = Field(20, ge=1, le=100)

@tool("list_properties")
def list_properties_tool(limit: int = 20) -> List[Dict]:
    """List recent properties for verification and selection."""
    return _list_properties(limit)

class SearchPropertiesInput(BaseModel):
    query: str = Field(..., description="Free text to match name or address (ilike).")
    limit: int = Field(5, ge=1, le=50)

@tool("search_properties")
def search_properties_tool(query: str, limit: int = 5) -> List[Dict]:
    """Search properties by name or address (fuzzy, case-insensitive)."""
    return _search_properties(query, limit)

# --- summarize document (RAG-lite) ---
class SummarizeDocumentInput(BaseModel):
    property_id: str
    document_group: str
    document_subgroup: str = ""
    document_name: str
    model: Optional[str] = None
    max_sentences: int = Field(5, ge=1, le=15)

@tool("summarize_document")
def summarize_document_tool(property_id: str, document_group: str, document_subgroup: str, document_name: str, model: Optional[str] = None, max_sentences: int = 5) -> Dict:
    """Fetches the document via signed URL and returns a short summary. Use when the user asks to summarize a specific document."""
    return _summarize_document(property_id, document_group, document_subgroup, document_name, model, max_sentences)

# --- question-answer on a specific document ---
class QADocumentInput(BaseModel):
    property_id: str
    document_group: str
    document_subgroup: str = ""
    document_name: str
    question: str
    model: Optional[str] = None

@tool("qa_document")
def qa_document_tool(property_id: str, document_group: str, document_subgroup: str, document_name: str, question: str, model: Optional[str] = None) -> Dict:
    """Answer a focused question about a single stored document in Spanish."""
    return _qa_document(property_id, document_group, document_subgroup, document_name, question, model)

# --- payment schedule QA ---
class QAPaymentScheduleInput(BaseModel):
    property_id: str
    document_group: str
    document_subgroup: str = ""
    document_name: str
    today_iso: Optional[str] = None

@tool("qa_payment_schedule")
def qa_payment_schedule_tool(property_id: str, document_group: str, document_subgroup: str, document_name: str, today_iso: Optional[str] = None) -> Dict:
    """Extract payment cadence and compute next due date based on the document text."""
    return _qa_payment_schedule(property_id, document_group, document_subgroup, document_name, today_iso)

# --- RAG indexing + QA with citations ---
class IndexDocumentInput(BaseModel):
    property_id: str
    document_group: str
    document_subgroup: str = ""
    document_name: str

@tool("rag_index_document")
def rag_index_document_tool(property_id: str, document_group: str, document_subgroup: str, document_name: str) -> Dict:
    """Fetches, splits and stores document chunks for retrieval QA."""
    return _index_document(property_id, document_group, document_subgroup, document_name)

class QAWithCitationsInput(BaseModel):
    property_id: str
    query: str
    top_k: int = 5
    document_name: str | None = None
    document_group: str | None = None
    document_subgroup: str | None = None

@tool("rag_qa_with_citations")
def rag_qa_with_citations_tool(property_id: str, query: str, top_k: int = 5, document_name: str | None = None, document_group: str | None = None, document_subgroup: str | None = None) -> Dict:
    """RAG QA over indexed chunks; returns answer and citations. Optionally filter by document_name, document_group, document_subgroup to search only in specific document(s)."""
    return _qa_with_citations(property_id, query, top_k, document_name=document_name, document_group=document_group, document_subgroup=document_subgroup)

class IndexAllDocumentsInput(BaseModel):
    property_id: str

@tool("rag_index_all_documents")
def rag_index_all_documents_tool(property_id: str) -> Dict:
    """Index all documents with file for a property. Use at session start or when results seem incomplete."""
    return _index_all_documents(property_id)

# ==================== MANINOS AI TOOLS ====================

# RAG Tools for MANINOS
@tool("query_documents")
def query_documents_tool(property_id: str, question: str, document_type: str = None) -> Dict:
    """
    🔍 ADVANCED RAG QUERY - Search and answer questions about uploaded documents.
    
    This tool uses state-of-the-art RAG (Retrieval Augmented Generation) with:
    - 🧠 Semantic search (embeddings + vector similarity)
    - 📝 Lexical search (keyword matching with term frequency)
    - 🎯 LLM-based reranking for maximum relevance
    - 📚 Multi-document synthesis (combines info from multiple sources)
    
    ═══════════════════════════════════════════════════════════════════
    WHEN TO USE THIS TOOL:
    ═══════════════════════════════════════════════════════════════════
    
    ✅ USE FOR:
    - Questions about title status: "¿El título está limpio?", "¿Hay gravámenes?"
    - Questions about listing details: "¿Cuál es el precio?", "¿Cuántos dormitorios?"
    - Questions about property condition: "¿Qué defectos hay?", "¿Qué dice el inspector?"
    - Questions about location: "¿Dónde está ubicada?", "¿En qué parque?"
    - Questions about dates: "¿Cuándo fue construida?", "¿Cuándo expira el lease?"
    - Questions about financials: "¿Cuánto es el HOA?", "¿Cuáles son los costos?"
    - General synthesis: "Dame un resumen de la propiedad"
    
    ❌ DO NOT USE FOR:
    - Listing documents: use list_docs instead
    - Uploading documents: that's automatic via UI
    - Info already in database: use get_property instead
    - Calculations: use calculate_maninos_deal, calculate_repair_costs instead
    
    ═══════════════════════════════════════════════════════════════════
    EXAMPLES:
    ═══════════════════════════════════════════════════════════════════
    
    User: "¿Cuál es el estado del título de esta propiedad?"
    Agent: [query_documents(property_id, "¿Cuál es el estado del título?")]
    → Returns: "Clean Blue Title sin gravámenes"
    
    User: "¿Qué defectos importantes mencionan?"
    Agent: [query_documents(property_id, "¿Qué defectos importantes hay?")]
    → Returns: List of defects from photos/inspection docs
    
    User: "Dame toda la información financiera disponible"
    Agent: [query_documents(property_id, "información financiera precio costos HOA")]
    → Returns: Synthesized financial data from multiple documents
    
    ═══════════════════════════════════════════════════════════════════
    PARAMETERS:
    ═══════════════════════════════════════════════════════════════════
    
    property_id (str, required): UUID of the property
    question (str, required): User's question in natural language
        - Can be in Spanish or English
        - Can be a simple question or complex multi-part query
        - Be specific for better results
    
    document_type (str, optional): Filter by document type
        - 'title_status': Search only title documents
        - 'property_listing': Search only listing documents  
        - 'property_photos': Search only photos/inspection docs
        - None (default): Search ALL documents (recommended)
    
    ═══════════════════════════════════════════════════════════════════
    RETURNS:
    ═══════════════════════════════════════════════════════════════════
    
    {
        "answer": str,              # Natural language answer
        "citations": [...],         # Source documents used
        "context_used": bool,       # Whether context was available
        "chunks_searched": int,     # Total chunks considered
        "chunks_used": int,         # Chunks used for answer
        "model_used": str          # LLM model used (gpt-4o or gpt-4o-mini)
    }
    
    ═══════════════════════════════════════════════════════════════════
    PERFORMANCE:
    ═══════════════════════════════════════════════════════════════════
    - Simple queries: ~2-3 seconds (gpt-4o-mini)
    - Complex queries: ~4-6 seconds (gpt-4o + reranking)
    - Handles documents up to 100+ pages
    - Searches 100s of chunks in milliseconds
    
    ACCURACY:
    - 90%+ for factual questions (dates, prices, names)
    - 85%+ for multi-document synthesis
    - Explicit "No information" when data not found
    """
    return _query_documents_maninos(property_id, question, document_type=document_type)

@tool("index_all_documents_maninos")
def index_all_documents_maninos_tool(property_id: str) -> Dict:
    """
    Index (or re-index) all documents for a property to enable RAG queries.
    
    Use this when:
    - User reports that document queries are not working
    - New documents were just uploaded
    - You suspect the index is out of sync
    
    This creates text chunks and embeddings for all uploaded documents,
    storing them in the rag_chunks table for fast semantic search.
    
    Returns:
        {
            "total_chunks": int,
            "documents_indexed": int,
            "total_documents": int,
            "details": [...]
        }
    """
    return _index_all_documents_maninos(property_id)

# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT EXTRACTION TOOLS (ABOKA AI)
# ═══════════════════════════════════════════════════════════════════════════════

@tool("get_pending_extractions")
def get_pending_extractions_tool(property_id: str) -> List[Dict]:
    """
    Get documents with pending extraction approval.
    
    🎯 USE THIS when there are documents uploaded that need user confirmation
    to add their extracted values to the Estudio Económico.
    
    RETURNS:
    List of documents with:
    - document_id: UUID
    - document_name: Name of the document
    - extracted_data: {concepto_detectado, valor_total, proveedor, fecha, ...}
    - mapped_estudio_key: The Estudio Económico key it maps to
    - extraction_confidence: 0.0 - 1.0
    
    FLOW:
    1. Call this tool to check for pending documents
    2. For each document, present the extracted value to user
    3. If user approves, call approve_extraction
    4. If user rejects, call reject_extraction
    """
    return _get_pending_extractions(property_id)


class ApproveExtractionInput(BaseModel):
    document_id: str = Field(..., description="UUID of the document to approve")
    estudio_key: Optional[str] = Field(None, description="Override the mapped estudio key (optional)")


@tool("approve_extraction")
def approve_extraction_tool(document_id: str, estudio_key: Optional[str] = None) -> Dict:
    """
    Approve an extracted value and add it to the Estudio Económico (Real column).
    
    🎯 USE THIS when user confirms the extracted value is correct.
    
    PARAMS:
    - document_id: UUID of the document
    - estudio_key: (optional) Override the auto-mapped key
    
    EXAMPLE:
    User: "Sí, añade la factura del aire al estudio"
    Agent: approve_extraction(document_id="abc-123")
    → Updates Estudio Económico: "Aire Acondicionado" Real = 5000€
    
    RETURNS:
    {"ok": true, "message": "Valor aplicado", "estudio_key": "reforma_ac", "valor": 5000}
    """
    return _approve_extraction(document_id, estudio_key)


class RejectExtractionInput(BaseModel):
    document_id: str = Field(..., description="UUID of the document to reject")


@tool("reject_extraction")
def reject_extraction_tool(document_id: str) -> Dict:
    """
    Reject an extracted value proposal.
    
    🎯 USE THIS when user declines to add the extracted value.
    
    EXAMPLE:
    User: "No, esa factura no es correcta"
    Agent: reject_extraction(document_id="abc-123")
    
    RETURNS:
    {"ok": true, "message": "Extracción rechazada"}
    """
    return _reject_extraction(document_id)


@tool("format_extraction_proposal")
def format_extraction_proposal_tool(document_id: str, property_id: str) -> str:
    """
    Format an extraction proposal for user-friendly display.
    
    🎯 USE THIS to generate a nice message proposing the extracted value.
    
    EXAMPLE OUTPUT:
    "📄 He analizado **factura_clima.pdf**:
    
    • **Concepto**: Aire Acondicionado
    • **Importe**: 5,000€
    • **Proveedor**: Climatización SL
    
    → Se añadiría a: **Aire Acondicionado** (columna Real)
    
    ¿Lo añado al Estudio Económico como gasto **REAL**?"
    """
    # Get the pending extraction for this document
    pending = _get_pending_extractions(property_id)
    for doc in pending:
        if doc.get('document_id') == document_id:
            return _format_extraction_proposal(
                doc.get('extracted_data', {}),
                doc.get('mapped_estudio_key')
            )
    return "No se encontró el documento con extracción pendiente."

# Export the registry
# ============================================================================
# MANINOS AI - Tool Registry (Clean)
# ============================================================================
# All RAMA-specific tools removed (Numbers/Excel, Frameworks, R2B, etc.)
# Kept: Property management, Docs (generic), Voice, Maninos acquisition tools
# ============================================================================

TOOLS = [
    # Property Management (9 tools)
    add_property_tool,
    get_property_tool,
    set_current_property_tool,
    find_property_tool,
    list_properties_tool,
    search_properties_tool,
    delete_property_tool,
    delete_properties_tool,
    update_property_fields_tool,
    
    # Document Management - Generic (8 tools)
    upload_and_link_tool,
    list_docs_tool,
    signed_url_for_tool,
    delete_document_tool,
    summarize_document_tool,
    qa_document_tool,
    rag_index_document_tool,
    rag_qa_with_citations_tool,
    
    # Armario Digital ABOKA (6 tools)
    list_armario_tool,
    get_armario_summary_tool,
    classify_for_armario_tool,
    upload_to_armario_tool,
    seed_armario_tool,
    get_armario_document_url_tool,
    
    # Email
    send_email_tool,
    
    # Voice (4 tools)
    transcribe_audio_tool,
    synthesize_speech_tool,
    process_voice_input_tool,
    create_voice_response_tool,
    
    # RAG & Indexing
    query_documents_tool,  # RAG query for documents
    index_all_documents_maninos_tool,  # Re-index documents
    
    # Document Extraction (ABOKA - 4 tools)
    get_pending_extractions_tool,  # Get documents pending approval
    approve_extraction_tool,  # Approve extracted value → add to Estudio Real
    reject_extraction_tool,  # Reject extracted value
    format_extraction_proposal_tool,  # Format proposal message for user
]
