"""
Gemini AI client for Agent Zero
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from config import config

logger = logging.getLogger(__name__)

class GeminiClient:
    """Client for interacting with Gemini AI"""
    
    def __init__(self):
        """Initialize Gemini client"""
        self.api_key = config.gemini.api_key
        self.model_name = config.gemini.model
        self.temperature = config.gemini.temperature
        self.max_tokens = config.gemini.max_tokens
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=genai.types.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
                top_p=0.95,
                top_k=64,
            ),
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
        )
        
        logger.info(f"Initialized Gemini client with model: {self.model_name}")
    
    async def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> str:
        """Generate response from Gemini"""
        try:
            # Prepare the full prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\nUser: {prompt}"
            
            if stream:
                return await self._generate_streaming_response(full_prompt, tools)
            else:
                return await self._generate_single_response(full_prompt, tools)
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    async def _generate_single_response(self, prompt: str, tools: Optional[List[Dict]] = None) -> str:
        """Generate single response"""
        try:
            # Create chat session
            chat = self.model.start_chat(history=[])
            
            # Generate response
            response = await asyncio.to_thread(chat.send_message, prompt)
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error in single response generation: {e}")
            raise
    
    async def _generate_streaming_response(self, prompt: str, tools: Optional[List[Dict]] = None) -> AsyncGenerator[str, None]:
        """Generate streaming response"""
        try:
            # Create chat session
            chat = self.model.start_chat(history=[])
            
            # Generate streaming response
            response = await asyncio.to_thread(chat.send_message, prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Error in streaming response generation: {e}")
            raise
    
    async def generate_with_tools(
        self, 
        prompt: str, 
        tools: List[Dict],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate response with tool calling capability"""
        try:
            # Prepare the full prompt with tool information
            tool_descriptions = self._format_tools_for_prompt(tools)
            full_prompt = f"{system_prompt or ''}\n\nAvailable tools:\n{tool_descriptions}\n\nUser: {prompt}"
            
            # Generate response
            response = await self._generate_single_response(full_prompt)
            
            # Parse tool calls from response
            tool_calls = self._parse_tool_calls(response)
            
            return {
                "response": response,
                "tool_calls": tool_calls
            }
            
        except Exception as e:
            logger.error(f"Error generating response with tools: {e}")
            raise
    
    def _format_tools_for_prompt(self, tools: List[Dict]) -> str:
        """Format tools for inclusion in prompt"""
        tool_descriptions = []
        for tool in tools:
            desc = f"- {tool['name']}: {tool.get('description', 'No description')}"
            if 'parameters' in tool:
                desc += f"\n  Parameters: {tool['parameters']}"
            tool_descriptions.append(desc)
        return "\n".join(tool_descriptions)
    
    def _parse_tool_calls(self, response: str) -> List[Dict]:
        """Parse tool calls from response"""
        # This is a simplified parser - in a real implementation,
        # you'd want more sophisticated parsing
        tool_calls = []
        
        # Look for tool call patterns in the response
        lines = response.split('\n')
        for line in lines:
            if line.strip().startswith('TOOL_CALL:'):
                try:
                    # Parse tool call format: TOOL_CALL: tool_name(param1=value1, param2=value2)
                    tool_call_str = line.replace('TOOL_CALL:', '').strip()
                    # Simple parsing - you'd want more robust parsing in production
                    if '(' in tool_call_str and ')' in tool_call_str:
                        tool_name = tool_call_str.split('(')[0].strip()
                        params_str = tool_call_str.split('(')[1].split(')')[0]
                        
                        # Parse parameters
                        params = {}
                        if params_str.strip():
                            for param in params_str.split(','):
                                if '=' in param:
                                    key, value = param.split('=', 1)
                                    params[key.strip()] = value.strip().strip('"\'')
                        
                        tool_calls.append({
                            "name": tool_name,
                            "parameters": params
                        })
                except Exception as e:
                    logger.warning(f"Failed to parse tool call: {line}, error: {e}")
        
        return tool_calls
    
    async def chat_with_history(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: Optional[str] = None
    ) -> str:
        """Chat with conversation history"""
        try:
            # Convert messages to Gemini format
            history = []
            for msg in messages[:-1]:  # All except the last message
                history.append({
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [msg["content"]]
                })
            
            # Create chat with history
            chat = self.model.start_chat(history=history)
            
            # Send the latest message
            latest_message = messages[-1]["content"]
            if system_prompt and messages[0]["role"] == "user":
                latest_message = f"{system_prompt}\n\n{latest_message}"
            
            response = await asyncio.to_thread(chat.send_message, latest_message)
            return response.text
            
        except Exception as e:
            logger.error(f"Error in chat with history: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_key_configured": bool(self.api_key)
        }
