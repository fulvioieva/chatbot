# ip_quality_check.py
import json
import requests
import urllib
import logging
import time

class IPQS:
    def __init__(self):
        self.key = 'ejnA0aVotQsjDYMO7IDb6QijmoVH0yH2'

    def malicious_url_scanner_api(self, url: str, vars: dict = {}) -> dict:
        api_url = f'https://www.ipqualityscore.com/api/json/url/{self.key}/{urllib.parse.quote_plus(url)}'
        response = requests.get(api_url, params=vars)
        return json.loads(response.text)

def check_ip_quality(ip_address, strictness=0, max_retries=3, retry_delay=2):
    ipqs = IPQS()
    additional_params = {'strictness': strictness}

    for attempt in range(max_retries):
        try:
            result = ipqs.malicious_url_scanner_api(ip_address, additional_params)
            logging.info(f"IPQualityScore API response for {ip_address}: {result}")
            
            if 'success' in result:
                if result['success'] == True:
                    return result
                elif 'message' in result and 'timed out' in result['message'].lower():
                    if attempt < max_retries - 1:
                        logging.warning(f"Request timed out. Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logging.error("Max retries reached. Unable to get a valid response.")
                        return {"error": "Timeout error. Unable to get information after multiple attempts."}
                else:
                    logging.error(f"API request failed: {result.get('message', 'No error message provided')}")
            else:
                logging.error(f"Unexpected API response structure: {result}")
            
            return None

        except requests.RequestException as e:
            logging.error(f"Request to IPQualityScore API failed: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error in check_ip_quality: {str(e)}")
            return None

    return None