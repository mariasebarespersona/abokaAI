"""
PropertyAgent (Aboka AI) - Specialized agent for Renovation Management.

Handles:
- Property management
- Estudio Económico (financial tracking)
- Armario Digital (document management)
- Document extraction and approval
- RAG queries on documents
- Email sending of documents
"""

from typing import List
from .base_agent import BaseAgent
from tools.registry import (
    # Property tools
    set_current_property_tool,
    list_properties_tool,
    delete_property_tool,
    find_property_tool,
    get_property_tool,
    update_property_fields_tool,
    # Estudio Económico (financial)
    update_estudio_economico_tool,
    get_estudio_economico_tool,
    # Armario Digital - Document Management
    search_armario_documents_tool,      # Search docs by name
    send_armario_document_email_tool,   # Send doc by email
    list_armario_tool,                  # List all docs in armario
    get_armario_summary_tool,           # Get completion stats
    query_armario_document_tool,        # RAG - Ask questions about document content
    # Document Extraction (auto-extract values from invoices)
    get_pending_extractions_tool,
    approve_extraction_tool,
    reject_extraction_tool,
    format_extraction_proposal_tool,
)


class PropertyAgent(BaseAgent):
    """Agent specialized in Renovation Management and Flipping."""
    
    def __init__(self):
        super().__init__(name="PropertyAgent", model="gpt-4o-mini", temperature=0.0)
    
    def get_system_prompt(self, intent: str = None, property_name: str = None, context: dict = None) -> str:
        """Get system prompt using modular prompt loader."""
        import sys
        import os
        
        # Add prompts directory to path
        prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
        if prompts_dir not in sys.path:
            sys.path.insert(0, prompts_dir)
        
        from prompt_loader import build_agent_prompt
        
        # Build base prompt from modular system (now points to the cleaned _base.md)
        base_prompt = build_agent_prompt("property_agent", intent)
        
        # Add property context if available
        property_context = ""
        if property_name:
            property_context = f"\n\n## 🎯 PROPIEDAD ACTUAL\n**Nombre**: {property_name}\n"
        else:
            property_context = "\n\n⚠️ No hay propiedad activa seleccionada. Pide al usuario los datos para comenzar.\n"
        
        # NOTE: Removed Flow Validator guidance as it was Maninos specific.
        # Aboka uses a more flexible flow managed by the user.
        
        return base_prompt + property_context
    
    def run(self, user_input: str, property_id: str = None, context: dict = None):
        """
        Override run to handle property operations.
        NOTE: Property creation is NOT allowed here - use the "New Evaluation" button in the UI.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        text_lower = user_input.lower().strip()
        ctx = context or {}
        
        # Check if user is trying to create a property - redirect to UI
        create_keywords = ["crear", "nueva propiedad", "añadir propiedad", "add property", "create property", "anadir propiedad"]
        if any(kw in text_lower for kw in create_keywords):
            logger.info(f"[PropertyAgent] 🚫 User tried to create property via chat - redirecting to UI flow")
            return {
                "action": "complete",
                "agent": self.name,
                "response": "📋 Para añadir una nueva propiedad, usa el botón **'New Evaluation'** en el menú de propiedades (icono ☰ a la izquierda).\n\nEsto iniciará el flujo de creación donde podrás ingresar el nombre y dirección de la propiedad.",
                "tool_calls": [],
                "latency_ms": 0,
                "success": True
            }
        
        # Check if user wants to switch to a property
        if any(phrase in text_lower for phrase in ["trabajar con", "cambiar a", "switch to", "usar", "metete", "meterse", "entra", "entrar", "abre", "abrir", "ve a", "ir a"]):
            logger.info(f"[PropertyAgent] 🎯 Detected property switch request: '{user_input}'")
            
            try:
                # List all properties and search by name
                all_properties = list_properties_tool.invoke({"limit": 50})
                
                # Extract property name from user input
                property_name_search = text_lower
                for phrase in ["trabajar con", "cambiar a", "switch to", "usar", "metete en", "metete", "meterse en", "meterse", "entra en", "entra", "entrar en", "entrar", "abre", "abrir", "ve a", "ir a", "la propiedad", "propiedad"]:
                    property_name_search = property_name_search.replace(phrase, "").strip()
                
                # Find matching property
                matching_prop = None
                for prop in all_properties:
                    if property_name_search in prop.get("name", "").lower():
                        matching_prop = prop
                        break
                
                if matching_prop:
                    prop_id = matching_prop["id"]
                    prop_name = matching_prop["name"]
                    set_result = set_current_property_tool.invoke({"property_id": prop_id})
                    
                    return {
                        "action": "complete",
                        "agent": self.name,
                        "response": f"✅ Ahora estás trabajando con '{prop_name}'.",
                        "tool_calls": [
                            {
                                "name": "set_current_property",
                                "args": {"property_id": prop_id},
                                "result": set_result
                            }
                        ],
                        "property_id": prop_id,
                        "latency_ms": 0,
                        "success": True
                    }
                else:
                    return {
                        "action": "complete",
                        "agent": self.name,
                        "response": f"No encontré ninguna propiedad que coincida con '{user_input}'. ¿Quieres ver la lista de propiedades?",
                        "tool_calls": [],
                        "latency_ms": 0,
                        "success": True
                    }
            except Exception as e:
                logger.error(f"[PropertyAgent] ❌ Error switching property: {e}")
                return {
                    "action": "error",
                    "agent": self.name,
                    "response": f"Error al cambiar de propiedad: {str(e)}",
                    "error": str(e),
                    "latency_ms": 0,
                    "success": False
                }
        
        # Default: use parent's run method
        result = super().run(user_input, property_id, context)
        
        return result
    
    def get_tools(self) -> List:
        """Return ABOKA AI tools for renovation management.
        
        Tools organized by function:
        - Property: get, list, find, delete, update
        - Estudio Económico: get, update (financial tracking)
        - Armario Digital: search, list, summary, send email
        - RAG: query documents
        - Extraction: get pending, approve, reject, format
        """
        return [
            # ═══ PROPERTY MANAGEMENT ═══
            set_current_property_tool,
            list_properties_tool,
            delete_property_tool,
            find_property_tool,
            get_property_tool,
            update_property_fields_tool,
            
            # ═══ ESTUDIO ECONÓMICO (Financial) ═══
            update_estudio_economico_tool,
            get_estudio_economico_tool,
            
            # ═══ ARMARIO DIGITAL (Documents) ═══
            search_armario_documents_tool,      # Search by name → returns document_id
            send_armario_document_email_tool,   # Send doc by email (needs document_id)
            list_armario_tool,                  # List all docs in a cajón
            get_armario_summary_tool,           # Get completion stats per cajón
            query_armario_document_tool,        # RAG - Ask questions about document content
            
            # ═══ DOCUMENT EXTRACTION ═══
            get_pending_extractions_tool,       # Check for values extracted from invoices
            approve_extraction_tool,            # Approve → adds value to Excel (Real)
            reject_extraction_tool,             # Reject extracted value
            format_extraction_proposal_tool,    # Format proposal for display
        ]
