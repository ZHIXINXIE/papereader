import sys
sys.path.append("E:\Project\paperreader\code2")
from config import paper_info, paper_info_file_name, conference_folder, paper_meta, abstract_info, all_embedding_name
import tool.qwen3_embedding_interface as qwen3_embedding_interface
from os import path
from xzxTool import op
from typing import List, Optional
import numpy as np
import json

def _deserialize_paper_info(item: dict) -> Optional[paper_info]:
    """Helper to safely deserialize nested paper_info"""
    try:
        meta_obj = paper_meta(**item['meta'])
        abstract_obj = abstract_info(**item['abstract'])
        return paper_info(meta=meta_obj, abstract=abstract_obj)
    except Exception as e:
        print(f"Error deserializing paper info: {e}")
        return None

def collect_search_doc_conference(conference_list: List[str]) -> (List[np.ndarray], List[paper_info]):
    """
    根据conference_list,收集所有conference对应的embedding和paper info
    """
    paper_info_list = []
    embedding_list = []
    for conference in conference_list:
        conference_path = path.join(conference_folder, conference)
        if not path.exists(conference_path):
            raise FileNotFoundError(f"Warning: {conference_path} does not exist. Skipping.")
        paper_info_file_path = path.join(conference_path, paper_info_file_name)
        if not path.exists(paper_info_file_path):
            raise FileNotFoundError(f"Warning: {paper_info_file_path} does not exist. Skipping.")
        with open(paper_info_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                p_info = _deserialize_paper_info(item)
                if p_info:
                    paper_info_list.append(p_info)
        
        embedding_path = path.join(conference_path, all_embedding_name)
        if path.exists(embedding_path):
            embedding_list+=op.load(embedding_path)
        else:
            print(f"Warning: Embedding file {embedding_path} not found.")
            
    return paper_info_list, embedding_list

def collect_search_doc_paperinfopathlist(paper_info_path_list: List[str]) -> (List[np.ndarray], List[paper_info]):
    """
    根据paper_info_path_list,收集所有paper info和embedding
    """
    paper_info_list_all = []
    embedding_list = []
    for paper_info_path in paper_info_path_list:            
        try:
            with open(paper_info_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data:
                # Deserialize nested dataclasses
                p_info = _deserialize_paper_info(item)
                if not p_info:
                    continue 
                try:
                    emb_path = p_info.abstract.abstract_embedding_path
                    # Load embedding
                    if path.exists(emb_path):
                        paper_embedding = op.load(emb_path)
                        embedding_list.append(paper_embedding)
                        paper_info_list_all.append(p_info)
                except Exception as e:
                    print(f"Error processing embedding for {p_info.meta.id if p_info else 'unknown'}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error reading {conference_paper_info_path}: {e}")
            continue

    if not embedding_list:
        return [], []
    return paper_info_list_all, embedding_list

def search(query: str, embedding_model: qwen3_embedding_interface.Qwen3_Embedding_Interface, instruction:str = "please search the most related paper to the query:", top_k: int = 10, paper_info_list: List[paper_info] = None, embedding_list: List[np.ndarray] = None) -> List[paper_info]:
    """
    根据instruction和query,在root_dir下的embedding文件夹中,搜索top_k个最相似的论文信息
    """
    full_query = embedding_model.get_detailed_instruct(instruction, query)
    query_embedding_list = embedding_model.batch_encode([full_query], batch_size=1)
    if not query_embedding_list:
        return []
    query_embedding = np.array(query_embedding_list[0])
    if not embedding_list or not paper_info_list:
        return []
    embeddings_matrix = np.stack(embedding_list)
    # Normalize query embedding
    norm_query = np.linalg.norm(query_embedding)
    if norm_query > 0:
        query_embedding = query_embedding / norm_query
    # Normalize paper embeddings
    norm_embeddings = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
    # Avoid division by zero
    norm_embeddings[norm_embeddings == 0] = 1
    embeddings_matrix = embeddings_matrix / norm_embeddings
    # Cosine similarity: (N, D) @ (D,) -> (N,)
    similarity_list = embeddings_matrix @ query_embedding
    # Get top K indices
    # argsort returns indices that sort the array (ascending), so we take from the end
    sorted_indices = np.argsort(similarity_list)[::-1]
    top_k_indices = sorted_indices[:top_k]
    top_k_paper_info = [paper_info_list[i] for i in top_k_indices]
    return top_k_paper_info

if __name__ == "__main__":
    query = "Give me a paper about large language security"
    embedding_model = qwen3_embedding_interface.Qwen3_Embedding_Interface()
    conferences = ["iclr2025","nips2025"]
    paper_info_path_list = [path.join(conference_folder, conference, paper_info_file_name) for conference in conferences]
    # test 1
    # print("======== test 1 ========")
    paper_info_list1, embedding_list1 = collect_search_doc_paperinfopathlist(paper_info_path_list)
    top_k_paper_info = search(query, embedding_model, paper_info_list=paper_info_list1, embedding_list=embedding_list1)
    print("the result of test 1")
    for p_info in top_k_paper_info:
        print(p_info.meta.title)
    # test 2
    print("======== test 2 ========")
    paper_info_list2, embedding_list2 = collect_search_doc_conference(conferences)
    top_k_paper_info = search(query, embedding_model, paper_info_list=paper_info_list2, embedding_list=embedding_list2)
    print("the result of test 2")
    for p_info in top_k_paper_info:
        print(p_info.meta.title)
    