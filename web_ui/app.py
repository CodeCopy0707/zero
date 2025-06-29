"""
FastAPI web application for Agent Zero Gemini
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from config import config

logger = logging.getLogger(__name__)

class ChatMessage(BaseModel):
    """Chat message model"""
    message: str
    timestamp: Optional[str] = None

class WebSocketManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect client"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client {client_id} connected")
    
    def disconnect(self, client_id: str):
        """Disconnect client"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client {client_id} disconnected")
    
    async def send_personal_message(self, message: str, client_id: str):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: str):
        """Broadcast message to all clients"""
        disconnected_clients = []
        
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

def create_app(agent_app) -> FastAPI:
    """Create FastAPI application"""
    
    app = FastAPI(
        title="Agent Zero Gemini",
        description="Web interface for Agent Zero powered by Gemini AI",
        version="1.0.0"
    )
    
    # WebSocket manager
    websocket_manager = WebSocketManager()
    
    # Templates and static files
    templates = Jinja2Templates(directory="web_ui/templates")
    app.mount("/static", StaticFiles(directory="web_ui/static"), name="static")
    
    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        """Home page"""
        return templates.TemplateResponse("index.html", {
            "request": request,
            "title": "Agent Zero Gemini",
            "agent_name": config.agent.name
        })
    
    @app.get("/api/status")
    async def get_status():
        """Get agent status"""
        try:
            status = await agent_app.get_status()
            return JSONResponse(content=status)
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/tools")
    async def get_tools():
        """Get available tools"""
        try:
            tools = agent_app.root_agent.tool_manager.get_available_tools()
            return JSONResponse(content={"tools": tools})
        except Exception as e:
            logger.error(f"Error getting tools: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/memory/stats")
    async def get_memory_stats():
        """Get memory statistics"""
        try:
            stats = await agent_app.root_agent.memory_manager.get_memory_stats()
            return JSONResponse(content=stats)
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/hierarchy")
    async def get_hierarchy():
        """Get agent hierarchy"""
        try:
            hierarchy = await agent_app.hierarchy_manager.get_hierarchy()
            return JSONResponse(content=hierarchy)
        except Exception as e:
            logger.error(f"Error getting hierarchy: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/chat")
    async def chat(message: ChatMessage):
        """Send chat message"""
        try:
            response = await agent_app.process_user_input(message.message)
            return JSONResponse(content={
                "success": True,
                "response": response,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            return JSONResponse(content={
                "success": False,
                "error": str(e)
            }, status_code=500)
    
    @app.post("/api/chat")
    async def chat(message: ChatMessage):
        """Send chat message"""
        try:
            response = await agent_app.process_user_input(message.message)
            
            return JSONResponse(content={
                "success": True,
                "response": response,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
    
    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str):
        """WebSocket endpoint for real-time communication"""
        await websocket_manager.connect(websocket, client_id)
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                if message_data.get("type") == "chat":
                    # Process chat message
                    user_message = message_data.get("message", "")
                    
                    # Send typing indicator
                    await websocket_manager.send_personal_message(
                        json.dumps({
                            "type": "typing",
                            "message": "Agent is thinking...",
                            "timestamp": datetime.now().isoformat()
                        }),
                        client_id
                    )
                    
                    # Process with agent
                    try:
                        response = await agent_app.process_user_input(user_message)
                        
                        # Send response
                        await websocket_manager.send_personal_message(
                            json.dumps({
                                "type": "response",
                                "message": response,
                                "timestamp": datetime.now().isoformat()
                            }),
                            client_id
                        )
                        
                    except Exception as e:
                        # Send error
                        await websocket_manager.send_personal_message(
                            json.dumps({
                                "type": "error",
                                "message": f"Error: {str(e)}",
                                "timestamp": datetime.now().isoformat()
                            }),
                            client_id
                        )
                
                elif message_data.get("type") == "status":
                    # Send status update
                    status = await agent_app.get_status()
                    await websocket_manager.send_personal_message(
                        json.dumps({
                            "type": "status",
                            "data": status,
                            "timestamp": datetime.now().isoformat()
                        }),
                        client_id
                    )

        except WebSocketDisconnect:
            websocket_manager.disconnect(client_id)
        except Exception as e:
            logger.error(f"WebSocket error for client {client_id}: {e}")
            websocket_manager.disconnect(client_id)

    @app.get("/api/agents")
    async def get_agents():
        """Get all agents information"""
        try:
            hierarchy = await agent_app.hierarchy_manager.get_hierarchy()
            return JSONResponse(content=hierarchy)

        except Exception as e:
            logger.error(f"Error getting agents: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/memory/{agent_id}")
    async def get_agent_memory(agent_id: str, limit: int = 20):
        """Get agent memory"""
        try:
            if agent_id == "root_agent" and agent_app.root_agent:
                interactions = await agent_app.root_agent.memory_manager.get_recent_interactions(limit=limit)
                return JSONResponse(content={"interactions": interactions})
            else:
                return JSONResponse(content={"interactions": []})

        except Exception as e:
            logger.error(f"Error getting agent memory: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/reset")
    async def reset_agent():
        """Reset agent state"""
        try:
            # Reset the agent
            if agent_app.root_agent:
                await agent_app.root_agent.reset()

            return JSONResponse(content={
                "success": True,
                "message": "Agent reset successfully",
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error resetting agent: {e}")
            return JSONResponse(content={
                "success": False,
                "error": str(e)
            }, status_code=500)

    @app.post("/api/clear_memory")
    async def clear_memory():
        """Clear agent memory"""
        try:
            if agent_app.root_agent:
                await agent_app.root_agent.memory_manager.clear_memories()

            return JSONResponse(content={
                "success": True,
                "message": "Memory cleared successfully",
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error clearing memory: {e}")
            return JSONResponse(content={
                "success": False,
                "error": str(e)
            }, status_code=500)

    @app.get("/api/performance")
    async def get_performance():
        """Get performance metrics"""
        try:
            # Get tool statistics
            tool_stats = await agent_app.root_agent.tool_manager.get_tool_statistics()

            # Get memory stats
            memory_stats = await agent_app.root_agent.memory_manager.get_memory_stats()

            # Get hierarchy stats
            hierarchy_stats = await agent_app.hierarchy_manager.get_hierarchy_stats()

            return JSONResponse(content={
                "tools": tool_stats,
                "memory": memory_stats,
                "hierarchy": hierarchy_stats,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            raise HTTPException(status_code=500, detail=str(e))
                "success": True,
                "message": "Agent reset successfully"
            })
            
        except Exception as e:
            logger.error(f"Error resetting agent: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e)
                }
            )
    
    return app

async def run_web_app(agent_app):
    """Run web application"""
    import uvicorn
    
    # Start agent
    await agent_app.start()
    
    # Create FastAPI app
    app = create_app(agent_app)
    
    try:
        # Run server
        config_obj = uvicorn.Config(
            app,
            host=config.web_ui.host,
            port=config.web_ui.port,
            log_level="info"
        )
        server = uvicorn.Server(config_obj)
        
        logger.info(f"Starting web server on {config.web_ui.host}:{config.web_ui.port}")
        await server.serve()
        
    except KeyboardInterrupt:
        logger.info("Web server interrupted by user")
    except Exception as e:
        logger.error(f"Web server error: {e}")
    finally:
        # Stop agent
        await agent_app.stop()
