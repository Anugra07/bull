"""
Verra Registry Scraper for VM0047 (ARR) Projects.

Scrapes project metadata and monitoring report URLs from the Verra Registry.
Stores results in Supabase `verra_projects` table.

Usage:
    python backend/scripts/scrape_verra.py
    python backend/scripts/scrape_verra.py --methodology VM0047 --max-pages 10
"""

import os
import sys
import re
import time
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from dotenv import load_dotenv
load_dotenv('backend/.env')

try:
    from supabase import create_client, Client
except ImportError:
    print("supabase-py not found. Will run in local-file mode.")
    create_client = None
    Client = None

# --- Config ---
VERRA_SEARCH_URL = "https://registry.verra.org/app/search/VCS"
VERRA_PROJECT_URL = "https://registry.verra.org/app/projectDetail/VCS"
REQUEST_DELAY = 2.0  # seconds between requests (be respectful)
HEADERS = {
    'User-Agent': 'Bull-Carbon-Analyzer/1.0 (Research; contact@bull.dev)',
    'Accept': 'text/html,application/xhtml+xml',
}

# Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
supabase: Optional[Client] = None
if url and key and create_client is not None:
    supabase = create_client(url, key)


def infer_ecosystem(description: str) -> str:
    """Infer ecosystem type from project description text."""
    desc_lower = description.lower()
    if any(w in desc_lower for w in ['mangrove', 'coastal', 'tidal']):
        return 'mangrove'
    elif any(w in desc_lower for w in ['tropical', 'rainforest', 'humid forest']):
        return 'tropical_forest'
    elif any(w in desc_lower for w in ['temperate', 'boreal', 'deciduous']):
        return 'temperate_forest'
    elif any(w in desc_lower for w in ['grassland', 'savanna', 'prairie']):
        return 'grassland'
    elif any(w in desc_lower for w in ['agroforest', 'plantation', 'teak', 'eucalyptus']):
        return 'plantation'
    elif any(w in desc_lower for w in ['reforest', 'afforest', 'arr']):
        return 'reforestation'
    return 'unknown'


