"""
Network and API tools for Agent Zero Gemini
"""
import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import urllib.parse

from core.tools import BaseTool

logger = logging.getLogger(__name__)

class HTTPRequestTool(BaseTool):
    """HTTP request tool for API calls and web requests"""
    
    def __init__(self):
        super().__init__(
            name="http_request",
            description="Make HTTP requests - GET, POST, PUT, DELETE with headers and authentication"
        )
    
    async def execute(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request"""
        try:
            import httpx
            
            # Prepare request parameters
            headers = kwargs.get("headers", {})
            params = kwargs.get("params", {})
            data = kwargs.get("data")
            json_data = kwargs.get("json")
            timeout = kwargs.get("timeout", 30)
            auth = kwargs.get("auth")
            
            # Handle authentication
            auth_obj = None
            if auth:
                if auth.get("type") == "basic":
                    auth_obj = (auth.get("username"), auth.get("password"))
                elif auth.get("type") == "bearer":
                    headers["Authorization"] = f"Bearer {auth.get('token')}"
                elif auth.get("type") == "api_key":
                    if auth.get("location") == "header":
                        headers[auth.get("key", "X-API-Key")] = auth.get("value")
                    elif auth.get("location") == "query":
                        params[auth.get("key", "api_key")] = auth.get("value")
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json_data,
                    auth=auth_obj
                )
                
                # Parse response
                response_data = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "url": str(response.url)
                }
                
                # Try to parse JSON response
                try:
                    response_data["json"] = response.json()
                except:
                    response_data["text"] = response.text
                
                return {
                    "success": True,
                    "response": response_data
                }
                
        except ImportError:
            return {
                "success": False,
                "error": "httpx not installed. Install with: pip install httpx"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "method": {
                "type": "string",
                "description": "HTTP method",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
            },
            "url": {
                "type": "string",
                "description": "Request URL"
            },
            "headers": {
                "type": "object",
                "description": "HTTP headers",
                "optional": True
            },
            "params": {
                "type": "object",
                "description": "Query parameters",
                "optional": True
            },
            "data": {
                "type": "string",
                "description": "Request body data",
                "optional": True
            },
            "json": {
                "type": "object",
                "description": "JSON request body",
                "optional": True
            },
            "timeout": {
                "type": "integer",
                "description": "Request timeout in seconds",
                "default": 30,
                "optional": True
            },
            "auth": {
                "type": "object",
                "description": "Authentication configuration",
                "optional": True
            }
        }

class APITool(BaseTool):
    """Advanced API interaction tool"""
    
    def __init__(self):
        super().__init__(
            name="api_client",
            description="Advanced API client with rate limiting, retries, and response caching"
        )
        self.session_cache = {}
        self.rate_limits = {}
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute API action"""
        try:
            if action == "call":
                return await self._api_call(**kwargs)
            elif action == "batch_call":
                return await self._batch_api_calls(**kwargs)
            elif action == "test_endpoint":
                return await self._test_endpoint(**kwargs)
            elif action == "get_schema":
                return await self._get_api_schema(**kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _api_call(self, **kwargs) -> Dict[str, Any]:
        """Make API call with advanced features"""
        import httpx
        
        url = kwargs.get("url")
        method = kwargs.get("method", "GET")
        retries = kwargs.get("retries", 3)
        retry_delay = kwargs.get("retry_delay", 1)
        cache_response = kwargs.get("cache", False)
        
        # Check cache first
        cache_key = f"{method}:{url}:{json.dumps(kwargs.get('params', {}), sort_keys=True)}"
        if cache_response and cache_key in self.session_cache:
            return {
                "success": True,
                "response": self.session_cache[cache_key],
                "cached": True
            }
        
        # Rate limiting check
        await self._check_rate_limit(url)
        
        last_error = None
        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=kwargs.get("headers", {}),
                        params=kwargs.get("params", {}),
                        json=kwargs.get("json"),
                        timeout=kwargs.get("timeout", 30)
                    )
                    
                    response_data = {
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "url": str(response.url)
                    }
                    
                    try:
                        response_data["json"] = response.json()
                    except:
                        response_data["text"] = response.text
                    
                    # Cache successful response
                    if cache_response and response.status_code == 200:
                        self.session_cache[cache_key] = response_data
                    
                    return {
                        "success": True,
                        "response": response_data,
                        "attempt": attempt + 1
                    }
                    
            except Exception as e:
                last_error = e
                if attempt < retries:
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                
        return {
            "success": False,
            "error": str(last_error),
            "attempts": retries + 1
        }
    
    async def _batch_api_calls(self, **kwargs) -> Dict[str, Any]:
        """Make multiple API calls concurrently"""
        calls = kwargs.get("calls", [])
        max_concurrent = kwargs.get("max_concurrent", 5)
        
        if not calls:
            return {
                "success": False,
                "error": "No API calls provided"
            }
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def make_call(call_config):
            async with semaphore:
                return await self._api_call(**call_config)
        
        # Execute calls concurrently
        tasks = [make_call(call) for call in calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_calls = 0
        failed_calls = 0
        call_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                call_results.append({
                    "call_index": i,
                    "success": False,
                    "error": str(result)
                })
                failed_calls += 1
            else:
                call_results.append({
                    "call_index": i,
                    **result
                })
                if result.get("success"):
                    successful_calls += 1
                else:
                    failed_calls += 1
        
        return {
            "success": True,
            "results": call_results,
            "summary": {
                "total_calls": len(calls),
                "successful": successful_calls,
                "failed": failed_calls
            }
        }
    
    async def _test_endpoint(self, **kwargs) -> Dict[str, Any]:
        """Test API endpoint availability and response"""
        url = kwargs.get("url")
        
        if not url:
            return {
                "success": False,
                "error": "URL required for endpoint testing"
            }
        
        # Test basic connectivity
        start_time = asyncio.get_event_loop().time()
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.head(url, timeout=10)
                
                end_time = asyncio.get_event_loop().time()
                response_time = end_time - start_time
                
                return {
                    "success": True,
                    "endpoint": url,
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "headers": dict(response.headers),
                    "available": response.status_code < 400
                }
                
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            response_time = end_time - start_time
            
            return {
                "success": False,
                "endpoint": url,
                "error": str(e),
                "response_time": response_time,
                "available": False
            }
    
    async def _get_api_schema(self, **kwargs) -> Dict[str, Any]:
        """Get API schema/documentation"""
        url = kwargs.get("url")
        schema_format = kwargs.get("format", "openapi")
        
        # Common schema endpoints
        schema_endpoints = {
            "openapi": ["/openapi.json", "/swagger.json", "/api-docs"],
            "jsonapi": ["/api/schema", "/schema.json"],
            "graphql": ["/graphql/schema", "/graphql"]
        }
        
        base_url = url.rstrip('/')
        
        for endpoint in schema_endpoints.get(schema_format, []):
            try:
                schema_url = base_url + endpoint
                result = await self._api_call(url=schema_url, method="GET")
                
                if result.get("success") and result.get("response", {}).get("status_code") == 200:
                    return {
                        "success": True,
                        "schema_url": schema_url,
                        "schema": result["response"].get("json", result["response"].get("text")),
                        "format": schema_format
                    }
                    
            except Exception:
                continue
        
        return {
            "success": False,
            "error": f"No {schema_format} schema found at common endpoints",
            "attempted_endpoints": schema_endpoints.get(schema_format, [])
        }
    
    async def _check_rate_limit(self, url: str):
        """Check and enforce rate limiting"""
        domain = urllib.parse.urlparse(url).netloc
        
        if domain in self.rate_limits:
            last_request_time = self.rate_limits[domain]
            time_since_last = asyncio.get_event_loop().time() - last_request_time
            
            # Minimum 100ms between requests to same domain
            if time_since_last < 0.1:
                await asyncio.sleep(0.1 - time_since_last)
        
        self.rate_limits[domain] = asyncio.get_event_loop().time()
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "action": {
                "type": "string",
                "description": "API action to perform",
                "enum": ["call", "batch_call", "test_endpoint", "get_schema"]
            },
            "url": {
                "type": "string",
                "description": "API endpoint URL"
            },
            "method": {
                "type": "string",
                "description": "HTTP method",
                "default": "GET",
                "optional": True
            },
            "headers": {
                "type": "object",
                "description": "HTTP headers",
                "optional": True
            },
            "params": {
                "type": "object",
                "description": "Query parameters",
                "optional": True
            },
            "json": {
                "type": "object",
                "description": "JSON request body",
                "optional": True
            },
            "retries": {
                "type": "integer",
                "description": "Number of retry attempts",
                "default": 3,
                "optional": True
            },
            "cache": {
                "type": "boolean",
                "description": "Cache response",
                "default": False,
                "optional": True
            },
            "calls": {
                "type": "array",
                "description": "Array of API call configurations (for batch_call)",
                "optional": True
            },
            "max_concurrent": {
                "type": "integer",
                "description": "Maximum concurrent requests (for batch_call)",
                "default": 5,
                "optional": True
            },
            "format": {
                "type": "string",
                "description": "Schema format (for get_schema)",
                "enum": ["openapi", "jsonapi", "graphql"],
                "default": "openapi",
                "optional": True
            }
        }

class WebhookTool(BaseTool):
    """Webhook management tool"""
    
    def __init__(self):
        super().__init__(
            name="webhook_manager",
            description="Create and manage webhooks for receiving HTTP callbacks"
        )
        self.active_webhooks = {}
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Manage webhooks"""
        try:
            if action == "create":
                return await self._create_webhook(**kwargs)
            elif action == "list":
                return await self._list_webhooks()
            elif action == "delete":
                return await self._delete_webhook(**kwargs)
            elif action == "test":
                return await self._test_webhook(**kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _create_webhook(self, **kwargs) -> Dict[str, Any]:
        """Create webhook endpoint"""
        from fastapi import FastAPI, Request
        import uvicorn
        
        port = kwargs.get("port", 8000)
        path = kwargs.get("path", "/webhook")
        webhook_id = kwargs.get("webhook_id", f"webhook_{len(self.active_webhooks)}")
        
        app = FastAPI()
        received_data = []
        
        @app.post(path)
        async def webhook_handler(request: Request):
            data = {
                "timestamp": asyncio.get_event_loop().time(),
                "headers": dict(request.headers),
                "method": request.method,
                "url": str(request.url)
            }
            
            try:
                data["json"] = await request.json()
            except:
                data["body"] = await request.body()
            
            received_data.append(data)
            return {"status": "received"}
        
        # Store webhook info
        self.active_webhooks[webhook_id] = {
            "app": app,
            "port": port,
            "path": path,
            "data": received_data,
            "url": f"http://localhost:{port}{path}"
        }
        
        return {
            "success": True,
            "webhook_id": webhook_id,
            "url": f"http://localhost:{port}{path}",
            "message": f"Webhook created at {path} on port {port}"
        }
    
    async def _list_webhooks(self) -> Dict[str, Any]:
        """List active webhooks"""
        webhooks = []
        for webhook_id, info in self.active_webhooks.items():
            webhooks.append({
                "webhook_id": webhook_id,
                "url": info["url"],
                "received_count": len(info["data"])
            })
        
        return {
            "success": True,
            "webhooks": webhooks
        }
    
    async def _delete_webhook(self, **kwargs) -> Dict[str, Any]:
        """Delete webhook"""
        webhook_id = kwargs.get("webhook_id")
        
        if webhook_id in self.active_webhooks:
            del self.active_webhooks[webhook_id]
            return {
                "success": True,
                "message": f"Webhook {webhook_id} deleted"
            }
        else:
            return {
                "success": False,
                "error": f"Webhook {webhook_id} not found"
            }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "action": {
                "type": "string",
                "description": "Webhook action",
                "enum": ["create", "list", "delete", "test"]
            },
            "port": {
                "type": "integer",
                "description": "Port for webhook server",
                "default": 8000,
                "optional": True
            },
            "path": {
                "type": "string",
                "description": "Webhook endpoint path",
                "default": "/webhook",
                "optional": True
            },
            "webhook_id": {
                "type": "string",
                "description": "Webhook identifier",
                "optional": True
            }
        }
