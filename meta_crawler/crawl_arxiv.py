import sys
sys.path.append("E:\Project\paperreader\code2")
import os
import json
import arxiv
from datetime import datetime
from typing import List, Dict
from config import paper_meta, arxiv_folder

#常见的分类:
def crawl_arxiv_paper_meta_date(start_date: str, end_date: str, categories: List[str] = ["cs.AI", "cs.LG","cs.CL", "cs.CV", "cs.CR"]) -> List[paper_meta]:
    """
    从arXiv上爬取指定日期范围内的论文元数据.
    start_date: 字符串格式 "YYYY-MM-DD"
    end_date: 字符串格式 "YYYY-MM-DD"
    categories: arXiv 分类列表, 例如 ["cs.CL", "cs.LG"]. 默认为 None (不限制分类).
    """
    if categories is None:
        categories = []

    print(f"Start crawling arXiv from {start_date} to {end_date} with categories: {categories}...")
    
    # 转换日期格式为 arXiv API 需要的格式 YYYYMMDDHHMM
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        print(f"Date format error: {e}. Please use YYYY-MM-DD.")
        return []

    # 构造查询时间范围
    # 注意: arXiv API 的时间查询是基于提交时间的
    start_str = start.strftime("%Y%m%d0000")
    end_str = end.strftime("%Y%m%d2359")
    
    # 基础时间查询: submittedDate:[start TO end]
    time_query = f"submittedDate:[{start_str} TO {end_str}]"
    
    # 构造分类查询
    if categories:
        # cat:cs.CL OR cat:cs.LG
        cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
        # (cat:cs.CL OR cat:cs.LG) AND submittedDate:[...]
        query = f"({cat_query}) AND {time_query}"
    else:
        query = time_query
    
    # 配置 Client
    client = arxiv.Client(
        page_size=100,
        delay_seconds=3.0,
        num_retries=3
    )
    
    search = arxiv.Search(
        query=query,
        max_results=None, # 获取该范围内所有结果
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Ascending
    )
    
    paper_metas = []
    
    try:
        # 获取结果生成器
        results = client.results(search)
        
        for result in results:
            # 提取 ArXiv ID (short id, e.g., 2101.12345)
            # get_short_id() 包含版本号吗? 通常是 2101.12345v1
            # 我们通常希望去掉版本号，但在元数据中保留原始 ID 也可以
            paper_id = "arxiv_"+result.title.replace(" ", "_")
            
            # 处理作者列表
            authors = [author.name for author in result.authors]
            
            # 处理发布日期
            published_date = result.published.strftime("%Y-%m-%d")
            published_year = str(result.published.year)
            
            # 构建 paper_meta 对象
            meta = paper_meta(
                id=paper_id,
                conference="arxiv",
                year=published_year,
                date=published_date,
                title=result.title.replace("\n", " "),
                authors=authors,
                abstract=result.summary.replace("\n", " "),
                institution="", # arXiv API 不提供机构信息
                pdf_url=result.pdf_url,
                has_abstract=True,
                has_institution=False,
                has_pdf_url=True,
                has_search_on_arxiv=True
            )
            
            paper_metas.append(meta)
            # 简单的进度打印
            if len(paper_metas) % 50 == 0:
                print(f"Crawled {len(paper_metas)} papers...")
                
    except Exception as e:
        print(f"Error occurred while crawling arXiv: {e}")
    
    print(f"Finished crawling. Total papers: {len(paper_metas)}")
    return paper_metas

def save_paper_meta(paper_meta_list: List[paper_meta]):
    """
    保存论文元数据到数据库.
    将论文按日期分组保存到对应的文件夹中.
    """
    if not paper_meta_list:
        print("No papers to save.")
        return

    # 按日期分组
    papers_by_date: Dict[str, List[paper_meta]] = {}
    for meta in paper_meta_list:
        date = meta.date
        if date not in papers_by_date:
            papers_by_date[date] = []
        papers_by_date[date].append(meta)
    
    for date, metas in papers_by_date.items():
        # 确保目录存在
        save_folder = os.path.join(arxiv_folder, date)
        if not os.path.exists(save_folder):
            try:
                os.makedirs(save_folder)
            except OSError as e:
                print(f"Failed to create directory {save_folder}: {e}")
                continue
            
        save_path = os.path.join(save_folder, "paper_meta.json")
        
        exist_paper_meta = []
        
        # 读取现有数据
        if os.path.exists(save_path):
            try:
                with open(save_path, "r", encoding="utf-8") as f:
                    exist_paper_meta = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading existing file {save_path}: {e}. Starting fresh.")
                exist_paper_meta = []
        
        # 去重: 使用 set 存储已存在的 ID
        existing_ids = {p.get('id') for p in exist_paper_meta if isinstance(p, dict) and 'id' in p}
        
        new_entries = []
        for meta in metas:
            if meta.id not in existing_ids:
                new_entries.append(meta.__dict__)
                existing_ids.add(meta.id)
        
        if new_entries:
            # 追加新数据
            exist_paper_meta.extend(new_entries)
            
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(exist_paper_meta, f, ensure_ascii=False, indent=4)
                print(f"Date {date}: Saved {len(new_entries)} new papers. Total: {len(exist_paper_meta)}")
            except IOError as e:
                print(f"Error writing to file {save_path}: {e}")
        else:
            print(f"Date {date}: No new papers to save (all duplicates).")

if __name__ == "__main__":
    paper_metas = crawl_arxiv_paper_meta_date("2026-02-04", "2026-02-05")
    save_paper_meta(paper_metas)
