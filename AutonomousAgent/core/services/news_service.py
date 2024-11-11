import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

class WebScraper: 

    def __init__(self,reference_website):

        self.links:list           = self._extract_links_from_url(reference_website)
        self.source = reference_website

        self.context = {
                        "function" : "provide news", 
                      }
        

    def _extract_text_from_url(self,url):
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
        return self._extract_text_from_url(self.source)