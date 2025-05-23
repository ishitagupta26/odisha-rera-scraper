import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import re
from selenium.webdriver.support.ui import Select

class RERAOdishaScraper:
    def __init__(self):
        """Initialize the scraper with Chrome driver"""
        print("Setting up Chrome driver...")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        # Uncomment the next line if you want to run in headless mode (no browser window)
        # chrome_options.add_argument('--headless')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 10)
        
    def get_project_links(self, max_projects=6):
        """Get project links from the main page"""
        print("Navigating to RERA Odisha projects page...")
        self.driver.get("https://rera.odisha.gov.in/projects/project-list")
             
        # Wait for the page to load completely
        time.sleep(8)
        
        try:
            project_links = []
            processed_projects = 0
            
            print("Looking for project cards...")
            
            # Scroll down to ensure all projects are loaded
            self.driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(3)
            
            while processed_projects < max_projects:
                # Re-find project cards each time to avoid stale element references
                project_cards = []
                selectors = [
                    ".card.project-card.mb-3",
                    ".card.project-card",
                    "div[class*='project-card']",
                    ".card",
                    "div[class*='card']"
                ]
                
                for selector in selectors:
                    cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if cards and len(cards) > 1:
                        project_cards = cards
                        print(f"Found {len(project_cards)} project cards using selector: {selector}")
                        break
                
                if not project_cards:
                    print("No project cards found")
                    break
                
                # Process cards starting from where we left off
                for i in range(processed_projects, min(len(project_cards), max_projects)):
                    try:
                        print(f"\nProcessing project card {i+1}...")
                        
                        # Re-find the specific card to avoid stale reference
                        current_cards = self.driver.find_elements(By.CSS_SELECTOR, selectors[0] if project_cards else ".card")
                        if i >= len(current_cards):
                            print(f"Card {i+1} not found, re-scanning...")
                            break
                            
                        card = current_cards[i]
                        
                        # Look for clickable elements
                        clickable_selectors = [
                            ".//a[contains(text(), 'View Details')]",
                            ".//button[contains(text(), 'View Details')]",
                            ".//a[contains(@class, 'btn') and contains(@class, 'btn-primary')]",
                            ".//a[contains(@class, 'btn')]",
                            ".//button[contains(@class, 'btn')]"
                        ]
                        
                        clicked_successfully = False
                        for selector in clickable_selectors:
                            try:
                                elements = card.find_elements(By.XPATH, selector)
                                for element in elements:
                                    if element.is_displayed() and element.is_enabled():
                                        element_text = element.text.strip()
                                        print(f"Trying to click: '{element_text}'")
                                        
                                        current_url = self.driver.current_url
                                        
                                        try:
                                            # Scroll element into view
                                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                                            time.sleep(1)
                                            
                                            # Try clicking
                                            try:
                                                element.click()
                                            except:
                                                self.driver.execute_script("arguments[0].click();", element)
                                            
                                            time.sleep(4)
                                            new_url = self.driver.current_url
                                            
                                            if (new_url != current_url and 
                                                ('project-details' in new_url or new_url.count('/') > current_url.count('/'))):
                                                
                                                project_links.append(new_url)
                                                processed_projects += 1
                                                clicked_successfully = True
                                                print(f"✓ Added project {processed_projects}: {new_url}")
                                                
                                                # Go back to main page
                                                self.driver.back()
                                                time.sleep(4)
                                                self.driver.execute_script("window.scrollTo(0, 1000);")
                                                time.sleep(2)
                                                break
                                            else:
                                                if new_url != current_url:
                                                    self.driver.back()
                                                    time.sleep(2)
                                                    
                                        except Exception as click_error:
                                            print(f"Click error: {click_error}")
                                            continue
                                            
                                if clicked_successfully:
                                    break
                            except StaleElementReferenceException:
                                print("Stale element reference, breaking to re-scan")
                                break
                            except Exception as e:
                                print(f"Error with selector {selector}: {e}")
                                continue
                        
                        if clicked_successfully:
                            break  # Break to re-scan for fresh elements
                            
                    except StaleElementReferenceException:
                        print(f"Stale element for card {i+1}, re-scanning...")
                        break
                    except Exception as e:
                        print(f"Error processing card {i+1}: {e}")
                        continue
                
                # If we haven't processed any new projects in this iteration, break
                if processed_projects == len(project_links):
                    if processed_projects == 0:
                        break
                    # Try scrolling to load more projects
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)
            
            # Remove duplicates
            project_links = list(dict.fromkeys(project_links))
            
            print(f"\nSuccessfully found {len(project_links)} project detail links:")
            for i, link in enumerate(project_links, 1):
                print(f"{i}. {link}")
                
            return project_links
            
        except Exception as e:
            print(f"Error getting project links: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def scrape_project_details(self, project_url):
        """Scrape details from a single project page"""
        print(f"\nScraping project: {project_url}")
        
        try:
            self.driver.get(project_url)
            time.sleep(5)
            
            project_data = {
                'Rera Regd. No': '',
                'Project Name': '',
                'Promoter Name': '',
                'Address of the Promoter': '',
                'GST No': ''
            }
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            page_text = soup.get_text()
            
            # Extract RERA Registration Number
            rera_patterns = [
                r'RERA\s*Reg(?:d)?\.?\s*No\.?\s*:?\s*([A-Z0-9/\-\.]+)',
                r'Registration\s*No\.?\s*:?\s*([A-Z0-9/\-\.]+)',
                r'Reg\.?\s*No\.?\s*:?\s*([A-Z0-9/\-\.]+)',
                r'RP/\d+/\d+/\d+',
                r'[A-Z]{2}/\d+/\d+/\d+'
            ]
            
            for pattern in rera_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    rera_no = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    rera_no = re.sub(r'Registration.*$', '', rera_no, flags=re.IGNORECASE).strip()
                    project_data['Rera Regd. No'] = rera_no
                    print(f"Found RERA No: {rera_no}")
                    break
            
            # Extract Project Name - improved extraction
            # First try to find it in the project details section
            project_name_patterns = [
                r'Project\s*Name\s*:?\s*([A-Za-z0-9\s\-\.,&()]+?)(?=\s*Project\s*Type|\s*RERA|\s*Registration|\n|$)',
                r'Project\s*Name\s*([A-Za-z0-9\s\-\.,&()]+?)(?=\s*Project\s*Type|\s*RERA|\s*Registration|\n|$)'
            ]
            
            for pattern in project_name_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    project_name = match.group(1).strip()
                    # Clean up project name
                    project_name = re.sub(r'\s+', ' ', project_name)
                    if len(project_name) > 3 and project_name.lower() not in ['projects', 'project', 'details']:
                        project_data['Project Name'] = project_name
                        print(f"Found Project Name: {project_name}")
                        break
            
            # If project name not found, try alternative selectors
            if not project_data['Project Name']:
                try:
                    # Look for specific elements that might contain project name
                    project_name_elements = soup.find_all(['h1', 'h2', 'h3', 'h4'])
                    for element in project_name_elements:
                        text = element.get_text().strip()
                        if (text and len(text) > 3 and 
                            text.lower() not in ['projects', 'project', 'details', 'orera', 'authority'] and
                            'logo' not in text.lower()):
                            project_data['Project Name'] = text
                            print(f"Found Project Name from header: {text}")
                            break
                except:
                    pass
            
            # Click on Promoter tab to get more information
            try:
                promoter_tab = self.driver.find_element(By.XPATH, "//a[contains(text(),'Promoter') or contains(@href,'promoter')]")
                self.driver.execute_script("arguments[0].click();", promoter_tab)
                time.sleep(3)
                print("Clicked Promoter tab")
                
                # Re-parse the page after clicking the tab
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                page_text = soup.get_text()
            except:
                print("Could not find or click Promoter tab")
            
            # Extract Promoter Name
            promoter_patterns = [
                r'Company\s*Name\s*:?\s*([M/S\.\s]*[A-Z][A-Za-z0-9\s\.,&\-()]+?)(?=\s*Company\s*Logo|\s*Registration|\s*Correspondence|\s*Email|\n\s*\n|$)',
                r'Promoter\s*Name\s*:?\s*([M/S\.\s]*[A-Z][A-Za-z0-9\s\.,&\-()]+?)(?=\s*Company|\s*Registration|\s*Email|\n\s*\n|$)',
                r'Promoter\s*:?\s*([M/S\.\s]*[A-Z][A-Za-z0-9\s\.,&\-()]+?)(?=\s*Company|\s*Registration|\s*Email|\n\s*\n|$)',
                r'M/S\.\s*([A-Z][A-Za-z0-9\s\.,&\-()]+?)(?=\s*Company|\s*Registration|\s*Email|\n\s*\n|$)'
            ]
            
            for pattern in promoter_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    promoter_name = match.group(1).strip()
                    promoter_name = re.sub(r'\s+', ' ', promoter_name)
                    promoter_name = re.sub(r'Company Logo.*$', '', promoter_name, flags=re.IGNORECASE).strip()
                    if len(promoter_name) > 3:
                        project_data['Promoter Name'] = promoter_name
                        print(f"Found Promoter Name: {promoter_name}")
                        break
            
            # Extract Registered Office Address
            address_patterns = [
                r'Registered\s*Office\s*Address\s*:?\s*([A-Za-z0-9\s,\-\.:/()]+?)(?=\s*,{3,}|\s*Entity|\s*Email|\s*Mobile|\s*Phone|\n\s*\n|$)',
                r'Office\s*Address\s*:?\s*([A-Za-z0-9\s,\-\.:/()]+?)(?=\s*,{3,}|\s*Entity|\s*Email|\s*Mobile|\s*Phone|\n\s*\n|$)',
                r'Address\s*:?\s*([A-Za-z0-9\s,\-\.:/()]+?)(?=\s*,{3,}|\s*Entity|\s*Email|\s*Mobile|\s*Phone|\n\s*\n|$)'
            ]
            
            for pattern in address_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    address = match.group(1).strip()
                    address = re.sub(r'\s+', ' ', address)
                    address = re.sub(r',+', ',', address)
                    if len(address) > 10:
                        project_data['Address of the Promoter'] = address
                        print(f"Found Address: {address}")
                        break
            
            # Extract GST Number
            gst_patterns = [
                r'GST\s*No\.?\s*:?\s*([A-Z0-9]{15})',
                r'GSTIN\s*:?\s*([A-Z0-9]{15})',
                r'GST\s*:?\s*([A-Z0-9]{15})',
                r'([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1})'
            ]
            
            for pattern in gst_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    gst_no = match.group(1).strip()
                    if len(gst_no) == 15:
                        project_data['GST No'] = gst_no
                        print(f"Found GST No: {gst_no}")
                        break
            
            print(f"Final scraped data: {project_data}")
            return project_data
            
        except Exception as e:
            print(f"Error scraping project details: {e}")
            import traceback
            traceback.print_exc()
            return {
                'Rera Regd. No': '',
                'Project Name': '',
                'Promoter Name': '',
                'Address of the Promoter': '',
                'GST No': ''
            }
    
    def scrape_all_projects(self, max_projects=6):
        """Main method to scrape all projects"""
        print("Starting RERA Odisha project scraping...")
        
        # Get project links
        project_links = self.get_project_links(max_projects)
        
        if not project_links:
            print("No project links found. The website structure might have changed.")
            return []
        
        # Scrape each project
        all_projects_data = []
        for i, project_url in enumerate(project_links, 1):
            print(f"\n--- Scraping Project {i}/{len(project_links)} ---")
            project_data = self.scrape_project_details(project_url)
            project_data['URL'] = project_url
            all_projects_data.append(project_data)
            
            # Add delay between requests
            time.sleep(2)
        
        return all_projects_data
    
    def save_to_csv(self, data, filename='rera_projects.csv'):
        """Save scraped data to CSV file"""
        if data:
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            print(f"\nData saved to {filename}")
            print(f"Total projects scraped: {len(data)}")
            return filename
        else:
            print("No data to save")
            return None
    
    def close(self):
        """Close the browser"""
        self.driver.quit()

def main():
    """Main function to run the scraper"""
    scraper = None
    try:
        # Initialize scraper
        scraper = RERAOdishaScraper()
        
        # Scrape first 6 projects
        projects_data = scraper.scrape_all_projects(max_projects=6)
        
        # Save to CSV
        csv_file = scraper.save_to_csv(projects_data)
        
        # Display results
        if projects_data:
            print("\n" + "="*50)
            print("SCRAPING COMPLETED SUCCESSFULLY!")
            print("="*50)
            
            for i, project in enumerate(projects_data, 1):
                print(f"\nProject {i}:")
                print(f"  RERA Regd. No: {project['Rera Regd. No']}")
                print(f"  Project Name: {project['Project Name']}")
                print(f"  Promoter Name: {project['Promoter Name']}")
                print(f"  Address: {project['Address of the Promoter']}")
                print(f"  GST No: {project['GST No']}")
                print(f"  URL: {project['URL']}")
        else:
            print("\nNo data was scraped. Please check the website structure.")
    
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if scraper:
            scraper.close()

if __name__ == "__main__":
    main()