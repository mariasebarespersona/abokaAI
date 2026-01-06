"""
OrchestrationRouter - Manages agent routing for Aboka AI.

Handles:
- Initial routing based on intent (General Chat vs Property Mode)
- Simple routing to PropertyAgent when property is selected
- Loop prevention (max 3 redirects)
"""

import logging
import time
from typing import Dict, Any, Optional
from router.active_router import ActiveRouter
# Metrics removed - using Logfire instead
def log_event(*args, **kwargs): pass  # No-op for now
from agents.property_agent import PropertyAgent

logger = logging.getLogger("orchestrator")


class OrchestrationRouter:
    """
    Orchestrates agent routing for Aboka AI.
    """
    
    def __init__(self):
        """Initialize orchestration router."""
        self.active_router = ActiveRouter()
        self.max_redirects = 3
        
        # Initialize specialized agents
        # SIMPLIFIED: Only PropertyAgent (handles acquisition flow including documents)
        self.property_agent = PropertyAgent()
        
        # Agent registry
        self.agents = {
            "PropertyAgent": self.property_agent
        }
        
        logger.info(f"[orchestrator] Initialized with {len(self.agents)} specialized agent (PropertyAgent), max_redirects=3")
    
    async def route_and_execute(
        self,
        user_input: str,
        session_id: str,
        property_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        use_main_agent: bool = False,
        direct_execution: bool = False,  # NEW: Enable Phase 2b direct execution
        force_agent: Optional[str] = None  # NEW: Force a specific agent (e.g., "DocsAgent")
    ) -> Dict[str, Any]:
        """
        Route user input to appropriate agent and handle redirects.
        
        Args:
            user_input: User's message
            session_id: Session ID for tracking
            property_id: Current property ID
            context: Additional context
            use_main_agent: If True, skip routing and use MainAgent directly
            direct_execution: If True, agents execute directly (Phase 2b)
            force_agent: If set, skip routing and use this agent directly
        
        Returns:
            Dict with response, agent_path, redirects, and metadata
        """
        start_time = time.time()
        redirect_count = 0
        agent_path = []  # Track which agents were used
        current_input = user_input
        
        try:
            # Prepare context
            full_context = context or {}
            full_context["session_id"] = session_id
            full_context["property_id"] = property_id
            
            # Add property_name if available
            if property_id:
                try:
                    from tools.property_tools import get_property
                    prop_info = get_property(property_id)
                    if prop_info:
                        full_context["property_name"] = prop_info.get("name")
                        full_context["acquisition_stage"] = prop_info.get("acquisition_stage")
                        logger.info(f"[orchestrator] Working with property: {full_context['property_name']} ({property_id}), stage={full_context['acquisition_stage']}")
                except Exception as e:
                    logger.warning(f"[orchestrator] Could not get property info: {e}")
            
            # Load conversation history from LangGraph checkpointer if available
            if session_id:
                try:
                    from agentic import agent as langgraph_agent
                    from langchain_core.messages import HumanMessage, AIMessage
                    
                    config = {"configurable": {"thread_id": session_id}}
                    state = langgraph_agent.get_state(config)
                    
                    if state and state.values.get("messages"):
                        messages = state.values["messages"][-25:]
                        history = [m for m in messages if isinstance(m, (HumanMessage, AIMessage))]
                        full_context["history"] = history
                        logger.info(f"[orchestrator] Loaded {len(history)} messages from checkpointer")
                except Exception as e:
                    logger.warning(f"[orchestrator] Could not load history from checkpointer: {e}")
            
            # If use_main_agent is True, skip routing entirely
            if use_main_agent:
                logger.info(f"[orchestrator] Using MainAgent directly (skip routing)")
                return {
                    "status": "use_main_agent",
                    "agent_path": ["MainAgent"],
                    "redirects": 0,
                    "total_latency_ms": int((time.time() - start_time) * 1000)
                }
            
            # Routing Logic
            routing = None
            current_agent_name = None

            # If force_agent is set, use it
            if force_agent:
                logger.info(f"[orchestrator] Using {force_agent} directly (force_agent)")
                current_agent_name = force_agent
                agent_path.append(current_agent_name)
            
            # SIMPLE ROUTER: If property_id exists, default to PropertyAgent.
            # Otherwise use ActiveRouter to detect if user wants to enter property mode or do something else.
            elif property_id:
                 # In Property Mode -> PropertyAgent
                current_agent_name = "PropertyAgent"
                routing = {
                    "intent": "property_management",
                    "confidence": 1.0,
                    "target_agent": "PropertyAgent",
                    "reason": "Active property context"
                }
                agent_path.append(current_agent_name)
                logger.info(f"[orchestrator] 🏘️ Property ID present -> Routing to PropertyAgent")
            else:
                # No property selected -> Use ActiveRouter
                routing = await self.active_router.decide(current_input, full_context)
                current_agent_name = routing["target_agent"]
                agent_path.append(current_agent_name)
                logger.info(f"[orchestrator] 🔍 Active router -> {current_agent_name} (intent={routing['intent']})")

            
            # === DIRECT EXECUTION ===
            if direct_execution and current_agent_name in self.agents:
                logger.info(f"[orchestrator] 🚀 Starting direct execution with {current_agent_name}")
                
                # Add intent to context
                if routing and routing.get("intent"):
                    full_context["intent"] = routing["intent"]
                
                # Execution loop with redirects
                while redirect_count < self.max_redirects:
                    agent = self.agents[current_agent_name]
                    
                    logger.info(f"[orchestrator] Executing {current_agent_name} (redirect #{redirect_count})")
                    
                    # Execute agent
                    result = agent.run(
                        user_input=current_input,
                        property_id=property_id,
                        context=full_context
                    )
                    
                    action = result.get("action")
                    logger.info(f"[orchestrator] {current_agent_name} returned action={action}")
                    
                    if action == "complete":
                        # Success
                        orchestrator_result = {
                            "status": "completed",
                            "response": result.get("response"),
                            "agent_path": agent_path,
                            "redirects": redirect_count,
                            "final_agent": current_agent_name,
                            "tool_calls": result.get("tool_calls", []),
                            "total_latency_ms": int((time.time() - start_time) * 1000)
                        }
                        
                        if "property_id" in result:
                            orchestrator_result["property_id"] = result["property_id"]
                        
                        return orchestrator_result
                    
                    elif action == "redirect":
                        to_agent = result.get("to_agent")
                        reason = result.get("reason", "unknown")
                        
                        logger.info(f"[orchestrator] 🔄 Redirecting to {to_agent}")
                        
                        if to_agent not in self.agents and to_agent != "MainAgent":
                            to_agent = "MainAgent"
                        
                        current_agent_name = to_agent
                        agent_path.append(to_agent)
                        redirect_count += 1
                        
                        if to_agent == "MainAgent":
                            break
                    
                    elif action == "escalate":
                        logger.info(f"[orchestrator] ⬆️ Escalating to MainAgent")
                        agent_path.append("MainAgent")
                        break
                    
                    elif action == "error":
                        error = result.get("error", "unknown")
                        logger.error(f"[orchestrator] ❌ Error: {error}")
                        full_context["original_intent"] = routing.get("intent") if routing else None
                        agent_path.append("MainAgent")
                        break
                    
                    else:
                        logger.warning(f"[orchestrator] ⚠️ Unknown action {action}")
                        agent_path.append("MainAgent")
                        break
                
                if redirect_count >= self.max_redirects:
                     agent_path.append("MainAgent")

                return {
                    "status": "use_main_agent",
                    "agent_path": agent_path,
                    "redirects": redirect_count,
                    "total_latency_ms": int((time.time() - start_time) * 1000),
                    "reason": "fallback_or_redirect"
                }
            
            # Routing only (no execution)
            else:
                return {
                    "status": "routed",
                    "intent": routing["intent"] if routing else "unknown",
                    "target_agent": current_agent_name,
                    "agent_path": agent_path,
                    "total_latency_ms": int((time.time() - start_time) * 1000)
                }
        
        except Exception as e:
            logger.error(f"[orchestrator] Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "agent_path": agent_path or ["MainAgent"],
                "total_latency_ms": int((time.time() - start_time) * 1000)
            }


# Global orchestrator instance
orchestrator = OrchestrationRouter()
