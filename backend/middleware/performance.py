"""
Performance Monitoring Middleware - Track API performance metrics
"""

import time
from typing import Callable, Dict, Any
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from services.logging_service import logger
from utils.request_metadata import safe_request_route


class PerformanceMetrics:
    """Track performance metrics"""
    
    def __init__(self):
        self.reset()
    
    def record_request(
        self,
        endpoint: str,
        method: str,
        response_time: float,
        status_code: int
    ):
        """Record API request metrics"""
        self.metrics["total_requests"] += 1
        self.metrics["response_times"].append(response_time)
        
        # Track by endpoint
        endpoint_key = f"{method} {endpoint}"
        if endpoint_key not in self.metrics["by_endpoint"]:
            self.metrics["by_endpoint"][endpoint_key] = {
                "count": 0,
                "total_time": 0,
                "min_time": float('inf'),
                "max_time": 0,
                "status_codes": defaultdict(int)
            }
        
        endpoint_metrics = self.metrics["by_endpoint"][endpoint_key]
        endpoint_metrics["count"] += 1
        endpoint_metrics["total_time"] += response_time
        endpoint_metrics["min_time"] = min(endpoint_metrics["min_time"], response_time)
        endpoint_metrics["max_time"] = max(endpoint_metrics["max_time"], response_time)
        endpoint_metrics["status_codes"][status_code] += 1
        
        # Track status codes
        self.metrics["status_codes"][status_code] += 1
        
        # Track slow queries
        if response_time > 1.0:
            self.metrics["slow_queries"].append({
                "endpoint": endpoint_key,
                "response_time": response_time,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        response_times = self.metrics["response_times"]
        
        if not response_times:
            return {
                "total_requests": 0,
                "average_response_time_ms": 0,
                "p95_response_time_ms": 0,
                "p99_response_time_ms": 0
            }
        
        sorted_times = sorted(response_times)
        avg_time = sum(response_times) / len(response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p99_index = int(len(sorted_times) * 0.99)
        
        return {
            "total_requests": self.metrics["total_requests"],
            "average_response_time_ms": round(avg_time * 1000, 2),
            "p95_response_time_ms": round(sorted_times[p95_index] * 1000, 2) if p95_index < len(sorted_times) else 0,
            "p99_response_time_ms": round(sorted_times[p99_index] * 1000, 2) if p99_index < len(sorted_times) else 0,
            "status_codes": dict(self.metrics["status_codes"]),
            "slow_queries_count": len(self.metrics["slow_queries"]),
            "by_endpoint": {
                endpoint: {
                    "count": data["count"],
                    "avg_time_ms": round((data["total_time"] / data["count"]) * 1000, 2),
                    "min_time_ms": round(data["min_time"] * 1000, 2),
                    "max_time_ms": round(data["max_time"] * 1000, 2),
                    "status_codes": dict(data["status_codes"])
                }
                for endpoint, data in self.metrics["by_endpoint"].items()
            }
        }
    
    def reset(self):
        """Reset metrics"""
        self.metrics = {
            "total_requests": 0,
            "response_times": [],
            "status_codes": defaultdict(int),
            "by_endpoint": {},
            "slow_queries": []
        }


# Global metrics instance
performance_metrics = PerformanceMetrics()


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor API performance"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Skip monitoring for health checks and metrics endpoints
        if request.url.path in ["/health", "/metrics", "/api/monitoring/metrics"]:
            return await call_next(request)
        
        try:
            response = await call_next(request)
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Record metrics
            performance_metrics.record_request(
                endpoint=safe_request_route(request),
                method=request.method,
                response_time=response_time,
                status_code=response.status_code
            )
            
            # Log slow queries
            if response_time > 1.0:
                logger.log_performance(
                    metric_name="slow_query",
                    value=response_time * 1000,
                    unit="ms",
                    context={
                        "route": safe_request_route(request),
                        "method": request.method,
                        "status_code": response.status_code
                    }
                )
            
            # Add performance headers
            response.headers["X-Response-Time"] = f"{response_time:.3f}"
            
            # Log API request
            user_id = getattr(request.state, "user_id", None)
            logger.log_api_request(
                endpoint=safe_request_route(request),
                method=request.method,
                user_id=user_id,
                status_code=response.status_code,
                response_time_ms=int(response_time * 1000)
            )
            
            return response
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.log_error(
                error=e,
                context={
                    "route": safe_request_route(request),
                    "method": request.method,
                    "response_time_ms": int(response_time * 1000)
                },
                user_id=getattr(request.state, "user_id", None)
            )
            raise

