#!/usr/bin/env python3
"""
Stress Test Script for Postpartum AI Copilot

Usage:
    python stress_test.py --endpoint /api/chat --concurrent 10 --requests 50
    python stress_test.py --endpoint /health --concurrent 100 --duration 60
"""

import asyncio
import aiohttp
import time
import argparse
import statistics
from typing import List, Dict, Any, Tuple
from datetime import datetime
import json


class StressTestResult:
    """Stress test result container"""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times: List[float] = []
        self.errors: List[Dict[str, Any]] = []
        self.start_time: float = 0
        self.end_time: float = 0
        self.status_codes: Dict[int, int] = {}
    
    def add_result(self, success: bool, response_time: float, status_code: int = None, error: str = None):
        """Add a test result"""
        self.total_requests += 1
        self.response_times.append(response_time)
        
        if success:
            self.successful_requests += 1
            if status_code:
                self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        else:
            self.failed_requests += 1
            if error:
                self.errors.append({
                    "error": error,
                    "status_code": status_code,
                    "timestamp": datetime.now().isoformat()
                })
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate and return statistics"""
        if not self.response_times:
            return {
                "total_requests": 0,
                "message": "No requests completed"
            }
        
        duration = self.end_time - self.start_time if self.end_time > self.start_time else 1
        
        sorted_times = sorted(self.response_times)
        n = len(sorted_times)
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            "duration_seconds": duration,
            "requests_per_second": self.total_requests / duration if duration > 0 else 0,
            "response_times": {
                "mean": statistics.mean(self.response_times),
                "median": sorted_times[n // 2] if n > 0 else 0,
                "p50": sorted_times[int(n * 0.5)] if n > 0 else 0,
                "p95": sorted_times[int(n * 0.95)] if n > 1 else sorted_times[0] if n > 0 else 0,
                "p99": sorted_times[int(n * 0.99)] if n > 1 else sorted_times[0] if n > 0 else 0,
                "min": min(self.response_times),
                "max": max(self.response_times),
                "stdev": statistics.stdev(self.response_times) if len(self.response_times) > 1 else 0
            },
            "status_codes": self.status_codes,
            "error_count": len(self.errors),
            "errors": self.errors[:10]  # Show first 10 errors
        }


async def make_request(
    session: aiohttp.ClientSession,
    url: str,
    method: str = "GET",
    data: Dict[str, Any] = None,
    headers: Dict[str, str] = None
) -> Tuple[bool, float, int, str]:
    """Make a single HTTP request"""
    start_time = time.time()
    success = False
    status_code = None
    error = None
    
    try:
        if method == "GET":
            async with session.get(url, headers=headers) as response:
                status_code = response.status
                await response.text()  # Read response
                success = status_code < 400
        elif method == "POST":
            async with session.post(url, json=data, headers=headers) as response:
                status_code = response.status
                await response.text()  # Read response
                success = status_code < 400
        else:
            error = f"Unsupported method: {method}"
    except asyncio.TimeoutError:
        error = "Request timeout"
    except aiohttp.ClientError as e:
        error = f"Client error: {str(e)}"
    except Exception as e:
        error = f"Unexpected error: {str(e)}"
    
    response_time = time.time() - start_time
    return success, response_time, status_code, error


async def worker(
    session: aiohttp.ClientSession,
    url: str,
    method: str,
    data: Dict[str, Any],
    headers: Dict[str, str],
    num_requests: int,
    result: StressTestResult
):
    """Worker coroutine that makes multiple requests"""
    for _ in range(num_requests):
        success, response_time, status_code, error = await make_request(
            session, url, method, data, headers
        )
        result.add_result(success, response_time, status_code, error)


async def run_stress_test(
    base_url: str,
    endpoint: str,
    concurrent_users: int,
    requests_per_user: int = None,
    duration: int = None,
    method: str = "GET",
    data: Dict[str, Any] = None,
    headers: Dict[str, str] = None
) -> StressTestResult:
    """Run stress test"""
    result = StressTestResult()
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    # Determine number of requests
    if duration:
        # Time-based test
        requests_per_user = requests_per_user or 1000  # High number for time-based
    else:
        # Request-based test
        requests_per_user = requests_per_user or 50
        duration = None
    
    print(f"\n{'='*60}")
    print(f"Stress Test Configuration")
    print(f"{'='*60}")
    print(f"Endpoint: {url}")
    print(f"Method: {method}")
    print(f"Concurrent Users: {concurrent_users}")
    if duration:
        print(f"Duration: {duration} seconds")
    else:
        print(f"Requests per User: {requests_per_user}")
    print(f"{'='*60}\n")
    
    result.start_time = time.time()
    
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30)
    ) as session:
        if duration:
            # Time-based test
            end_time = time.time() + duration
            tasks = []
            
            async def time_based_worker():
                while time.time() < end_time:
                    success, response_time, status_code, error = await make_request(
                        session, url, method, data, headers
                    )
                    result.add_result(success, response_time, status_code, error)
            
            # Create concurrent workers
            for _ in range(concurrent_users):
                tasks.append(asyncio.create_task(time_based_worker()))
            
            await asyncio.gather(*tasks)
        else:
            # Request-based test
            tasks = []
            for _ in range(concurrent_users):
                task = asyncio.create_task(
                    worker(session, url, method, data, headers, requests_per_user, result)
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks)
    
    result.end_time = time.time()
    return result


def print_results(result: StressTestResult):
    """Print test results in a formatted way"""
    stats = result.get_statistics()
    
    print(f"\n{'='*60}")
    print(f"Stress Test Results")
    print(f"{'='*60}")
    print(f"Total Requests: {stats['total_requests']}")
    print(f"Successful: {stats['successful_requests']} ({stats['success_rate']:.2f}%)")
    print(f"Failed: {stats['failed_requests']}")
    print(f"Duration: {stats['duration_seconds']:.2f} seconds")
    print(f"Requests per Second: {stats['requests_per_second']:.2f} RPS")
    
    if 'response_times' in stats:
        rt = stats['response_times']
        print(f"\nResponse Times (seconds):")
        print(f"  Mean:   {rt['mean']:.3f}s")
        print(f"  Median: {rt['median']:.3f}s")
        print(f"  P50:    {rt['p50']:.3f}s")
        print(f"  P95:    {rt['p95']:.3f}s")
        print(f"  P99:    {rt['p99']:.3f}s")
        print(f"  Min:    {rt['min']:.3f}s")
        print(f"  Max:    {rt['max']:.3f}s")
        print(f"  StdDev: {rt['stdev']:.3f}s")
    
    if stats.get('status_codes'):
        print(f"\nStatus Code Distribution:")
        for code, count in sorted(stats['status_codes'].items()):
            percentage = (count / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0
            print(f"  {code}: {count} ({percentage:.2f}%)")
    
    if stats.get('errors'):
        print(f"\nErrors (showing first {len(stats['errors'])}):")
        for error in stats['errors']:
            print(f"  - {error.get('error', 'Unknown error')} (Status: {error.get('status_code', 'N/A')})")
    
    print(f"{'='*60}\n")
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"stress_test_results_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"Results saved to: {filename}")


def get_test_data(endpoint: str) -> Dict[str, Any]:
    """Get test data based on endpoint"""
    if "/chat" in endpoint:
        return {
            "query": "My baby is crying, what should I do?",
            "user_id": "stress_test_user",
            "language": "en"
        }
    elif "/tracking" in endpoint:
        return {
            "user_id": "stress_test_user",
            "entry_type": "feeding",
            "timestamp": datetime.now().isoformat(),
            "feeding_type": "breast",
            "duration_minutes": 15
        }
    elif "/emotional-checkin" in endpoint:
        return {
            "user_id": "stress_test_user",
            "mood_level": 5,
            "mood_notes": "Feeling okay"
        }
    elif "/crisis" in endpoint:
        return {
            "user_id": "stress_test_user",
            "query": "I need help"
        }
    else:
        return {}


def main():
    parser = argparse.ArgumentParser(description="Stress test for Postpartum AI Copilot API")
    parser.add_argument("--endpoint", default="/health", help="API endpoint to test")
    parser.add_argument("--concurrent", type=int, default=10, help="Number of concurrent users")
    parser.add_argument("--requests", type=int, default=None, help="Number of requests per user")
    parser.add_argument("--duration", type=int, default=None, help="Test duration in seconds")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--method", default="GET", choices=["GET", "POST"], help="HTTP method")
    parser.add_argument("--token", default=None, help="JWT token for authenticated requests")
    
    args = parser.parse_args()
    
    # Determine method based on endpoint
    if args.endpoint in ["/health", "/api/monitoring/health"]:
        method = "GET"
        data = None
    else:
        method = args.method if args.method == "POST" else "POST"
        data = get_test_data(args.endpoint)
    
    # Set headers
    headers = {"Content-Type": "application/json"}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"
    
    # Run stress test
    result = asyncio.run(run_stress_test(
        base_url=args.base_url,
        endpoint=args.endpoint,
        concurrent_users=args.concurrent,
        requests_per_user=args.requests,
        duration=args.duration,
        method=method,
        data=data,
        headers=headers
    ))
    
    # Print results
    print_results(result)


if __name__ == "__main__":
    main()

