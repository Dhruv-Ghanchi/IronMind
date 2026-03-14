def calculate_risk_score(impacted_nodes):
    """Deterministic severity scoring based on PRD §13."""
    score = len(impacted_nodes)
    explanation = f"Impacts {len(impacted_nodes)} downstream entities."
    
    if score > 7:
        severity = "HIGH"
    elif score > 3:
        severity = "MEDIUM"
    else:
        severity = "LOW"
        
    return {
        "risk_score": min(score, 10),
        "severity": severity,
        "explanation": explanation
    }
