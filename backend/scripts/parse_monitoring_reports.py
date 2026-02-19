"""
VM0047 Monitoring Report PDF Parser.

Extracts Stocking Index calibrations, carbon stock data, field plot
information, and performance benchmarks from VM0047 monitoring report PDFs.

Usage:
    python backend/scripts/parse_monitoring_reports.py --pdf path/to/report.pdf
    python backend/scripts/parse_monitoring_reports.py --url https://registry.verra.org/.../report.pdf
    python backend/scripts/parse_monitoring_reports.py --batch  # Process all pending reports from Supabase
"""

import os
import sys
import re
import json
import tempfile
import requests
from typing import Dict, Any, List, Optional

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from dotenv import load_dotenv
load_dotenv('backend/.env')

try:
    import pdfplumber
except ImportError:
    print("pdfplumber not found. Run: pip install pdfplumber")
    sys.exit(1)

try:
    from supabase import create_client, Client
except ImportError:
    print("supabase-py not found. Will run in print-only mode.")
    create_client = None
    Client = None

# Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
supabase: Optional[Client] = None
if url and key and create_client is not None:
    supabase = create_client(url, key)

# --- PDF Download ---

def download_pdf(pdf_url: str) -> str:
    """Download a PDF to a temp file and return the path."""
    headers = {
        'User-Agent': 'Bull-Carbon-Analyzer/1.0 (Research)',
    }
    response = requests.get(pdf_url, headers=headers, timeout=60, stream=True)
    response.raise_for_status()
    
    tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    for chunk in response.iter_content(chunk_size=8192):
        tmp.write(chunk)
    tmp.close()
    return tmp.name


# --- Extraction Functions ---

def extract_stocking_index(text: str) -> Dict[str, Any]:
    """Extract Stocking Index type and calibration data."""
    result = {}
    
    # SI Type
    si_patterns = [
        r'stocking\s+index.*?(NDVI|NDFI|EVI|canopy\s*height|GEDI|LiDAR|LAI)',
        r'(?:remote\s+sensing|spectral)\s+index.*?(NDVI|NDFI|EVI|LAI)',
        r'(NDVI|NDFI|EVI|LAI)\s+(?:was|is)\s+(?:used|selected|chosen)\s+as\s+(?:the\s+)?(?:stocking|vegetation)\s+index',
    ]
    for pattern in si_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['stocking_index_type'] = match.group(1).upper().strip()
            break
    
    # SI → Biomass R²
    r2_patterns = [
        r'R[²2]\s*=?\s*(0\.\d+)',
        r'coefficient\s+of\s+determination.*?(0\.\d+)',
        r'r-squared.*?(0\.\d+)',
    ]
    for pattern in r2_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['si_biomass_r_squared'] = float(match.group(1))
            break
    
    # Regression equation
    eq_patterns = [
        r'(?:AGB|biomass|AGC)\s*=\s*([\d.]+)\s*\*?\s*(?:NDVI|EVI|SI|NDFI)[\s+\-]*([\d.]*)',
        r'(?:y|AGB)\s*=\s*([\d.]+)\s*[xX×]\s*[+\-]?\s*([\d.]*)',
    ]
    for pattern in eq_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['si_biomass_equation'] = match.group(0).strip()
            break
    
    return result


