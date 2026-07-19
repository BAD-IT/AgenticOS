import logging

logger = logging.getLogger(__name__)

def triage_fatal_error(error_trace: str) -> str:
    """Classifies a fatal error trace into Category A, B, or C."""
    trace_lower = error_trace.lower()
    
    # Category B: Third-Party APIs
    if any(err in trace_lower for err in ["401 unauthorized", "503 service unavailable", "api key", "ratelimit", "timeout from api"]):
        return "Category B (Third-Party API)"
        
    # Category A: Host/Network/Environment
    if any(err in trace_lower for err in ["no space left", "connection refused", "name resolution", "file not found", "permission denied"]):
        return "Category A (Host/Environment)"
        
    # Category C: Internal OS / Hallucination
    return "Category C (Agentic OS Internal Logic)"
