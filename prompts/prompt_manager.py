"""
Prompt management system for Agent Zero Gemini
"""
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml
import json

from .system_prompts import SystemPrompts

logger = logging.getLogger(__name__)

class PromptManager:
    """Manages prompts for agents"""
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """Initialize PromptManager"""
        self.prompts_dir = prompts_dir or Path("prompts")
        self.prompts_dir.mkdir(exist_ok=True)
        
        # Built-in prompts
        self.system_prompts = SystemPrompts()
        
        # Custom prompts loaded from files
        self.custom_prompts: Dict[str, str] = {}
        
        # Prompt templates with variables
        self.templates: Dict[str, str] = {}
        
        # Load custom prompts
        self._load_custom_prompts()
        
        logger.info(f"Initialized PromptManager with {len(self.custom_prompts)} custom prompts")
    
    def _load_custom_prompts(self):
        """Load custom prompts from files"""
        try:
            # Load from YAML files
            for yaml_file in self.prompts_dir.glob("*.yaml"):
                self._load_yaml_prompts(yaml_file)
            
            # Load from JSON files
            for json_file in self.prompts_dir.glob("*.json"):
                self._load_json_prompts(json_file)
            
            # Load from text files
            for txt_file in self.prompts_dir.glob("*.txt"):
                self._load_text_prompt(txt_file)
                
        except Exception as e:
            logger.error(f"Error loading custom prompts: {e}")
    
    def _load_yaml_prompts(self, file_path: Path):
        """Load prompts from YAML file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if isinstance(data, dict):
                for name, content in data.items():
                    if isinstance(content, str):
                        self.custom_prompts[name] = content
                    elif isinstance(content, dict) and 'template' in content:
                        self.templates[name] = content['template']
                        
        except Exception as e:
            logger.error(f"Error loading YAML prompts from {file_path}: {e}")
    
    def _load_json_prompts(self, file_path: Path):
        """Load prompts from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                for name, content in data.items():
                    if isinstance(content, str):
                        self.custom_prompts[name] = content
                    elif isinstance(content, dict) and 'template' in content:
                        self.templates[name] = content['template']
                        
        except Exception as e:
            logger.error(f"Error loading JSON prompts from {file_path}: {e}")
    
    def _load_text_prompt(self, file_path: Path):
        """Load prompt from text file"""
        try:
            name = file_path.stem
            content = file_path.read_text(encoding='utf-8')
            self.custom_prompts[name] = content
            
        except Exception as e:
            logger.error(f"Error loading text prompt from {file_path}: {e}")
    
    def get_prompt(self, name: str, **kwargs) -> str:
        """Get prompt by name"""
        # Try system prompts first
        try:
            return self.system_prompts.get_prompt(name, **kwargs)
        except ValueError:
            pass
        
        # Try custom prompts
        if name in self.custom_prompts:
            prompt = self.custom_prompts[name]
            if kwargs:
                return prompt.format(**kwargs)
            return prompt
        
        # Try templates
        if name in self.templates:
            template = self.templates[name]
            if kwargs:
                return template.format(**kwargs)
            return template
        
        raise ValueError(f"Prompt '{name}' not found")
    
    def add_prompt(self, name: str, content: str, save_to_file: bool = False):
        """Add a custom prompt"""
        self.custom_prompts[name] = content
        
        if save_to_file:
            self._save_prompt_to_file(name, content)
        
        logger.debug(f"Added custom prompt: {name}")
    
    def add_template(self, name: str, template: str, save_to_file: bool = False):
        """Add a prompt template"""
        self.templates[name] = template
        
        if save_to_file:
            self._save_template_to_file(name, template)
        
        logger.debug(f"Added prompt template: {name}")
    
    def _save_prompt_to_file(self, name: str, content: str):
        """Save prompt to file"""
        try:
            file_path = self.prompts_dir / f"{name}.txt"
            file_path.write_text(content, encoding='utf-8')
            
        except Exception as e:
            logger.error(f"Error saving prompt to file: {e}")
    
    def _save_template_to_file(self, name: str, template: str):
        """Save template to file"""
        try:
            file_path = self.prompts_dir / f"{name}_template.yaml"
            data = {name: {"template": template}}
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False)
                
        except Exception as e:
            logger.error(f"Error saving template to file: {e}")
    
    def remove_prompt(self, name: str):
        """Remove a custom prompt"""
        if name in self.custom_prompts:
            del self.custom_prompts[name]
            logger.debug(f"Removed custom prompt: {name}")
        
        if name in self.templates:
            del self.templates[name]
            logger.debug(f"Removed prompt template: {name}")
    
    def list_prompts(self) -> Dict[str, List[str]]:
        """List all available prompts"""
        return {
            "system_prompts": self.system_prompts.list_prompts(),
            "custom_prompts": list(self.custom_prompts.keys()),
            "templates": list(self.templates.keys())
        }
    
    def get_agent_prompt(
        self, 
        agent_type: str = "main", 
        agent_name: str = "Agent Zero",
        agent_role: str = "General Assistant",
        current_task: Optional[str] = None,
        additional_context: Optional[str] = None
    ) -> str:
        """Get agent-specific prompt"""
        
        if agent_type == "main":
            base_prompt = self.get_prompt("main_agent")
        elif agent_type == "subordinate":
            base_prompt = self.get_prompt("subordinate_agent")
        else:
            base_prompt = self.get_prompt("main_agent")
        
        # Customize prompt with agent details
        context_additions = []
        
        if agent_name != "Agent Zero":
            context_additions.append(f"Your name is {agent_name}.")
        
        if agent_role != "General Assistant":
            context_additions.append(f"Your specific role is: {agent_role}")
        
        if current_task:
            context_additions.append(f"Current task: {current_task}")
        
        if additional_context:
            context_additions.append(f"Additional context: {additional_context}")
        
        if context_additions:
            customization = "\n\n## Current Context\n" + "\n".join(context_additions)
            return base_prompt + customization
        
        return base_prompt
    
    def create_dynamic_prompt(
        self,
        base_prompt: str,
        context: Dict[str, Any],
        tools: Optional[List[Dict]] = None,
        memory_context: Optional[str] = None
    ) -> str:
        """Create dynamic prompt with context"""
        
        prompt_parts = [base_prompt]
        
        # Add tool information
        if tools:
            tool_descriptions = []
            for tool in tools:
                desc = f"- {tool['name']}: {tool.get('description', 'No description')}"
                tool_descriptions.append(desc)
            
            tools_section = f"\n\n## Available Tools\n" + "\n".join(tool_descriptions)
            prompt_parts.append(tools_section)
        
        # Add memory context
        if memory_context:
            memory_section = f"\n\n## Memory Context\n{memory_context}"
            prompt_parts.append(memory_section)
        
        # Add current context
        if context:
            context_items = []
            for key, value in context.items():
                if value:
                    context_items.append(f"- {key}: {value}")
            
            if context_items:
                context_section = f"\n\n## Current Context\n" + "\n".join(context_items)
                prompt_parts.append(context_section)
        
        return "\n".join(prompt_parts)
    
    def validate_prompt(self, prompt: str) -> Dict[str, Any]:
        """Validate prompt structure and content"""
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "stats": {
                "length": len(prompt),
                "lines": len(prompt.split('\n')),
                "words": len(prompt.split())
            }
        }
        
        # Check length
        if len(prompt) > 50000:  # Arbitrary limit
            validation_result["warnings"].append("Prompt is very long and may exceed model limits")
        
        if len(prompt) < 50:
            validation_result["warnings"].append("Prompt is very short and may lack necessary context")
        
        # Check for common issues
        if "TOOL_CALL:" not in prompt and "tool" in prompt.lower():
            validation_result["warnings"].append("Prompt mentions tools but doesn't include TOOL_CALL format")
        
        # Check for placeholder variables
        import re
        placeholders = re.findall(r'\{(\w+)\}', prompt)
        if placeholders:
            validation_result["warnings"].append(f"Prompt contains unfilled placeholders: {placeholders}")
        
        return validation_result
    
    def reload_prompts(self):
        """Reload all custom prompts from files"""
        self.custom_prompts.clear()
        self.templates.clear()
        self._load_custom_prompts()
        
        logger.info("Reloaded all custom prompts")
