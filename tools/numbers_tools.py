from __future__ import annotations
from typing import Dict, List, Optional
from .supabase_client import sb
import logging

logger = logging.getLogger(__name__)

# ==================== ABOKA AI FINANCIAL ENGINE ====================

DEFAULT_TEMPLATE_ITEMS = [
    # COMPRA
    {"category": "Compra", "item_name": "Precio Compra", "estimated_amount": 0},
    {"category": "Compra", "item_name": "Impuestos (ITP)", "estimated_amount": 0},
    {"category": "Compra", "item_name": "Notaría y Registro", "estimated_amount": 0},
    {"category": "Compra", "item_name": "Honorarios Agencia", "estimated_amount": 0},
    
    # REFORMA
    {"category": "Reforma", "item_name": "Licencia Obras", "estimated_amount": 0},
    {"category": "Reforma", "item_name": "Demoliciones", "estimated_amount": 0},
    {"category": "Reforma", "item_name": "Albañilería", "estimated_amount": 0},
    {"category": "Reforma", "item_name": "Fontanería", "estimated_amount": 0},
    {"category": "Reforma", "item_name": "Electricidad", "estimated_amount": 0},
    {"category": "Reforma", "item_name": "Cocina", "estimated_amount": 0},
    {"category": "Reforma", "item_name": "Baños", "estimated_amount": 0},
    {"category": "Reforma", "item_name": "Suelos / Pintura", "estimated_amount": 0},
    {"category": "Reforma", "item_name": "Carpintería (Puertas/Ventanas)", "estimated_amount": 0},
    
    # GASTOS
    {"category": "Gastos", "item_name": "Comunidad (durante obra)", "estimated_amount": 0},
    {"category": "Gastos", "item_name": "IBI", "estimated_amount": 0},
    {"category": "Gastos", "item_name": "Suministros (Luz/Agua)", "estimated_amount": 0},
    {"category": "Gastos", "item_name": "Seguro", "estimated_amount": 0},
    
    # VENTA
    {"category": "Venta", "item_name": "Precio Venta Esperado", "estimated_amount": 0},
    {"category": "Venta", "item_name": "Plusvalía Municipal", "estimated_amount": 0},
    {"category": "Venta", "item_name": "Honorarios Venta", "estimated_amount": 0},
]

def init_financial_template(property_id: str) -> List[Dict]:
    """
    Initializes the financial_items table with default rows if empty.
    Returns the list of items.
    """
    try:
        # Check if items exist
        existing = sb.table("financial_items").select("id").eq("property_id", property_id).execute()
        
        if not existing.data:
            logger.info(f"Initializing financial items for property {property_id}")
            # Prepare batch insert
            rows_to_insert = []
            for item in DEFAULT_TEMPLATE_ITEMS:
                rows_to_insert.append({
                    "property_id": property_id,
                    "category": item["category"],
                    "item_name": item["item_name"],
                    "estimated_amount": item["estimated_amount"],
                    "real_amount": 0
                })
            
            sb.table("financial_items").insert(rows_to_insert).execute()
            
        return get_aboka_financials(property_id)
        
    except Exception as e:
        logger.error(f"Error initializing financial template: {e}")
        return []

def get_aboka_financials(property_id: str) -> List[Dict]:
    """
    Fetch all financial items for a property.
    Calls init_financial_template first to ensure data exists.
    """
    try:
        # First ensure we have data
        # Check count to avoid recursion loop if init fails
        count = sb.table("financial_items").select("id", count="exact").eq("property_id", property_id).execute()
        if count.count == 0:
            return init_financial_template(property_id)
            
        # Fetch data sorted by category (custom sort order handled in frontend or basic alphabetical)
        # We'll just return raw rows, frontend groups them.
        result = sb.table("financial_items").select("*").eq("property_id", property_id).execute()
        return result.data or []
        
    except Exception as e:
        logger.error(f"Error fetching financials: {e}")
        return []

def update_financial_item(item_id: str, updates: Dict) -> Dict:
    """
    Update a single financial item (e.g. estimate or real amount).
    """
    try:
        result = sb.table("financial_items").update(updates).eq("id", item_id).execute()
        if result.data:
            return {"ok": True, "data": result.data[0]}
        return {"ok": False, "error": "Item not found"}
    except Exception as e:
        logger.error(f"Error updating financial item {item_id}: {e}")
        return {"ok": False, "error": str(e)}

def update_financial_by_name(property_id: str, item_name: str, updates: Dict) -> Dict:
    """
    Update item by name (useful for LLM interaction or fuzzy matching).
    """
    try:
        # Try exact match first
        result = sb.table("financial_items").update(updates)\
            .eq("property_id", property_id)\
            .eq("item_name", item_name)\
            .execute()
            
        if result.data:
            return {"ok": True, "data": result.data[0]}
            
        return {"ok": False, "error": f"Item '{item_name}' not found"}
    except Exception as e:
        logger.error(f"Error updating financial item {item_name}: {e}")
        return {"ok": False, "error": str(e)}