def extract_area(text: str) -> Optional[float]:
    """Extract project area in hectares from text."""
    patterns = [
        r'([\d,]+\.?\d*)\s*(?:ha|hectares)',
        r'area.*?([\d,]+\.?\d*)\s*(?:ha|hectares)',
        r'([\d,]+\.?\d*)\s*acres',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = float(match.group(1).replace(',', ''))
            if 'acres' in pattern:
                val *= 0.4047  # Convert acres to ha
            return val
    return None


def scrape_verra_projects(methodology: str = 'VM0047', max_pages: int = 20) -> List[Dict[str, Any]]:
    """
    Scrape Verra Registry for projects using a specific methodology.
    
    NOTE: Verra's registry is a dynamic web app. This scraper attempts to
    access the search results. If the page structure changes, this will need
    updating. Consider using CarbonPlan OffsetsDB as a fallback.
    """
    print(f"Scraping Verra Registry for {methodology} projects...")
    projects = []
    
    for page in range(1, max_pages + 1):
        try:
            # Verra search URL pattern
            search_url = f"{VERRA_SEARCH_URL}/All%20Projects"
            params = {
                'q': methodology,
                'page': page,
            }
            
            response = requests.get(search_url, params=params, headers=HEADERS, timeout=30)
            
            if response.status_code == 429:
                print(f"Rate limited. Waiting 30s...")
                time.sleep(30)
                continue
            
            if response.status_code != 200:
                print(f"Page {page}: HTTP {response.status_code}")
                break
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find project cards/rows
            # Note: Verra uses dynamic Angular rendering, so HTML scraping may
            # return limited results. Fallback strategies are provided below.
            project_elements = soup.find_all('div', class_=re.compile(r'project|search-result'))
            
            if not project_elements:
                # Try table rows
                project_elements = soup.find_all('tr', class_=re.compile(r'project|result'))
            
            if not project_elements:
                print(f"Page {page}: No more results or page structure changed.")
                break
            
            for elem in project_elements:
                try:
                    # Extract project ID
                    project_id = None
                    id_match = re.search(r'(\d{3,5})', elem.get('data-project-id', '') or elem.text)
                    if id_match:
                        project_id = f"VCS-{id_match.group(1)}"
                    
                    # Extract name
                    name_elem = elem.find(['h3', 'h4', 'a', 'td'])
                    name = name_elem.text.strip() if name_elem else 'Unknown'
                    
                    # Extract description for ecosystem inference
                    desc_elem = elem.find('p') or elem.find('td', class_='description')
                    description = desc_elem.text.strip() if desc_elem else ''
                    
                    # Extract country
                    country_elem = elem.find('span', class_=re.compile(r'country|location'))
                    country = country_elem.text.strip() if country_elem else ''
                    
                    # Extract links
                    links = elem.find_all('a', href=True)
                    pd_url = None
                    mr_urls = []
                    for link in links:
                        href = link['href']
                        link_text = link.text.lower()
                        if 'project description' in link_text or 'pd' in link_text:
                            pd_url = href if href.startswith('http') else f"https://registry.verra.org{href}"
                        elif 'monitoring report' in link_text or 'mr' in link_text:
                            mr_url = href if href.startswith('http') else f"https://registry.verra.org{href}"
                            mr_urls.append(mr_url)
                    
                    if project_id:
                        projects.append({
                            'verra_id': project_id,
                            'name': name,
                            'country': country,
                            'status': 'Unknown',  # Would need project detail page
                            'methodology': methodology,
                            'area_ha': extract_area(description),
                            'ecosystem_type': infer_ecosystem(description),
                            'pd_url': pd_url,
                            'mr_urls': mr_urls,  # Not stored in DB, used for PDF parsing
                        })
                except Exception as e:
                    print(f"Error parsing project element: {e}")
                    continue
            
            print(f"Page {page}: Found {len(project_elements)} elements, total {len(projects)} projects")
            time.sleep(REQUEST_DELAY)
            
        except requests.exceptions.RequestException as e:
            print(f"Request error on page {page}: {e}")
            time.sleep(REQUEST_DELAY * 5)
            continue
    
    return projects


def try_offsetsdb_fallback(methodology: str = 'VM0047') -> List[Dict[str, Any]]:
    """
    Fallback: Use CarbonPlan OffsetsDB API for cleaner project metadata.
    https://github.com/carbonplan/offsets-db
    """
    print(f"Trying OffsetsDB fallback for {methodology}...")
    projects = []
    
    try:
        # OffsetsDB API endpoint
        api_url = "https://offsets-db-api.fly.dev/projects"
        params = {
            'registry': 'verra',
            'protocol': methodology,
            'per_page': 100,
        }
        
        response = requests.get(api_url, params=params, headers=HEADERS, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            for item in data.get('data', data if isinstance(data, list) else []):
                projects.append({
                    'verra_id': item.get('project_id', item.get('id', '')),
                    'name': item.get('name', ''),
                    'country': item.get('country', ''),
                    'status': item.get('status', 'Unknown'),
                    'methodology': methodology,
                    'area_ha': None,
                    'ecosystem_type': 'unknown',
                    'pd_url': None,
                    'mr_urls': [],
                })
            print(f"OffsetsDB returned {len(projects)} projects")
        else:
            print(f"OffsetsDB returned {response.status_code}")
            
    except Exception as e:
        print(f"OffsetsDB fallback failed: {e}")
    
    return projects


def save_to_supabase(projects: List[Dict[str, Any]]):
    """Save scraped projects to Supabase."""
    if not supabase:
        print("Supabase not configured. Saving to local CSV instead.")
        import pandas as pd
        df = pd.DataFrame(projects)
        os.makedirs('data', exist_ok=True)
        df.to_csv('data/verra_projects.csv', index=False)
        print(f"Saved {len(projects)} projects to data/verra_projects.csv")
        return
    
    batch_size = 50
    for i in range(0, len(projects), batch_size):
        batch = projects[i:i+batch_size]
        db_records = batch
        
        try:
            supabase.table("verra_projects").upsert(
                db_records, on_conflict="verra_id"
            ).execute()
            print(f"Upserted batch {i//batch_size + 1}")
        except Exception as e:
            print(f"Error upserting batch: {e}")
    
    print(f"Saved {len(projects)} projects to Supabase")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scrape Verra Registry for VM0047 projects")
    parser.add_argument("--methodology", default="VM0047", help="Methodology to filter by")
    parser.add_argument("--max-pages", type=int, default=20, help="Max search pages to scrape")
    parser.add_argument("--fallback", action="store_true", help="Use OffsetsDB API as fallback")
    args = parser.parse_args()
    
    if args.fallback:
        projects = try_offsetsdb_fallback(args.methodology)
    else:
        projects = scrape_verra_projects(args.methodology, args.max_pages)
        
        if len(projects) == 0:
            print("Direct scraping returned 0 results. Trying OffsetsDB fallback...")
            projects = try_offsetsdb_fallback(args.methodology)
    
    if projects:
        save_to_supabase(projects)
        print(f"\nTotal: {len(projects)} {args.methodology} projects scraped and saved.")
    else:
        print("No projects found. Verra may have changed their page structure.")
        print("Try: python backend/scripts/scrape_verra.py --fallback")
