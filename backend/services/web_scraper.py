from typing import Optional
import asyncio
from loguru import logger
from playwright.async_api import async_playwright
import re

class WebScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    async def initialize(self):
        """Initialize the browser and context."""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    async def cleanup(self):
        """Clean up browser resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def scrape_website_table_html(self, part_number: str) -> Optional[str]:
        """
        Scrape table HTML from supplier websites based on part number.
        
        Args:
            part_number: The part number to search for
            
        Returns:
            Optional[str]: The scraped table HTML if found, None otherwise
        """
        try:
            # Initialize if not already done
            if not self.page:
                await self.initialize()

            # List of supplier websites to try
            supplier_urls = [
                f"https://www.te.com/usa-en/product-{part_number}.html",
                f"https://www.molex.com/molex/products/part-detail/{part_number}",
                # Add more supplier URLs as needed
            ]

            for url in supplier_urls:
                try:
                    logger.info(f"Attempting to scrape {url}")
                    await self.page.goto(url, wait_until="networkidle")
                    
                    # Wait for table to load (adjust selector based on website)
                    await self.page.wait_for_selector("table", timeout=5000)
                    
                    # Get table HTML
                    table_html = await self.page.evaluate("""
                        () => {
                            const tables = document.querySelectorAll('table');
                            for (const table of tables) {
                                // Look for tables with technical specifications
                                const text = table.textContent.toLowerCase();
                                if (text.includes('specification') || 
                                    text.includes('technical') || 
                                    text.includes('parameter')) {
                                    return table.outerHTML;
                                }
                            }
                            return null;
                        }
                    """)

                    if table_html:
                        # Clean up the HTML
                        cleaned_html = self._clean_table_html(table_html)
                        logger.success(f"Successfully scraped table from {url}")
                        return cleaned_html

                except Exception as e:
                    logger.warning(f"Failed to scrape {url}: {e}")
                    continue

            logger.warning(f"No table found for part number {part_number}")
            return None

        except Exception as e:
            logger.error(f"Error during web scraping: {e}")
            return None

    def _clean_table_html(self, html: str) -> str:
        """
        Clean up the scraped table HTML.
        
        Args:
            html: The raw table HTML
            
        Returns:
            str: Cleaned table HTML
        """
        try:
            # Remove unnecessary attributes
            html = re.sub(r'\s+', ' ', html)  # Normalize whitespace
            html = re.sub(r'class="[^"]*"', '', html)  # Remove class attributes
            html = re.sub(r'style="[^"]*"', '', html)  # Remove style attributes
            html = re.sub(r'id="[^"]*"', '', html)  # Remove id attributes
            
            # Remove empty elements
            html = re.sub(r'<[^>]*>\s*</[^>]*>', '', html)
            
            return html.strip()
        except Exception as e:
            logger.error(f"Error cleaning table HTML: {e}")
            return html 