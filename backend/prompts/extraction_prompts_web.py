"""
Prompt templates for extracting information from web content.
These prompts are specifically designed for processing cleaned web data using detailed definitions.
"""

from typing import Dict, Any, Optional

# --- Base Prompt Templates ---

def get_material_properties_web_prompt(
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
    "material_properties": get_material_properties_web_prompt,
}

def get_prompt(
    prompt_name: str,
    **kwargs: Any
) -> str:
    """
    Get a web-specific prompt by name with optional formatting parameters.
    
    Args:
        prompt_name: Name of the prompt to retrieve
        **kwargs: Additional parameters to format the prompt
        
    Returns:
        Formatted prompt string
        
    Raises:
        KeyError: If prompt_name is not found in registry
    """
    if prompt_name not in PROMPT_REGISTRY:
        raise KeyError(f"Web prompt '{prompt_name}' not found in registry")
    
    prompt_func = PROMPT_REGISTRY[prompt_name]
    return prompt_func(**kwargs)

# --- Example Usage ---
"""
Example usage:

# Get web material properties prompt
web_prompt = get_prompt("material_properties")

# Get web material properties prompt with custom context
custom_web_prompt = get_prompt(
    "material_properties",
    context="Analyze the following product specification:",
    output_format="MATERIAL: [type]\nFILLING: [percentage]"
)
"""

WEB_EXTRACTION_PROMPT = """
You are an expert at extracting structured information from web content.
Extract the following information from the provided web content:

{extraction_schema}

Web content to process:
{content}

Provide the extracted information in a structured format.
"""

WEB_VALIDATION_PROMPT = """
You are an expert at validating extracted information from web content.
Validate the following extracted information against the original web content:

Original web content:
{content}

Extracted information:
{extracted_info}

Provide validation results and any corrections needed.
""" 