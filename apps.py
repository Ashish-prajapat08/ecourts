import streamlit as st
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta
import re

# ============ PAGE CONFIG ============
st.set_page_config(page_title="Delhi Courts Cause List Downloader", layout="wide")
st.title("Delhi District Courts - Cause List Downloader")
st.markdown("Download all judges' cause lists for selected court complex and date")

# ============ SETUP ============
os.makedirs("downloaded_pdfs", exist_ok=True)

DELHI_BASE_URL = "https://newdelhi.dcourts.gov.in"
DELHI_CAUSELIST_URL = DELHI_BASE_URL + "/cause-list-%e2%81%84-daily-board/"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Delhi Court Complexes (Manually added based on Delhi courts structure)
DELHI_COURTS = {
    "Patiala House Court Complex": "patiala-house",
    "Tis Hazari Court": "tis-hazari",
    "Karkardooma Court": "karkardooma",
    "Delhi High Court": "dhc",
    "Special CBI Courts": "cbi-courts"
}

# ============ FUNCTIONS ============

def safe_request(url, timeout=10):
    """Safe HTTP request"""
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response
    except:
        return None

def get_court_complex_name_from_url(url):
    """Extract court complex name from URL"""
    try:
        response = safe_request(url)
        if not response:
            return None
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('title')
        if title:
            return title.get_text(strip=True)
        return None
    except:
        return None

def get_pdf_links_for_court_and_date(date_obj, court_complex=None):
    """Fetch all PDF links for selected court complex and date"""
    try:
        response = safe_request(DELHI_CAUSELIST_URL)
        if not response:
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        pdf_links = []
        
        # Find all PDF links
        for link in soup.find_all('a', href=re.compile(r'\.pdf', re.I)):
            href = link.get('href', '').strip()
            if not href:
                continue
            
            # Make absolute URL
            if href.startswith('http'):
                full_url = href
            else:
                full_url = DELHI_BASE_URL + href if href.startswith('/') else DELHI_BASE_URL + '/' + href
            
            link_text = link.get_text(strip=True)
            if link_text:
                # Filter by court complex if specified
                if court_complex and court_complex.lower() not in link_text.lower():
                    continue
                
                pdf_links.append({
                    'name': link_text,
                    'url': full_url,
                    'judge': link_text  # Assuming link text contains judge/establishment name
                })
        
        return pdf_links
    
    except Exception as e:
        st.error(f"Error fetching PDFs: {str(e)}")
        return []

def download_pdf(pdf_url, filename):
    """Download single PDF"""
    try:
        response = safe_request(pdf_url, timeout=20)
        if not response:
            return None
        
        if response.status_code == 200 and len(response.content) > 1000:
            filepath = os.path.join("downloaded_pdfs", filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return filepath
        return None
    except:
        return None

def download_all_judges_pdfs(date_obj, court_complex):
    """Download cause lists for ALL judges in selected court complex"""
    try:
        pdf_links = get_pdf_links_for_court_and_date(date_obj, court_complex)
        
        if not pdf_links:
            return []
        
        downloaded_files = []
        date_str = date_obj.strftime("%d-%m-%Y")
        
        st.info(f"Found {len(pdf_links)} judge(s) for {court_complex}")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, pdf_link in enumerate(pdf_links):
            judge_name = pdf_link['judge']
            status_text.text(f"Downloading {idx + 1}/{len(pdf_links)}: {judge_name[:50]}")
            
            # Create safe filename
            safe_judge = re.sub(r'[^\w\s-]', '', judge_name)[:40]
            filename = f"CauseList_{court_complex}_{safe_judge}_{date_str}.pdf"
            
            # Download
            filepath = download_pdf(pdf_link['url'], filename)
            
            if filepath:
                downloaded_files.append({
                    'judge': judge_name,
                    'filepath': filepath,
                    'filename': filename
                })
                st.success(f"Downloaded: {filename}")
            else:
                st.warning(f"Failed to download: {judge_name}")
            
            progress_bar.progress((idx + 1) / len(pdf_links))
        
        status_text.empty()
        progress_bar.empty()
        
        return downloaded_files
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return []

# ============ UI ============

st.subheader("Form")

col1, col2 = st.columns([2, 1])

with col1:
    st.write("Step 1: Select Court Complex")
    selected_court = st.selectbox(
        "Court Complex:",
        list(DELHI_COURTS.keys()),
        key="court_select",
        index=0
    )
    
    st.write("Step 2: Select Date")
    selected_date = st.date_input(
        "Date:",
        value=datetime.now(),
        min_value=datetime.now() - timedelta(days=30),
        max_value=datetime.now() + timedelta(days=30),
        key="date_select"
    )
    
    st.write(f"**Selected:** {selected_court} | {selected_date.strftime('%d-%m-%Y')}")
    
    # Main download button
    if st.button("Download All Judges' Cause Lists", type="primary", use_container_width=True):
        with st.spinner(f"Fetching cause lists for {selected_court}..."):
            downloaded = download_all_judges_pdfs(selected_date, selected_court)
            
            if downloaded:
                st.success(f"Downloaded {len(downloaded)} PDF(s) successfully!")
                
                st.subheader("Downloaded Files:")
                for file_info in downloaded:
                    col_name, col_btn = st.columns([3, 1])
                    with col_name:
                        st.write(f"Judge: {file_info['judge']}")
                    with col_btn:
                        with open(file_info['filepath'], 'rb') as f:
                            st.download_button(
                                label="Download",
                                data=f.read(),
                                file_name=file_info['filename'],
                                mime="application/pdf",
                                key=file_info['filepath']
                            )
            else:
                st.error(f"No cause lists found for {selected_court} on {selected_date.strftime('%d-%m-%Y')}")

with col2:
    st.subheader("Downloads")
    try:
        files = os.listdir("downloaded_pdfs")
        if files:
            st.metric("Files Downloaded", len(files))
            with st.expander("Recent Files"):
                for file in sorted(files, reverse=True)[:8]:
                    filepath = os.path.join("downloaded_pdfs", file)
                    size = os.path.getsize(filepath) / 1024
                    st.write(f"📄 {file}\n({size:.1f} KB)")
        else:
            st.info("No downloads yet")
    except:
        st.info("Ready to download")

# ============ INFO ============
st.markdown("---")
st.markdown("""
### How to Use:
1. **Select Court Complex** from dropdown (Patiala House, Tis Hazari, etc.)
2. **Select Date** (past 30 days or future 30 days)
3. **Click "Download All Judges' Cause Lists"**
4. All judges' cause lists will download as separate PDFs

### What Happens:
- Fetches ALL judges' cause lists for selected court complex
- Downloads each as individual PDF file
- Files saved to `downloaded_pdfs/` folder
- Auto-named with court, judge, and date

### Notes:
- One click = All judges' cause lists downloaded
- Date format: DD-MM-YYYY
- Each PDF is for different judge/bench
- Files auto-save locally
""")