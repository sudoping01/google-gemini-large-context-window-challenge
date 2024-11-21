import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

class WebScraper: 
    """
    Web scraper for extracting text and links from websites.

    Provides functionality to extract text content and hyperlinks 
    from a given website while handling various HTTP and parsing errors.

    Attributes:
        links: List of extracted hyperlinks from reference website
        source: URL of the reference website
    """

    def __init__(self,reference_website):

        self.links:list           = self._extract_links_from_url(reference_website)
        self.source = reference_website

        self.context = {
                        "function" : "provide news", 
                      }
        

    def _extract_text_from_url(self,url):
        """
        Extracts all text content from a given URL.
        
        Args:
            url: Website URL to extract text from

        Returns:
            str: Extracted text content or error message if failed
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
    
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            text = soup.get_text(separator=' ', strip=True)
            
            return text
        
        except requests.HTTPError as http_err:
            return f"HTTP error occurred: {http_err}"
        except RequestException as req_err:
            return f"An error occurred while making the request: {req_err}"
        except Exception as err:
            return f"An unexpected error occurred: {err}"
        

    def _extract_links_from_url(self,url):
        """
        Extracts all hyperlinks from a given URL.

        Args:
            url: Website URL to extract links from

        Returns:
            list: List of extracted URLs or error message if failed
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            
            links = soup.find_all('a')
            
            
            extracted_links = []
            for link in links:
                href = link.get('href')
                if href:
                    
                    if href.startswith('/'):
                        href = url + href
                    extracted_links.append(href)
            
            return extracted_links
        
        except requests.HTTPError as http_err:
            return f"HTTP error occurred: {http_err}"
        except RequestException as req_err:
            return f"An error occurred while making the request: {req_err}"
        except Exception as err:
            return f"An unexpected error occurred: {err}"
        

    def get_news(self):
        """
        Retrieves text content from reference website.

        Returns:
            str: Extracted text content or error message
        """
        return self._extract_text_from_url(self.source)