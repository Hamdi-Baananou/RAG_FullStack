from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from langchain.vectorstores.base import VectorStoreRetriever
from langchain.docstore.document import Document
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
import asyncio
import json
import re
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from config import get_settings

class LLMInterface:
    """Service for handling LLM interactions and web scraping."""
    
    def __init__(self):
        """Initialize the LLM interface with configuration."""
        self.settings = get_settings()
        self.llm = self._initialize_llm()
        
        # Website configurations for scraping
        self.website_configs = [
            {
                "name": "TE Connectivity",
                "base_url_template": "https://www.te.com/en/product-{part_number}.html",
                "pre_extraction_js": (
                    "(async () => {"
                    "    const expandButtonSelector = '#pdp-features-expander-btn';"
                    "    const featuresPanelSelector = '#pdp-features-tabpanel';"
                    "    const expandButton = document.querySelector(expandButtonSelector);"
                    "    const featuresPanel = document.querySelector(featuresPanelSelector);"
                    "    if (expandButton && expandButton.getAttribute('aria-selected') === 'false') {"
                    "        console.log('Features expand button indicates collapsed state, clicking...');"
                    "        expandButton.click();"
                    "        await new Promise(r => setTimeout(r, 1500));"
                    "        console.log('Expand button clicked and waited.');"
                    "    } else if (expandButton) {"
                    "        console.log('Features expand button already indicates expanded state.');"
                    "    } else {"
                    "        console.log('Features expand button selector not found:', expandButtonSelector);"
                    "        if (featuresPanel && !featuresPanel.offsetParent) {"
                    "           console.warn('Button not found, but panel seems hidden. JS might need adjustment.');"
                    "        } else if (!featuresPanel) {"
                    "           console.warn('Neither expand button nor features panel found.');"
                    "        }"
                    "    }"
                    "})();"
                ),
                "table_selector": "#pdp-features-tabpanel",
                "part_number_pattern": r"^\d{7}-\d$"
            },
            {
                "name": "Molex",
                "base_url_template": "https://www.molex.com/en-us/products/part-detail/{part_number}#part-details",
                "pre_extraction_js": None,
                "table_selector": "body",
                "part_number_pattern": r"^\d{9}$"
            },
            {
                "name": "TraceParts",
                "base_url_template": "https://www.traceparts.com/en/search?CatalogPath=&KeepFilters=true&Keywords={part_number}&SearchAction=Keywords",
                "pre_extraction_js": None,
                "table_selector": ".technical-data",
                "part_number_pattern": None
            }
        ]

    def _initialize_llm(self) -> ChatGroq:
        """Initialize the Groq LLM client."""
        if not self.settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in the environment variables.")

        try:
            llm = ChatGroq(
                temperature=self.settings.LLM_TEMPERATURE,
                groq_api_key=self.settings.GROQ_API_KEY,
                model_name=self.settings.LLM_MODEL_NAME,
                max_tokens=self.settings.LLM_MAX_OUTPUT_TOKENS
            )
            logger.info(f"Groq LLM initialized with model: {self.settings.LLM_MODEL_NAME}")
            return llm
        except Exception as e:
            logger.error(f"Failed to initialize Groq LLM: {e}")
            raise ConnectionError(f"Could not initialize Groq LLM: {e}")

    @staticmethod
    def format_docs(docs: List[Document]) -> str:
        """Format retrieved documents into a string for the prompt."""
        context_parts = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get('source', 'Unknown')
            page = doc.metadata.get('page', 'N/A')
            start_index = doc.metadata.get('start_index', None)
            chunk_info = f"Chunk {i+1}" + (f" (starts at char {start_index})" if start_index is not None else "")
            context_parts.append(
                f"{chunk_info} from '{source}' (Page {page}):\n{doc.page_content}"
            )
        return "\n\n---\n\n".join(context_parts)

    def create_pdf_extraction_chain(self, retriever: VectorStoreRetriever) -> Optional[Any]:
        """Create a RAG chain for PDF extraction."""
        if retriever is None or self.llm is None:
            logger.error("Retriever or LLM is not initialized for PDF extraction chain.")
            return None

        template = """
You are an expert data extractor. Your goal is to extract a specific piece of information based on the Extraction Instructions provided below, using ONLY the Document Context from PDFs.

Part Number Information (if provided by user):
{part_number}

--- Document Context (from PDFs) ---
{context}
--- End Document Context ---

Extraction Instructions:
{extraction_instructions}

---
IMPORTANT: Respond with ONLY a single, valid JSON object containing exactly one key-value pair.
- The key for the JSON object MUST be the string: "{attribute_key}"
- The value MUST be the extracted result determined by following the Extraction Instructions using the Document Context provided above.
- Provide the value as a JSON string. Examples: "GF, T", "none", "NOT FOUND", "Female", "7.2", "999".
- Do NOT include any explanations, reasoning, or any text outside of the single JSON object in your response.

Example Output Format:
{{"{attribute_key}": "extracted_value_from_pdf"}}

Output:
"""
        prompt = PromptTemplate.from_template(template)

        pdf_chain = (
            RunnableParallel(
                context=RunnablePassthrough() | (lambda x: retriever.invoke(f"Extract information about {x['attribute_key']} for part number {x.get('part_number', 'N/A')}")) | self.format_docs,
                extraction_instructions=RunnablePassthrough(),
                attribute_key=RunnablePassthrough(),
                part_number=RunnablePassthrough()
            )
            .assign(
                extraction_instructions=lambda x: x['extraction_instructions']['extraction_instructions'],
                attribute_key=lambda x: x['attribute_key']['attribute_key'],
                part_number=lambda x: x['part_number'].get('part_number', "Not Provided")
            )
            | prompt
            | self.llm
            | StrOutputParser()
        )
        logger.info("PDF Extraction RAG chain created successfully.")
        return pdf_chain

    def create_web_extraction_chain(self) -> Optional[Any]:
        """Create a chain for web data extraction."""
        if self.llm is None:
            logger.error("LLM is not initialized for Web extraction chain.")
            return None

        template = """
You are an expert data extractor. Your goal is to answer a specific piece of information by applying the logic described in the 'Extraction Instructions' to the 'Cleaned Scraped Website Data' provided below. Use ONLY the provided website data as your context.

--- Cleaned Scraped Website Data ---
{cleaned_web_data}
--- End Cleaned Scraped Website Data ---

Extraction Instructions:
{extraction_instructions}

---
IMPORTANT: Follow the Extraction Instructions carefully using the website data.
Respond with ONLY a single, valid JSON object containing exactly one key-value pair.
- The key for the JSON object MUST be the string: "{attribute_key}"
- The value MUST be the result obtained by applying the Extraction Instructions to the Cleaned Scraped Website Data.
- Provide the value as a JSON string.
- If the information cannot be determined from the Cleaned Scraped Website Data based on the instructions, the value MUST be "NOT FOUND".
- Do NOT include any explanations or reasoning outside the JSON object.

Example Output Format:
{{"{attribute_key}": "extracted_value_based_on_instructions"}}

Output:
"""
        prompt = PromptTemplate.from_template(template)

        web_chain = (
            RunnableParallel(
                cleaned_web_data=RunnablePassthrough(),
                extraction_instructions=RunnablePassthrough(),
                attribute_key=RunnablePassthrough()
            )
            .assign(
                cleaned_web_data=lambda x: x['cleaned_web_data']['cleaned_web_data'],
                extraction_instructions=lambda x: x['extraction_instructions']['extraction_instructions'],
                attribute_key=lambda x: x['attribute_key']['attribute_key']
            )
            | prompt
            | self.llm
            | StrOutputParser()
        )
        logger.info("Web Data Extraction chain created successfully.")
        return web_chain

    async def extract_attribute(self, 
                              attribute_key: str, 
                              extraction_instructions: str, 
                              part_number: Optional[str] = None,
                              retriever: Optional[VectorStoreRetriever] = None) -> Tuple[str, str, float]:
        """
        Extract attribute using two-stage approach (web first, then PDF fallback).
        
        Args:
            attribute_key: The key for the attribute to extract
            extraction_instructions: Instructions for extraction
            part_number: Optional part number for web scraping
            retriever: Optional retriever for PDF fallback
            
        Returns:
            Tuple of (extracted_value, source, latency)
        """
        start_time = asyncio.get_event_loop().time()
        
        # Stage 1: Try web extraction if part number is provided
        if part_number:
            try:
                web_data = await self.scrape_website_table_html(part_number)
                if web_data:
                    web_chain = self.create_web_extraction_chain()
                    if web_chain:
                        web_result = await self.invoke_chain_and_process(
                            web_chain,
                            {
                                'cleaned_web_data': web_data,
                                'extraction_instructions': extraction_instructions,
                                'attribute_key': attribute_key
                            },
                            attribute_key
                        )
                        
                        try:
                            result_dict = json.loads(web_result)
                            if attribute_key in result_dict and result_dict[attribute_key] != "NOT FOUND":
                                latency = asyncio.get_event_loop().time() - start_time
                                return result_dict[attribute_key], "web", latency
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse web extraction result for {attribute_key}")
            except Exception as e:
                logger.error(f"Web extraction failed for {attribute_key}: {e}")
        
        # Stage 2: PDF fallback
        if retriever:
            try:
                pdf_chain = self.create_pdf_extraction_chain(retriever)
                if pdf_chain:
                    pdf_result = await self.invoke_chain_and_process(
                        pdf_chain,
                        {
                            'extraction_instructions': extraction_instructions,
                            'attribute_key': attribute_key,
                            'part_number': part_number
                        },
                        attribute_key
                    )
                    
                    try:
                        result_dict = json.loads(pdf_result)
                        if attribute_key in result_dict:
                            latency = asyncio.get_event_loop().time() - start_time
                            return result_dict[attribute_key], "pdf", latency
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse PDF extraction result for {attribute_key}")
            except Exception as e:
                logger.error(f"PDF extraction failed for {attribute_key}: {e}")
        
        # If both stages fail
        latency = asyncio.get_event_loop().time() - start_time
        return "NOT FOUND", "none", latency

    async def invoke_chain_and_process(self, chain: Any, input_data: Dict[str, Any], attribute_key: str) -> str:
        """Invoke chain, handle errors, and clean response."""
        try:
            response = await chain.ainvoke(input_data)
            logger.info(f"Chain invoked successfully for '{attribute_key}'. Response length: {len(response) if response else 0}")

            if response is None:
                logger.error(f"Chain invocation returned None for '{attribute_key}'")
                return json.dumps({"error": f"Chain invocation returned None for {attribute_key}"})

            cleaned_response = self._clean_chain_response(response, attribute_key)
            return cleaned_response

        except Exception as e:
            logger.error(f"Error during chain invocation for '{attribute_key}': {e}")
            return json.dumps({"error": f"Chain invocation failed: {str(e)}"})

    def _clean_chain_response(self, response: str, attribute_key: str) -> str:
        """Clean and validate chain response."""
        cleaned_response = response

        # Remove <think> tags
        think_start_tag = "<think>"
        think_end_tag = "</think>"
        start_index_think = cleaned_response.find(think_start_tag)
        end_index_think = cleaned_response.find(think_end_tag)
        if start_index_think != -1 and end_index_think != -1 and end_index_think > start_index_think:
            cleaned_response = cleaned_response[end_index_think + len(think_end_tag):].strip()

        # Remove ```json ... ``` markdown
        if cleaned_response.strip().startswith("```json"):
            cleaned_response = cleaned_response.strip()[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

        # Extract JSON object
        try:
            first_brace = cleaned_response.find('{')
            last_brace = cleaned_response.rfind('}')
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                potential_json = cleaned_response[first_brace:last_brace + 1]
                json.loads(potential_json)  # Validate JSON
                cleaned_response = potential_json
            else:
                logger.warning(f"No valid JSON object found in response for '{attribute_key}'")
                return json.dumps({attribute_key: "NOT FOUND"})
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in response for '{attribute_key}'")
            return json.dumps({attribute_key: "NOT FOUND"})

        return cleaned_response

    async def scrape_website_table_html(self, part_number: str) -> Optional[str]:
        """Scrape HTML tables from supplier websites."""
        if not part_number:
            return None

        for config in self.website_configs:
            if config["part_number_pattern"] and not re.match(config["part_number_pattern"], part_number):
                continue

            url = config["base_url_template"].format(part_number=part_number)
            try:
                browser_config = BrowserConfig(
                    headless=True,
                    timeout=self.settings.SCRAPING_TIMEOUT
                )
                
                crawler_config = CrawlerRunConfig(
                    cache_mode=CacheMode.NONE,
                    retries=self.settings.SCRAPING_RETRIES,
                    delay=self.settings.SCRAPING_DELAY
                )
                
                crawler = AsyncWebCrawler(browser_config=browser_config)
                result = await crawler.run(
                    url,
                    config=crawler_config,
                    pre_extraction_js=config["pre_extraction_js"]
                )
                
                if result and result.status_code == 200:
                    html_content = self._extract_html_from_result(result, config["name"])
                    if html_content:
                        cleaned_html = self._clean_scraped_html(html_content, config["name"])
                        if cleaned_html:
                            return cleaned_html
                
            except Exception as e:
                logger.error(f"Failed to scrape {config['name']} for part {part_number}: {e}")
                continue
        
        return None

    def _extract_html_from_result(self, result: Any, site_name: str) -> Optional[str]:
        """Extract HTML content from crawler result."""
        try:
            if hasattr(result, 'html'):
                return result.html
            elif hasattr(result, 'content'):
                return result.content
            else:
                logger.error(f"Could not find HTML content in {site_name} result")
                return None
        except Exception as e:
            logger.error(f"Error extracting HTML from {site_name} result: {e}")
            return None

    def _clean_scraped_html(self, html_content: str, site_name: str) -> Optional[str]:
        """Clean scraped HTML content."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style']):
                element.decompose()
            
            # Remove empty elements
            for element in soup.find_all():
                if len(element.get_text(strip=True)) == 0:
                    element.decompose()
            
            # Site-specific cleaning
            if site_name == "TE Connectivity":
                return self._clean_te_connectivity_html(soup)
            elif site_name == "Molex":
                return self._clean_molex_html(soup)
            else:
                # Generic cleaning for other sites
                return str(soup)
                
        except Exception as e:
            logger.error(f"Error cleaning {site_name} HTML: {e}")
            return None

    def _clean_te_connectivity_html(self, soup: BeautifulSoup) -> str:
        """Clean TE Connectivity specific HTML."""
        # Remove unnecessary attributes
        for tag in soup.find_all(True):
            for attr in ['class', 'id', 'style', 'data-*']:
                if attr in tag.attrs:
                    del tag[attr]
        
        # Extract relevant content
        content = []
        for element in soup.find_all(['table', 'tr', 'td', 'th']):
            text = element.get_text(strip=True)
            if text:
                content.append(text)
        
        return "\n".join(content)

    def _clean_molex_html(self, soup: BeautifulSoup) -> str:
        """Clean Molex specific HTML."""
        # Remove unnecessary attributes
        for tag in soup.find_all(True):
            for attr in ['class', 'id', 'style', 'data-*']:
                if attr in tag.attrs:
                    del tag[attr]
        
        # Extract relevant content
        content = []
        for element in soup.find_all(['table', 'tr', 'td', 'th']):
            text = element.get_text(strip=True)
            if text:
                content.append(text)
        
        return "\n".join(content) 