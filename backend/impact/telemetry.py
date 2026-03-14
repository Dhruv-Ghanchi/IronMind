import time

class ImpactTelemetry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.history = []
            cls._instance.stats = {"total_traversals": 0, "avg_lat": 0}
        return cls._instance
    
    def log_traversal(self, latency, count, depth):
        self.stats["total_traversals"] += 1
        self.history.append({
            "timestamp": time.time(),
            "latency": latency,
            "impact_count": count,
            "depth": depth
        })

telemetry = ImpactTelemetry()
