Odisha RERA Project Scraper
A Python web application that scrapes the first 6 projects from the [Odisha RERA Project List](https://rera.odisha.gov.in/projects/project-list), and fetches:

- RERA Regd. No  
- Project Name  
- Promoter Name  
- Address of the Promoter  
- GST Number  

Technologies Used

- Flask – for serving the frontend/backend  
- Selenium + BeautifulSoup – to scrape JavaScript-based dynamic content  
- HTML + Bootstrap – for a simple, clean frontend  
- Pandas – to save data into a downloadable CSV  

Features

- Click "Scrape Data" to begin real-time scraping  
- Frontend remains blank until scraping is triggered  
- CSV is available to download after scraping  

How It Works (Step-by-Step)
1.User visits the web app – initially, no data is shown
2.User clicks "Scrape Data"
3.Flask triggers the scraper.py, which:
  -Opens the RERA site using Selenium
  -Clicks and scrapes the first 6 View Details pages
  -Extracts required fields
  -Saves data into rera_projects.csv
4.After scraping, the frontend auto-refreshes and shows results in a table
5.User can download results as CSV

How to Run the App Locally

1. Install Python Dependencies
pip install -r requirements.txt

2. Run Flask Server
python app.py

4. Open in Browser
Navigate to: http://127.0.0.1:5000

