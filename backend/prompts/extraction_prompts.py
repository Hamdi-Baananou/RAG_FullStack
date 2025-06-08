"""
Prompt templates for general information extraction from documents and text.
Each prompt is designed to extract specific types of information in a structured format.
"""

from typing import Dict, Any, Optional

# --- Base Prompt Templates ---

def get_material_properties_prompt(
    context: Optional[str] = None,
    output_format: Optional[str] = None
) -> str:
    """
    Get the prompt for extracting material properties from documents.
    
    Args:
        context: Optional additional context about the material
        output_format: Optional custom output format specification
        
    Returns:
        Formatted prompt string
    """
    base_prompt = """
Extract material filling additives:
Material filling describes additives added to the base material in order to influence the mechanical material characteristics. Most common additives are GF (glass-fiber), GB (glass-balls), MF (mineral-fiber) and T (talcum).
"""
    
    if context:
        base_prompt = f"{context}\n\n{base_prompt}"
    
    if output_format:
        base_prompt = f"{base_prompt}\n\n**Output format:**\n{output_format}"
    else:
        base_prompt = f"{base_prompt}\n\n**Output format:**\nMATERIAL FILLING: [abbreviations/none]"
    
    return base_prompt.strip()

def get_web_material_properties_prompt(
    context: Optional[str] = None,
    output_format: Optional[str] = None
) -> str:
    """
    Get the prompt for extracting material properties from web content.
    
    Args:
        context: Optional additional context about the material
        output_format: Optional custom output format specification
        
    Returns:
        Formatted prompt string
    """
    base_prompt = """
Material filling describes additives added to the base material in order to influence the mechanical material characteristics. Most common additives are GF (glass-fiber), GB (glass-balls), MF (mineral-fiber) and T (talcum).
"""
    
    if context:
        base_prompt = f"{context}\n\n{base_prompt}"
    
    if output_format:
        base_prompt = f"{base_prompt}\n\n**Output format:**\n{output_format}"
    else:
        base_prompt = f"{base_prompt}\n\n**Output format:**\nMATERIAL FILLING: [abbreviations/none]"
    
    return base_prompt.strip()

# --- Prompt Registry ---

PROMPT_REGISTRY: Dict[str, Any] = {
    "material_properties": get_material_properties_prompt,
    "web_material_properties": get_web_material_properties_prompt,
}

def get_prompt(
    prompt_name: str,
    **kwargs: Any
) -> str:
    """
    Get a prompt by name with optional formatting parameters.
    
    Args:
        prompt_name: Name of the prompt to retrieve
        **kwargs: Additional parameters to format the prompt
        
    Returns:
        Formatted prompt string
        
    Raises:
        KeyError: If prompt_name is not found in registry
    """
    if prompt_name not in PROMPT_REGISTRY:
        raise KeyError(f"Prompt '{prompt_name}' not found in registry")
    
    prompt_func = PROMPT_REGISTRY[prompt_name]
    return prompt_func(**kwargs)

# --- Example Usage ---
"""
Example usage:

# Get basic material properties prompt
material_prompt = get_prompt("material_properties")

# Get material properties prompt with custom context
custom_prompt = get_prompt(
    "material_properties",
    context="Analyze the following technical specification:",
    output_format="MATERIAL: [type]\nFILLING: [percentage]"
)
""" 