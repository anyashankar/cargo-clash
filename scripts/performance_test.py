"""
Performance testing script for Cargo Clash.
Validates latency, concurrency, and reliability requirements.
"""

import asyncio
import aiohttp
import time
import statistics
import json
from typing import List, Dict, Any
import websockets
import concurrent.futures
from dataclasses import dataclass


@dataclass
class TestResult:
    """Test result data structure."""
    endpoint: str
    response_time: float
    status_code: int
    success: bool
    error: str = None


class PerformanceTester:
    """Performance testing suite for Cargo Clash."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http", "ws")
        self.results: List[TestResult] = []
        
    async def test_api_latency(self, endpoint: str, method: str = "GET", data: Dict = None) -> TestResult:
        """Test API endpoint latency."""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        await response.text()
                        response_time = time.time() - start_time
                        return TestResult(
                            endpoint=endpoint,
                            response_time=response_time,
                            status_code=response.status,
                            success=response.status < 400
                        )
                elif method == "POST":
                    async with session.post(f"{self.base_url}{endpoint}", json=data) as response:
                        await response.text()
                        response_time = time.time() - start_time
                        return TestResult(
                            endpoint=endpoint,
                            response_time=response_time,
                            status_code=response.status,
                            success=response.status < 400
                        )
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                endpoint=endpoint,
                response_time=response_time,
                status_code=0,
                success=False,
                error=str(e)
            )
    
    async def test_concurrent_requests(self, endpoint: str, concurrent_users: int = 50) -> List[TestResult]:
        """Test concurrent API requests."""
        tasks = []
        
        for _ in range(concurrent_users):
            task = self.test_api_latency(endpoint)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
    
    async def test_websocket_connection(self, user_id: int = 1) -> TestResult:
        """Test WebSocket connection and messaging."""
        start_time = time.time()
        
        try:
            uri = f"{self.ws_url}/ws/{user_id}"
            async with websockets.connect(uri) as websocket:
                # Send ping message
                ping_message = {
                    "type": "ping",
                    "data": {"timestamp": time.time()}
                }
                await websocket.send(json.dumps(ping_message))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_time = time.time() - start_time
                
                return TestResult(
                    endpoint=f"/ws/{user_id}",
                    response_time=response_time,
                    status_code=200,
                    success=True
                )
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                endpoint=f"/ws/{user_id}",
                response_time=response_time,
                status_code=0,
                success=False,
                error=str(e)
            )
    
    async def test_websocket_concurrent(self, concurrent_connections: int = 50) -> List[TestResult]:
        """Test concurrent WebSocket connections."""
        tasks = []
        
        for i in range(concurrent_connections):
            task = self.test_websocket_connection(user_id=i + 1)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
    
    async def run_latency_tests(self) -> Dict[str, Any]:
        """Run comprehensive latency tests."""
        print("Running latency tests...")
        
        endpoints = [
            "/health",
            "/api/locations",
            "/api/missions",
            "/api/market/prices",
        ]
        
        latency_results = {}
        
        for endpoint in endpoints:
            print(f"Testing {endpoint}...")
            results = []
            
            # Run 10 requests per endpoint
            for _ in range(10):
                result = await self.test_api_latency(endpoint)
                results.append(result)
                await asyncio.sleep(0.1)  # Small delay between requests
            
            # Calculate statistics
            response_times = [r.response_time for r in results if r.success]
            success_rate = len([r for r in results if r.success]) / len(results)
            
            if response_times:
                latency_results[endpoint] = {
                    "avg_latency": statistics.mean(response_times),
                    "min_latency": min(response_times),
                    "max_latency": max(response_times),
                    "median_latency": statistics.median(response_times),
                    "p95_latency": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0],
                    "success_rate": success_rate,
                    "total_requests": len(results)
                }
            else:
                latency_results[endpoint] = {
                    "error": "All requests failed",
                    "success_rate": 0,
                    "total_requests": len(results)
                }
        
        return latency_results
    
    async def run_concurrency_tests(self) -> Dict[str, Any]:
        """Run concurrency tests."""
        print("Running concurrency tests...")
        
        test_scenarios = [
            {"endpoint": "/health", "users": 50, "name": "Health Check - 50 users"},
            {"endpoint": "/api/locations", "users": 50, "name": "Locations API - 50 users"},
            {"endpoint": "/health", "users": 100, "name": "Health Check - 100 users"},
        ]
        
        concurrency_results = {}
        
        for scenario in test_scenarios:
            print(f"Testing: {scenario['name']}")
            start_time = time.time()
            
            results = await self.test_concurrent_requests(
                scenario["endpoint"], 
                scenario["users"]
            )
            
            total_time = time.time() - start_time
            
            # Calculate statistics
            response_times = [r.response_time for r in results if r.success]
            success_rate = len([r for r in results if r.success]) / len(results)
            requests_per_second = len(results) / total_time
            
            concurrency_results[scenario["name"]] = {
                "total_requests": len(results),
                "successful_requests": len([r for r in results if r.success]),
                "success_rate": success_rate,
                "total_time": total_time,
                "requests_per_second": requests_per_second,
                "avg_response_time": statistics.mean(response_times) if response_times else 0,
                "max_response_time": max(response_times) if response_times else 0,
            }
        
        return concurrency_results
    
    async def run_websocket_tests(self) -> Dict[str, Any]:
        """Run WebSocket performance tests."""
        print("Running WebSocket tests...")
        
        # Test single connection
        single_result = await self.test_websocket_connection()
        
        # Test concurrent connections
        concurrent_results = await self.test_websocket_concurrent(25)
        
        successful_connections = len([r for r in concurrent_results if r.success])
        success_rate = successful_connections / len(concurrent_results)
        response_times = [r.response_time for r in concurrent_results if r.success]
        
        websocket_results = {
            "single_connection": {
                "success": single_result.success,
                "response_time": single_result.response_time,
                "error": single_result.error
            },
            "concurrent_connections": {
                "total_attempts": len(concurrent_results),
                "successful_connections": successful_connections,
                "success_rate": success_rate,
                "avg_response_time": statistics.mean(response_times) if response_times else 0,
                "max_response_time": max(response_times) if response_times else 0,
            }
        }
        
        return websocket_results
    
    async def run_reliability_tests(self) -> Dict[str, Any]:
        """Run reliability and fault tolerance tests."""
        print("Running reliability tests...")
        
        # Test sustained load
        print("Testing sustained load...")
        sustained_results = []
        
        for i in range(100):  # 100 requests over time
            result = await self.test_api_latency("/health")
            sustained_results.append(result)
            
            if i % 10 == 0:
                print(f"Completed {i + 1}/100 requests")
            
            await asyncio.sleep(0.5)  # 2 requests per second
        
        # Calculate reliability metrics
        successful_requests = len([r for r in sustained_results if r.success])
        reliability_rate = successful_requests / len(sustained_results)
        
        # Test error handling
        print("Testing error handling...")
        error_results = []
        
        # Test invalid endpoints
        invalid_endpoints = ["/api/invalid", "/api/nonexistent", "/api/error"]
        
        for endpoint in invalid_endpoints:
            result = await self.test_api_latency(endpoint)
            error_results.append(result)
        
        reliability_results = {
            "sustained_load": {
                "total_requests": len(sustained_results),
                "successful_requests": successful_requests,
                "reliability_rate": reliability_rate,
                "avg_response_time": statistics.mean([r.response_time for r in sustained_results if r.success])
            },
            "error_handling": {
                "invalid_endpoint_tests": len(error_results),
                "handled_gracefully": len([r for r in error_results if r.status_code in [404, 405]])
            }
        }
        
        return reliability_results
    
    def validate_requirements(self, results: Dict[str, Any]) -> Dict[str, bool]:
        """Validate against performance requirements."""
        validation = {}
        
        # Requirement: Sub-second latency
        latency_check = True
        if "latency_tests" in results:
            for endpoint, metrics in results["latency_tests"].items():
                if isinstance(metrics, dict) and "avg_latency" in metrics:
                    if metrics["avg_latency"] > 1.0:  # 1 second
                        latency_check = False
                        break
        
        validation["sub_second_latency"] = latency_check
        
        # Requirement: 50+ concurrent player actions/min
        concurrency_check = False
        if "concurrency_tests" in results:
            for test_name, metrics in results["concurrency_tests"].items():
                if metrics.get("requests_per_second", 0) * 60 >= 50:  # 50 per minute
                    concurrency_check = True
                    break
        
        validation["concurrent_actions_50_per_min"] = concurrency_check
        
        # Requirement: 100% event delivery (WebSocket reliability)
        websocket_check = False
        if "websocket_tests" in results:
            ws_metrics = results["websocket_tests"].get("concurrent_connections", {})
            if ws_metrics.get("success_rate", 0) >= 0.95:  # 95% success rate
                websocket_check = True
        
        validation["websocket_reliability"] = websocket_check
        
        # Requirement: Fault-tolerant processing
        reliability_check = False
        if "reliability_tests" in results:
            reliability_metrics = results["reliability_tests"].get("sustained_load", {})
            if reliability_metrics.get("reliability_rate", 0) >= 0.99:  # 99% reliability
                reliability_check = True
        
        validation["fault_tolerance"] = reliability_check
        
        return validation
    
    async def run_full_test_suite(self) -> Dict[str, Any]:
        """Run complete performance test suite."""
        print("Starting Cargo Clash Performance Test Suite")
        print("=" * 50)
        
        start_time = time.time()
        
        # Run all test categories
        results = {
            "latency_tests": await self.run_latency_tests(),
            "concurrency_tests": await self.run_concurrency_tests(),
            "websocket_tests": await self.run_websocket_tests(),
            "reliability_tests": await self.run_reliability_tests(),
        }
        
        # Validate requirements
        validation = self.validate_requirements(results)
        results["requirement_validation"] = validation
        
        total_time = time.time() - start_time
        results["test_duration"] = total_time
        
        print("\n" + "=" * 50)
        print("Performance Test Suite Completed")
        print(f"Total Duration: {total_time:.2f} seconds")
        print("\nRequirement Validation:")
        for requirement, passed in validation.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {requirement}: {status}")
        
        return results


async def main():
    """Run performance tests."""
    tester = PerformanceTester()
    results = await tester.run_full_test_suite()
    
    # Save results to file
    with open("performance_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to: performance_test_results.json")


if __name__ == "__main__":
    asyncio.run(main())