def extract_performance_benchmark(text: str) -> Optional[float]:
    """Extract Performance Benchmark value from VM0047 report."""
    patterns = [
        r'performance\s+benchmark.*?(\d+\.?\d*)\s*(?:tC|tCO2|t\s*CO2)',
        r'(?:PB|benchmark)\s*[:=]\s*(\d+\.?\d*)',
        r'performance\s+benchmark\s+(?:value|is|of)\s*[:=]?\s*(\d+\.?\d*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def extract_carbon_stocks(text: str) -> Dict[str, float]:
    """Extract carbon stock values at different time points."""
    stocks = {}
    
    # Pattern: "carbon stock at t0 = 45.2 tC/ha"
    patterns = [
        r'(?:carbon\s+stock|C\s+stock|AGC).*?(?:t|year|period)\s*(\d+).*?(\d+\.?\d+)\s*(?:tC/ha|tCO2e?/ha)',
        r'(?:t|T)(\d+).*?(\d+\.?\d+)\s*(?:tC|tCO2)',
        r'(\d+\.?\d+)\s*(?:tC/ha|tCO2e?/ha).*?(?:t|year|period)\s*(\d+)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                if pattern == patterns[2]:  # Reversed order
                    stocks[f"t{match[1]}"] = float(match[0])
                else:
                    stocks[f"t{match[0]}"] = float(match[1])
            except (ValueError, IndexError):
                continue
    
    # Also look for standalone carbon stock values
    standalone = re.findall(r'(\d+\.?\d+)\s*tC/ha', text, re.IGNORECASE)
    if standalone and not stocks:
        stocks['reported'] = [float(v) for v in standalone[:5]]  # Cap at 5 values
    
    return stocks


def extract_field_plots(text: str) -> Dict[str, Any]:
    """Extract field plot information."""
    result = {}
    
    # Number of plots
    plot_patterns = [
        r'(\d+)\s*(?:permanent\s+)?(?:sample\s+)?plots?\s+(?:were\s+)?(?:established|measured|surveyed)',
        r'(?:total\s+of\s+)?(\d+)\s*(?:field\s+)?plots?',
        r'(\d+)\s+(?:PSP|CSP|plot)',
    ]
    for pattern in plot_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            n = int(match.group(1))
            if 1 <= n <= 10000:  # Sanity check
                result['n_field_plots'] = n
                break
    
    return result


def extract_monitoring_year(text: str) -> Optional[int]:
    """Extract the monitoring period year."""
    patterns = [
        r'monitoring\s+period.*?(\d{4})',
        r'(?:reporting|verification)\s+period.*?(\d{4})',
        r'(\d{4})\s*[-–]\s*\d{4}',  # Date range
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            year = int(match.group(1))
            if 2015 <= year <= 2030:
                return year
    return None


def extract_plot_level_data(tables: List) -> List[Dict[str, Any]]:
    """Extract plot-level biomass data from tables."""
    plot_data = []
    
    for table in tables:
        if not table or len(table) < 2:
            continue
        
        # Check if table header contains biomass-related columns
        header = [str(cell).lower() if cell else '' for cell in table[0]]
        header_text = ' '.join(header)
        
        if not any(kw in header_text for kw in ['biomass', 'agb', 'dbh', 'basal', 'carbon', 'volume']):
            continue
        
        # Find column indices
        biomass_col = None
        dbh_col = None
        species_col = None
        plot_col = None
        
        for i, h in enumerate(header):
            if any(kw in h for kw in ['biomass', 'agb', 'agc']):
                biomass_col = i
            elif 'dbh' in h or 'diameter' in h:
                dbh_col = i
            elif 'species' in h or 'sp.' in h:
                species_col = i
            elif 'plot' in h or 'id' in h:
                plot_col = i
        
        # Extract rows
        for row in table[1:]:
            try:
                entry = {}
                if biomass_col is not None and row[biomass_col]:
                    val = re.sub(r'[^\d.]', '', str(row[biomass_col]))
                    if val:
                        entry['biomass'] = float(val)
                if dbh_col is not None and row[dbh_col]:
                    val = re.sub(r'[^\d.]', '', str(row[dbh_col]))
                    if val:
                        entry['dbh'] = float(val)
                if species_col is not None and row[species_col]:
                    entry['species'] = str(row[species_col]).strip()
                if plot_col is not None and row[plot_col]:
                    entry['plot_id'] = str(row[plot_col]).strip()
                
                if entry:
                    plot_data.append(entry)
            except (ValueError, IndexError):
                continue
    
    return plot_data


# --- Main Parser ---

def parse_monitoring_report(pdf_path: str) -> Dict[str, Any]:
    """
    Parse a VM0047 monitoring report PDF and extract all relevant data.
    
    Returns dict with: stocking_index_type, si_biomass_r_squared,
    si_biomass_equation, performance_benchmark, carbon_stocks,
    n_field_plots, plot_data, monitoring_year
    """
    print(f"Parsing: {pdf_path}")
    
    data = {}
    all_text = ""
    all_tables = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    all_text += page_text + "\n"
                
                page_tables = page.extract_tables()
                if page_tables:
                    all_tables.extend(page_tables)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return data
    
    # Extract all data points
    si_data = extract_stocking_index(all_text)
    data.update(si_data)
    
    pb = extract_performance_benchmark(all_text)
    if pb is not None:
        data['performance_benchmark'] = pb
    
    carbon = extract_carbon_stocks(all_text)
    if carbon:
        data['carbon_stocks'] = carbon
    
    plots = extract_field_plots(all_text)
    data.update(plots)
    
    year = extract_monitoring_year(all_text)
    if year:
        data['monitoring_year'] = year
    
    # Extract plot-level data from tables
    plot_data = extract_plot_level_data(all_tables)
    if plot_data:
        data['plot_data'] = plot_data
    
    # Summary
    print(f"  SI Type: {data.get('stocking_index_type', 'not found')}")
    print(f"  R²: {data.get('si_biomass_r_squared', 'not found')}")
    print(f"  Benchmark: {data.get('performance_benchmark', 'not found')}")
    print(f"  Carbon stocks: {len(carbon)} time points")
    print(f"  Field plots: {data.get('n_field_plots', 'not found')}")
    print(f"  Plot-level rows: {len(plot_data)}")
    
    return data


def save_monitoring_data(project_id: str, report_url: str, data: Dict[str, Any]):
    """Save parsed monitoring data to Supabase."""
    if not supabase:
        print("Supabase not configured. Printing results only.")
        print(json.dumps(data, indent=2, default=str))
        return
    
    record = {
        'project_id': project_id,
        'report_url': report_url,
        'monitoring_year': data.get('monitoring_year'),
        'stocking_index_type': data.get('stocking_index_type'),
        'si_biomass_r_squared': data.get('si_biomass_r_squared'),
        'si_biomass_equation': data.get('si_biomass_equation'),
        'performance_benchmark': data.get('performance_benchmark'),
        'carbon_stocks': data.get('carbon_stocks'),
        'n_field_plots': data.get('n_field_plots'),
        'plot_data': data.get('plot_data'),
        'gee_features': data.get('gee_features'),
    }
    
    try:
        supabase.table("verra_monitoring_data").insert(record).execute()
        print(f"Saved monitoring data for project {project_id}")
    except Exception as e:
        print(f"Error saving: {e}")


def extract_project_gee_features(project_geometry: Any, soil_depth: str = "0-30cm") -> Dict[str, Any]:
    """
    Extract GEE features for a project geometry.
    Returns {} if geometry is unavailable or GEE is not configured.
    """
    if not project_geometry:
        return {}

    try:
        from app.services.gee import analyze_polygon

        return analyze_polygon(project_geometry, soil_depth=soil_depth)
    except Exception as e:
        print(f"GEE enrichment failed: {e}")
        return {}


def process_batch():
    """Process all pending monitoring reports from Supabase verra_projects."""
    if not supabase:
        print("Supabase not configured.")
        return
    
    # Get projects and their monitoring report URLs.
    response = supabase.table("verra_projects").select("id, verra_id, pd_url, mr_urls, geometry").execute()
    projects = response.data
    
    print(f"Found {len(projects)} projects to process")
    
    for project in projects:
        mr_urls = project.get("mr_urls") or []
        if isinstance(mr_urls, str):
            try:
                mr_urls = json.loads(mr_urls)
            except Exception:
                mr_urls = []

        if not isinstance(mr_urls, list) or len(mr_urls) == 0:
            continue

        print(f"Project {project['verra_id']}: processing {len(mr_urls)} monitoring reports")

        for mr_url in mr_urls:
            # Skip if this report is already ingested.
            existing = (
                supabase.table("verra_monitoring_data")
                .select("id")
                .eq("project_id", project["id"])
                .eq("report_url", mr_url)
                .execute()
            )
            if existing.data:
                continue

            pdf_path = None
            try:
                pdf_path = download_pdf(mr_url)
                parsed = parse_monitoring_report(pdf_path)

                gee_features = extract_project_gee_features(project.get("geometry"))
                if gee_features:
                    parsed["gee_features"] = gee_features

                save_monitoring_data(project["id"], mr_url, parsed)
            except Exception as e:
                print(f"Failed report {mr_url}: {e}")
            finally:
                if pdf_path and os.path.exists(pdf_path):
                    os.unlink(pdf_path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Parse VM0047 Monitoring Report PDFs")
    parser.add_argument("--pdf", type=str, help="Path to a local PDF file")
    parser.add_argument("--url", type=str, help="URL to a PDF to download and parse")
    parser.add_argument("--batch", action="store_true", help="Process all pending from Supabase")
    parser.add_argument("--project-id", type=str, help="Supabase project UUID (for saving)")
    args = parser.parse_args()
    
    if args.pdf:
        result = parse_monitoring_report(args.pdf)
        print(f"\n--- Extracted Data ---")
        print(json.dumps(result, indent=2, default=str))
        
        if args.project_id:
            save_monitoring_data(args.project_id, args.pdf, result)
    
    elif args.url:
        print(f"Downloading PDF from {args.url}...")
        pdf_path = download_pdf(args.url)
        result = parse_monitoring_report(pdf_path)
        print(f"\n--- Extracted Data ---")
        print(json.dumps(result, indent=2, default=str))
        
        if args.project_id:
            save_monitoring_data(args.project_id, args.url, result)
        
        # Cleanup
        os.unlink(pdf_path)
    
    elif args.batch:
        process_batch()
    
    else:
        parser.print_help()
