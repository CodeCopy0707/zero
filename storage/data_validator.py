"""
Data validation for JSON storage system
"""
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import jsonschema

logger = logging.getLogger(__name__)

class DataValidator:
    """Validates JSON data structure and integrity"""
    
    def __init__(self):
        """Initialize data validator with schemas"""
        self.schemas = self._define_schemas()
        
    def _define_schemas(self) -> Dict[str, Dict]:
        """Define JSON schemas for validation"""
        return {
            "agents": {
                "type": "object",
                "properties": {
                    "agents": {
                        "type": "object",
                        "patternProperties": {
                            "^[a-zA-Z0-9_-]+$": {
                                "type": "object",
                                "properties": {
                                    "agent_id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "role": {"type": "string"},
                                    "state": {"type": "string"},
                                    "created": {"type": "string"},
                                    "superior_id": {"type": ["string", "null"]},
                                    "subordinate_ids": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "config": {"type": "object"}
                                },
                                "required": ["agent_id", "name", "role", "state", "created"]
                            }
                        }
                    },
                    "hierarchy": {"type": "object"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "created": {"type": "string"},
                            "version": {"type": "string"}
                        },
                        "required": ["created", "version"]
                    }
                },
                "required": ["agents", "hierarchy", "metadata"]
            },
            
            "memory": {
                "type": "object",
                "properties": {
                    "interactions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "agent_id": {"type": "string"},
                                "role": {"type": "string"},
                                "content": {"type": "string"},
                                "timestamp": {"type": "string"},
                                "metadata": {"type": "object"}
                            },
                            "required": ["id", "agent_id", "role", "content", "timestamp"]
                        }
                    },
                    "facts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "content": {"type": "string"},
                                "importance": {"type": "number"},
                                "timestamp": {"type": "string"},
                                "agent_id": {"type": "string"}
                            },
                            "required": ["id", "content", "importance", "timestamp"]
                        }
                    },
                    "skills": {"type": "array"},
                    "experiences": {"type": "array"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "total_interactions": {"type": "integer"},
                            "last_cleanup": {"type": "string"}
                        }
                    }
                },
                "required": ["interactions", "facts", "skills", "experiences", "metadata"]
            },
            
            "tools": {
                "type": "object",
                "properties": {
                    "tool_configs": {"type": "object"},
                    "usage_logs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "tool_name": {"type": "string"},
                                "agent_id": {"type": "string"},
                                "timestamp": {"type": "string"},
                                "parameters": {"type": "object"},
                                "result": {"type": ["object", "string", "null"]},
                                "success": {"type": "boolean"}
                            },
                            "required": ["tool_name", "agent_id", "timestamp", "success"]
                        }
                    },
                    "custom_tools": {"type": "object"},
                    "metadata": {"type": "object"}
                },
                "required": ["tool_configs", "usage_logs", "custom_tools", "metadata"]
            },
            
            "sessions": {
                "type": "object",
                "properties": {
                    "active_sessions": {"type": "object"},
                    "session_history": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "session_id": {"type": "string"},
                                "start_time": {"type": "string"},
                                "end_time": {"type": ["string", "null"]},
                                "user_id": {"type": ["string", "null"]},
                                "message_count": {"type": "integer"}
                            },
                            "required": ["session_id", "start_time"]
                        }
                    },
                    "metadata": {"type": "object"}
                },
                "required": ["active_sessions", "session_history", "metadata"]
            },
            
            "knowledge": {
                "type": "object",
                "properties": {
                    "facts": {"type": "object"},
                    "procedures": {"type": "object"},
                    "concepts": {"type": "object"},
                    "relationships": {"type": "object"},
                    "metadata": {"type": "object"}
                },
                "required": ["facts", "procedures", "concepts", "relationships", "metadata"]
            },
            
            "instruments": {
                "type": "object",
                "properties": {
                    "custom_instruments": {"type": "object"},
                    "procedures": {"type": "object"},
                    "workflows": {"type": "object"},
                    "metadata": {"type": "object"}
                },
                "required": ["custom_instruments", "procedures", "workflows", "metadata"]
            }
        }
    
    def validate_data(self, data_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against schema"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        if data_type not in self.schemas:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Unknown data type: {data_type}")
            return validation_result
        
        try:
            # Validate against JSON schema
            jsonschema.validate(data, self.schemas[data_type])
            
            # Additional custom validations
            custom_validation = self._custom_validations(data_type, data)
            validation_result["warnings"].extend(custom_validation.get("warnings", []))
            
            if custom_validation.get("errors"):
                validation_result["valid"] = False
                validation_result["errors"].extend(custom_validation["errors"])
                
        except jsonschema.ValidationError as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Schema validation error: {e.message}")
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def _custom_validations(self, data_type: str, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Perform custom validations beyond schema"""
        result = {"errors": [], "warnings": []}
        
        if data_type == "agents":
            result.update(self._validate_agents(data))
        elif data_type == "memory":
            result.update(self._validate_memory(data))
        elif data_type == "tools":
            result.update(self._validate_tools(data))
        elif data_type == "sessions":
            result.update(self._validate_sessions(data))
        
        return result
    
    def _validate_agents(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Custom validation for agents data"""
        errors = []
        warnings = []
        
        agents = data.get("agents", {})
        hierarchy = data.get("hierarchy", {})
        
        # Check agent hierarchy consistency
        for agent_id, agent_data in agents.items():
            # Check superior-subordinate relationships
            superior_id = agent_data.get("superior_id")
            if superior_id and superior_id not in agents:
                errors.append(f"Agent {agent_id} references non-existent superior {superior_id}")
            
            subordinate_ids = agent_data.get("subordinate_ids", [])
            for sub_id in subordinate_ids:
                if sub_id not in agents:
                    errors.append(f"Agent {agent_id} references non-existent subordinate {sub_id}")
                elif agents[sub_id].get("superior_id") != agent_id:
                    warnings.append(f"Inconsistent hierarchy: {sub_id} should have {agent_id} as superior")
        
        # Check for circular references
        def has_circular_reference(agent_id: str, visited: set) -> bool:
            if agent_id in visited:
                return True
            
            visited.add(agent_id)
            superior_id = agents.get(agent_id, {}).get("superior_id")
            if superior_id:
                return has_circular_reference(superior_id, visited.copy())
            
            return False
        
        for agent_id in agents:
            if has_circular_reference(agent_id, set()):
                errors.append(f"Circular reference detected in agent hierarchy involving {agent_id}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_memory(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Custom validation for memory data"""
        errors = []
        warnings = []
        
        interactions = data.get("interactions", [])
        facts = data.get("facts", [])
        
        # Check for duplicate interaction IDs
        interaction_ids = [item.get("id") for item in interactions if item.get("id")]
        if len(interaction_ids) != len(set(interaction_ids)):
            errors.append("Duplicate interaction IDs found")
        
        # Check timestamp format
        for interaction in interactions:
            timestamp = interaction.get("timestamp")
            if timestamp:
                try:
                    datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except ValueError:
                    warnings.append(f"Invalid timestamp format: {timestamp}")
        
        # Check fact importance values
        for fact in facts:
            importance = fact.get("importance", 0)
            if not (0 <= importance <= 1):
                warnings.append(f"Fact importance should be between 0 and 1, got {importance}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_tools(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Custom validation for tools data"""
        errors = []
        warnings = []
        
        usage_logs = data.get("usage_logs", [])
        
        # Check for required fields in usage logs
        for log in usage_logs:
            if not log.get("tool_name"):
                errors.append("Tool usage log missing tool_name")
            if not log.get("agent_id"):
                errors.append("Tool usage log missing agent_id")
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_sessions(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Custom validation for sessions data"""
        errors = []
        warnings = []
        
        session_history = data.get("session_history", [])
        
        # Check session timestamps
        for session in session_history:
            start_time = session.get("start_time")
            end_time = session.get("end_time")
            
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    
                    if end_dt < start_dt:
                        errors.append(f"Session end time before start time: {session.get('session_id')}")
                        
                except ValueError as e:
                    warnings.append(f"Invalid session timestamp: {e}")
        
        return {"errors": errors, "warnings": warnings}
    
    def repair_data(self, data_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to repair common data issues"""
        repaired_data = data.copy()
        
        if data_type == "agents":
            repaired_data = self._repair_agents(repaired_data)
        elif data_type == "memory":
            repaired_data = self._repair_memory(repaired_data)
        elif data_type == "tools":
            repaired_data = self._repair_tools(repaired_data)
        elif data_type == "sessions":
            repaired_data = self._repair_sessions(repaired_data)
        
        return repaired_data
    
    def _repair_agents(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Repair agents data"""
        # Ensure required fields exist
        if "agents" not in data:
            data["agents"] = {}
        if "hierarchy" not in data:
            data["hierarchy"] = {}
        if "metadata" not in data:
            data["metadata"] = {
                "created": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        
        # Fix agent data
        for agent_id, agent_data in data["agents"].items():
            if "subordinate_ids" not in agent_data:
                agent_data["subordinate_ids"] = []
            if "created" not in agent_data:
                agent_data["created"] = datetime.now().isoformat()
        
        return data
    
    def _repair_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Repair memory data"""
        # Ensure required fields exist
        required_fields = ["interactions", "facts", "skills", "experiences", "metadata"]
        for field in required_fields:
            if field not in data:
                data[field] = [] if field != "metadata" else {}
        
        # Fix metadata
        if "total_interactions" not in data["metadata"]:
            data["metadata"]["total_interactions"] = len(data["interactions"])
        if "last_cleanup" not in data["metadata"]:
            data["metadata"]["last_cleanup"] = datetime.now().isoformat()
        
        return data
    
    def _repair_tools(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Repair tools data"""
        required_fields = ["tool_configs", "usage_logs", "custom_tools", "metadata"]
        for field in required_fields:
            if field not in data:
                data[field] = [] if field == "usage_logs" else {}
        
        return data
    
    def _repair_sessions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Repair sessions data"""
        required_fields = ["active_sessions", "session_history", "metadata"]
        for field in required_fields:
            if field not in data:
                data[field] = [] if field == "session_history" else {}
        
        return data
    
    def validate_and_repair(self, data_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data and attempt repairs if needed"""
        validation_result = self.validate_data(data_type, data)
        
        if not validation_result["valid"]:
            logger.warning(f"Data validation failed for {data_type}, attempting repair")
            repaired_data = self.repair_data(data_type, data)
            
            # Re-validate after repair
            repair_validation = self.validate_data(data_type, repaired_data)
            if repair_validation["valid"]:
                logger.info(f"Successfully repaired {data_type} data")
                return {
                    "data": repaired_data,
                    "repaired": True,
                    "original_errors": validation_result["errors"],
                    "validation": repair_validation
                }
            else:
                logger.error(f"Failed to repair {data_type} data")
                return {
                    "data": data,
                    "repaired": False,
                    "errors": validation_result["errors"],
                    "repair_errors": repair_validation["errors"]
                }
        
        return {
            "data": data,
            "repaired": False,
            "validation": validation_result
        }
