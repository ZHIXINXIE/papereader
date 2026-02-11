import sys
sys.path.append("E:\Project\paperreader\code2")
import os
import json
import re
import glob
import hashlib
import arxiv
import shutil
import subprocess
from typing import List, Dict
from tqdm import tqdm
from config import paper_meta, conference_folder, paper_list, paper_list_git, awesome_ml_sp_papers, awesome_ml_sp_papers_git
import time

def crawl_conference_paper_meta_date_paperlist(is_refresh : bool = False, year_threshold : int = 2023) -> List[paper_meta]:
    '''
    由于conference的paper list是公开而且较为固定的,所以没有太多可配置参数.但是由于本地有两个来源,一个是paperlist,一个是awesome-ml-sp-papers
    所以这里直接从这两个来源中读取paper meta.这里呢,只考虑从paperlist这一个当中汲取思路.
    '''
    if is_refresh and os.path.exists(paper_list):
        print(f"Removing existing {paper_list}...")
        def on_rm_error(func, path, exc_info):
            import stat
            os.chmod(path, stat.S_IWRITE)
            func(path)
        shutil.rmtree(paper_list, onerror=on_rm_error)

    if not os.path.exists(paper_list):
        # Clone from git
        print(f"Cloning paperlists from {paper_list_git} to {paper_list}...")
        try:
            subprocess.run(["git", "clone", paper_list_git, paper_list], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to clone paperlists: {e}")
            return []
            
    all_papers = []
    
    print("Crawling papers from paperlists...")
    # Walk through the directory
    for root, dirs, files in os.walk(paper_list):
        for file in files:
            if file.endswith(".json") and file != "croissant.json":
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # Infer conference and year from filename
                    filename_no_ext = os.path.splitext(file)[0]
                    match = re.match(r"([a-zA-Z]+)(\d{4})", filename_no_ext)
                    if match:
                        conf_name = match.group(1)
                        year = match.group(2)
                    else:
                        conf_name = os.path.basename(root)
                        year = "Unknown"
                    if int(year) < year_threshold:
                        continue
                    # paperlist format check: should be a list
                    if not isinstance(data, list):
                        continue

                    for item in data:
                        title = item.get("title", "")
                        if not title: continue
                        
                        # Filter out rejected or withdrawn papers (specifically for ICLR and similar)
                        status = item.get("status", "")
                        if status and ("Reject" in status or "Withdraw" in status):
                            continue
                        
                        # Generate ID: prefix with conf_year to avoid collision
                        # Some items have 'id' field, but it might not be unique globally
                        paper_id = f"{conf_name}_{title}"
                        
                        authors_str = item.get("author", "")
                        authors = [a.strip() for a in authors_str.split(";")] if authors_str else []
                        
                        abstract = item.get("abstract", "")
                        institution = item.get("aff", "") 
                        pdf_url = item.get("pdf", "")
                                
                        meta = paper_meta(
                            id=paper_id,
                            conference=conf_name,
                            year=year,
                            date="", 
                            title=title,
                            authors=authors,
                            abstract=abstract,
                            institution=institution,
                            has_search_on_arxiv=False,
                            pdf_url=pdf_url,
                            has_abstract=bool(abstract),
                            has_institution=bool(institution),
                            has_pdf_url=bool(pdf_url)
                        )
                        all_papers.append(meta)
                        
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    
    print(f"Found {len(all_papers)} papers from paperlists.")
    return all_papers

def crawl_conference_paper_meta_date_awesomemlsppaper(is_refresh : bool = False, year_threshold : int = 2023) -> List[paper_meta]:
    '''
    实现从awesome-ml-sp-papers中读取paper meta的逻辑.
    '''
    import shutil
    import subprocess

    readme_path = os.path.join(awesome_ml_sp_papers, "README.md")
    
    if (is_refresh or not os.path.exists(readme_path)) and os.path.exists(awesome_ml_sp_papers):
        print(f"Removing existing {awesome_ml_sp_papers}...")
        def on_rm_error(func, path, exc_info):
            import stat
            os.chmod(path, stat.S_IWRITE)
            func(path)
        shutil.rmtree(awesome_ml_sp_papers, onerror=on_rm_error)
        
    if not os.path.exists(awesome_ml_sp_papers):
        # Clone from git
        print(f"Cloning Awesome-ML-SP-Papers from {awesome_ml_sp_papers_git} to {awesome_ml_sp_papers}...")
        try:
            subprocess.run(["git", "clone", awesome_ml_sp_papers_git, awesome_ml_sp_papers], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to clone Awesome-ML-SP-Papers: {e}")
            return []
        
    papers = []
    print("Crawling papers from Awesome-ML-SP-Papers...")
    
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Regex for: 9. **Title**. Conference Year. `Tags` [[pdf](link)]
        pattern = re.compile(r"^\d+\.\s+\*\*(.*?)\*\*\.\s+(.*?)\.\s+(`.*?`)?\s*(\[\[pdf\]\((.*?)\)\].*)?$")
        
        for line in lines:
            line = line.strip()
            match = pattern.match(line)
            if match:
                title = match.group(1)
                conf_year_str = match.group(2)
                # tags = match.group(3)
                pdf_link = match.group(5) if match.group(5) else ""
                
                # Extract year
                year_match = re.search(r"(\d{4})", conf_year_str)
                year = year_match.group(1) if year_match else "Unknown"
                conf_name = conf_year_str.replace(year, "").strip()
                
                # Normalize conference names
                lower_conf = conf_name.lower()
                if "s&p" in lower_conf or ("ieee" in lower_conf and "sp" in lower_conf):
                    conf_name = "sp"
                elif "ccs" in lower_conf:
                    conf_name = "ccs"
                elif "ndss" in lower_conf:
                    conf_name = "ndss"
                elif "usenix" in lower_conf:
                    conf_name = "usenix"
                
                if int(year) < year_threshold:
                    continue
                if not conf_name:
                    conf_name = "security_conf" # Default fallback
                
                paper_id = f"{conf_name}_{title}"
                
                meta = paper_meta(
                    id=paper_id,
                    conference=conf_name,
                    year=year,
                    date="",
                    title=title,
                    authors=[], # Not available in README
                    abstract="",
                    institution="",
                    pdf_url=pdf_link,
                    has_abstract=False,
                    has_institution=False,
                    has_pdf_url=bool(pdf_link),
                    has_search_on_arxiv=False
                )
                papers.append(meta)
    except Exception as e:
        print(f"Error processing Awesome-ML-SP-Papers: {e}")
            
    print(f"Found {len(papers)} papers from Awesome-ML-SP-Papers.")
    return papers

def save_paper_meta(paper_metas : List[paper_meta]) -> None:
    '''
    实现将paper meta保存到文件中的逻辑.
    '''
    if not paper_metas:
        return

    print("Saving papers...")
    # Group by conference + year
    grouped = {}
    for p in paper_metas:
        # Normalize keys
        c_name = p.conference.lower().replace(" ", "")
        y_name = p.year
        key = f"{c_name}{y_name}"
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(p)
        
    for key, papers in grouped.items():
        if not papers: continue
        
        # Folder name: conference + year (e.g., cvpr2024)
        folder_name = key
        save_folder = os.path.join(conference_folder, folder_name)
        
        if not os.path.exists(save_folder):
            try:
                os.makedirs(save_folder, exist_ok=True)
            except OSError:
                continue
            
        save_path = os.path.join(save_folder, "paper_meta.json")
        
        # Load existing
        existing = []
        if os.path.exists(save_path):
            try:
                with open(save_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except:
                existing = []
                
        # Deduplicate and Update
        existing_map = {p.get('id'): p for p in existing if isinstance(p, dict) and p.get('id')}      
        for p in papers:
            existing_map[p.id] = p.__dict__
        
        # Convert map back to list
        final_list = list(existing_map.values())
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(final_list, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving to {save_path}: {e}")

def make_up(paper_metas : List[paper_meta]) -> List[paper_meta]:
    '''
    实现将paper meta填充完整的逻辑.
    '''
    to_process = [p for p in paper_metas if not p.has_abstract or not p.has_pdf_url]
    if not to_process:
        print("No papers need makeup.")
        return paper_metas

    print(f"Starting make_up for {len(to_process)} papers (fetching from arXiv)...")    
    # Using a client with minimal delay, we will handle delays manually in the loop
    client = arxiv.Client(
        page_size=1,
        delay_seconds=0.1, # Set small base delay, we control it manually
        num_retries=1      # We handle retries manually
    )
    
    for meta in tqdm(to_process):
        if meta.has_search_on_arxiv:
            continue
        retries = 3
       
        while retries > 0:
            try:
                # Clean title: remove newlines, extra spaces
                clean_title = meta.title.replace("\n", " ").strip()
                search_query = f'ti:"{clean_title}"'
                
                search = arxiv.Search(
                    query=search_query,
                    max_results=1,
                    sort_by=arxiv.SortCriterion.Relevance
                )
                
                results = list(client.results(search))
                meta.has_search_on_arxiv = True
                # If we get here, request was successful
                time.sleep(0.1) # Normal delay
                
                if not results:
                    break
                    
                result = results[0]
                
                # Simple title matching verification
                def simplify(s):
                    return re.sub(r'[^a-zA-Z0-9]', '', s.lower())
                    
                if simplify(result.title) == simplify(meta.title):
                    if not meta.has_abstract and result.summary:
                        meta.abstract = result.summary.replace("\n", " ")
                        meta.has_abstract = True
                        
                    if not meta.has_pdf_url and result.pdf_url:
                        meta.pdf_url = result.pdf_url
                        meta.has_pdf_url = True
                    
                    if not meta.authors and result.authors:
                        meta.authors = [a.name for a in result.authors]                
                break # Success, break retry loop
                
            except Exception as e:
                retries -= 1
                if retries > 0:
                    time.sleep(2.0) # Error delay
                else:
                    print(f"Failed after retries: {meta.title} - {e}")
                    pass
    
    print("Make up finished.")
    return paper_metas

if __name__ == "__main__":
    # test 1 读取并解析所有的github里面的conference的信息
    paper_metas = crawl_conference_paper_meta_date_paperlist(is_refresh=False, year_threshold=2024)
    paper_metas += crawl_conference_paper_meta_date_awesomemlsppaper(is_refresh=False, year_threshold=2024)
    save_paper_meta(paper_metas)

    # test 2 填充缺失的abstract和pdf url
    for conference in os.listdir(conference_folder):
        print(f"Processing {conference}...")
        conference_path = os.path.join(conference_folder, conference)
        if not os.path.isdir(conference_path): continue
        
        paper_meta_path = os.path.join(conference_path, "paper_meta.json")
        if not os.path.exists(paper_meta_path): continue
        
        with open(paper_meta_path, 'r', encoding='utf-8') as f:
            paper_metas = json.load(f)
            paper_metas = [paper_meta(**p) for p in paper_metas]
            paper_metas = make_up(paper_metas)
            save_paper_meta(paper_metas)
