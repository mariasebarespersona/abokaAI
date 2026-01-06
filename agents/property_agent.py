"""
PropertyAgent (Aboka AI) - Specialized agent for Renovation Management.

Handles:
- Property creation and management
- Document management (upload, list, query)
- Financial tracking (Numbers Table)
"""

from typing import List
from .base_agent import BaseAgent
from tools.registry import (
    # Property tools (NOTE: add_property_tool removed - property creation is only through UI flow)
    set_current_property_tool,
    list_properties_tool,
    delete_property_tool,
    find_property_tool,
    get_property_tool,
    update_property_fields_tool,
    # Financial tools - Estudio Económico
    update_estudio_economico_tool,
    get_estudio_economico_tool,
    # Document tools
    upload_and_link_tool,
    list_docs_tool,
    delete_document_tool,
    signed_url_for_tool,
    send_email_tool,
    get_document_for_email_tool,
    # Armario Digital tools (search & email)
    search_armario_documents_tool,
    send_armario_document_email_tool,
    # RAG tools
    query_documents_tool,
    index_all_documents_maninos_tool,
    # Document Extraction tools
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
        """Return all renovation management tools.
        NOTE: add_property_tool is NOT included - property creation only via UI 'New Evaluation' button.
        """
        return [
            # Property management (add_property removed - use UI flow)
            set_current_property_tool,
            list_properties_tool,
            delete_property_tool,
            find_property_tool,
            get_property_tool,
            update_property_fields_tool,
            # Financial tools - Estudio Económico
            update_estudio_economico_tool,
            get_estudio_economico_tool,
            # Documents
            upload_and_link_tool,
            list_docs_tool,
            delete_document_tool,
            signed_url_for_tool,
            send_email_tool,
            get_document_for_email_tool,
            # Armario Digital (search & email)
            search_armario_documents_tool,
            send_armario_document_email_tool,
            # RAG Tools
            query_documents_tool,
            index_all_documents_maninos_tool,
            # Document Extraction (ABOKA)
            get_pending_extractions_tool,
            approve_extraction_tool,
            reject_extraction_tool,
            format_extraction_proposal_tool,
        ]
