import logging

logger = logging.getLogger(__name__)

def triage_fatal_error(error_trace: str) -> str:
    """Classifies a fatal error trace into Category A, B, or C."""
    trace_lower = error_trace.lower()
    
    # Category A: Host/Network/Environment
    if any(err in trace_lower for err in [
        "no space left", "connection refused", "name resolution",
        "file not found", "permission denied", "cuda out of memory",
        "out of memory", "oom", "gpu", "disk full", "errno",
        "dns", "network unreachable", "segfault", "killed"
    ]):
        return "Category A (Host/Environment)"
        
    # Category B: Third-Party APIs
    if any(err in trace_lower for err in [
        "401 unauthorized", "503 service unavailable", "api key",
        "ratelimit", "rate limit", "timeout from api", "429",
        "quota exceeded", "forbidden", "502 bad gateway"
    ]):
        return "Category B (Third-Party API)"
        
    # Category C: Internal OS / Hallucination
    return "Category C (Agentic OS Internal Logic)"
