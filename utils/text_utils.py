"""
Text utilities for Agent Zero Gemini
"""
import re
import html
from typing import List, Dict, Optional, Any
from datetime import datetime

class TextUtils:
    """Utility functions for text processing"""
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
        """Truncate text to maximum length"""
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean text by removing extra whitespace and special characters"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        return text
    
    @staticmethod
    def extract_code_blocks(text: str) -> List[Dict[str, str]]:
        """Extract code blocks from markdown-style text"""
        # Pattern for code blocks with optional language
        pattern = r'```(\w+)?\n?(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        code_blocks = []
        for language, code in matches:
            code_blocks.append({
                "language": language or "text",
                "code": code.strip()
            })
        
        return code_blocks
    
    @staticmethod
    def extract_tool_calls(text: str) -> List[Dict[str, Any]]:
        """Extract tool calls from text"""
        # Pattern for TOOL_CALL: format
        pattern = r'TOOL_CALL:\s*(\w+)\((.*?)\)'
        matches = re.findall(pattern, text, re.DOTALL)
        
        tool_calls = []
        for tool_name, params_str in matches:
            # Parse parameters
            params = {}
            if params_str.strip():
                # Simple parameter parsing
                param_pattern = r'(\w+)=(["\'])(.*?)\2'
                param_matches = re.findall(param_pattern, params_str)
                
                for param_name, quote, param_value in param_matches:
                    params[param_name] = param_value
            
            tool_calls.append({
                "name": tool_name,
                "parameters": params
            })
        
        return tool_calls
    
    @staticmethod
    def format_response(text: str, max_line_length: int = 80) -> str:
        """Format response text for better readability"""
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            if len(line) <= max_line_length:
                formatted_lines.append(line)
            else:
                # Word wrap long lines
                words = line.split()
                current_line = ""
                
                for word in words:
                    if len(current_line + " " + word) <= max_line_length:
                        if current_line:
                            current_line += " " + word
                        else:
                            current_line = word
                    else:
                        if current_line:
                            formatted_lines.append(current_line)
                        current_line = word
                
                if current_line:
                    formatted_lines.append(current_line)
        
        return '\n'.join(formatted_lines)
    
    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML characters"""
        return html.escape(text)
    
    @staticmethod
    def unescape_html(text: str) -> str:
        """Unescape HTML characters"""
        return html.unescape(text)
    
    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract URLs from text"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(url_pattern, text)
    
    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """Extract email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(email_pattern, text)
    
    @staticmethod
    def count_words(text: str) -> int:
        """Count words in text"""
        return len(text.split())
    
    @staticmethod
    def count_sentences(text: str) -> int:
        """Count sentences in text"""
        # Simple sentence counting based on punctuation
        sentence_endings = r'[.!?]+\s+'
        sentences = re.split(sentence_endings, text)
        return len([s for s in sentences if s.strip()])
    
    @staticmethod
    def highlight_keywords(text: str, keywords: List[str], highlight_format: str = "**{}**") -> str:
        """Highlight keywords in text"""
        highlighted_text = text
        
        for keyword in keywords:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            highlighted_text = pattern.sub(
                lambda m: highlight_format.format(m.group(0)),
                highlighted_text
            )
        
        return highlighted_text
    
    @staticmethod
    def create_summary(text: str, max_sentences: int = 3) -> str:
        """Create simple summary by taking first few sentences"""
        sentences = re.split(r'[.!?]+\s+', text)
        summary_sentences = sentences[:max_sentences]
        
        # Clean up and join
        summary = '. '.join(s.strip() for s in summary_sentences if s.strip())
        
        if summary and not summary.endswith('.'):
            summary += '.'
        
        return summary
    
    @staticmethod
    def format_timestamp(timestamp: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format timestamp"""
        if timestamp is None:
            timestamp = datetime.now()
        
        return timestamp.strftime(format_str)
    
    @staticmethod
    def parse_key_value_pairs(text: str, separator: str = "=", line_separator: str = "\n") -> Dict[str, str]:
        """Parse key-value pairs from text"""
        pairs = {}
        
        lines = text.split(line_separator)
        for line in lines:
            line = line.strip()
            if separator in line:
                key, value = line.split(separator, 1)
                pairs[key.strip()] = value.strip()
        
        return pairs
    
    @staticmethod
    def create_table(data: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> str:
        """Create simple text table"""
        if not data:
            return ""
        
        # Get headers
        if headers is None:
            headers = list(data[0].keys())
        
        # Calculate column widths
        col_widths = {}
        for header in headers:
            col_widths[header] = len(header)
        
        for row in data:
            for header in headers:
                value = str(row.get(header, ""))
                col_widths[header] = max(col_widths[header], len(value))
        
        # Create table
        lines = []
        
        # Header row
        header_row = " | ".join(header.ljust(col_widths[header]) for header in headers)
        lines.append(header_row)
        
        # Separator row
        separator_row = " | ".join("-" * col_widths[header] for header in headers)
        lines.append(separator_row)
        
        # Data rows
        for row in data:
            data_row = " | ".join(str(row.get(header, "")).ljust(col_widths[header]) for header in headers)
            lines.append(data_row)
        
        return "\n".join(lines)
    
    @staticmethod
    def similarity_score(text1: str, text2: str) -> float:
        """Calculate simple similarity score between two texts"""
        # Convert to lowercase and split into words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 0.0
        
        return intersection / union
