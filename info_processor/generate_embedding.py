import sys, json, os, tqdm
sys.path.append("E:\Project\paperreader\code2")
import tool.qwen3_embedding_interface as qwen3_embedding_interface
from config import paper_meta, abstract_info, embedding_folder_name, abstract_info_file_name, paper_info_file_name, paper_info, paper_meta_file_name, all_embedding_name
from typing import List
from os import path
from xzxTool import op
import numpy as np
from dataclasses import asdict

def generate_embeddings(paper_metas: List[paper_meta], root_dir: str, embedding_model: qwen3_embedding_interface.Qwen3_Embedding_Interface, batch_size: int = 128, is_all: bool = True) -> List[abstract_info]:
    """
    根据一个paper_meta列表,
    1. 给列表里面的每一个元素都生成摘要对应的embedding,
    2. 并存储在embedding文件里面
    3. 并更新abstract_info.json文件里面的embedding文件的地址,
    4. 并更新abstract_info.json文件里面的has_embedding为True.
    5. 如果is_all为True,则将每一个embedding都stack起来,并且存储到root_dir称为all.pkl.
    """
    abstract_info_path = path.join(root_dir, abstract_info_file_name)
    embedding_folder_path = path.join(root_dir, embedding_folder_name)
    if not os.path.exists(embedding_folder_path):
        os.mkdir(embedding_folder_path)
    if os.path.exists(abstract_info_path):
        abstract_infos = json.load(open(abstract_info_path, "r", encoding="utf-8"))
    else:
        abstract_infos = []
    abstract_infos_dict = {item["id"]: item for item in abstract_infos}
    need_process_abstract = []
    need_process_paper_id = []
    for paper_meta in paper_metas:
        paper_id = paper_meta.id
        # 如果已经存在且has_embedding为True,或者则跳过
        if abstract_infos_dict.get(paper_id, None) is not None and abstract_infos_dict[paper_id].get("has_embedding", False):
            continue
        if paper_meta.has_abstract == False:
            # 如果没有摘要,则跳过
            continue
        else:
            need_process_abstract.append(paper_meta.abstract)
            need_process_paper_id.append(paper_id)
            
    #收集完成,开始批量处理
    if not need_process_abstract:
        if is_all:
            embeddings = []
            # if os.path.exists(path.join(root_dir, all_embedding_name)):
            #     #如果要求is_all,但是all.pkl已经存在,则跳过
            #     pass
            # else:
            for pkl_file in sorted(os.listdir(embedding_folder_path),key=lambda x: int(x.split('.')[0])):
                pkl_path = path.join(embedding_folder_path, pkl_file)
                if pkl_file.endswith(".pkl"):
                    embeddings.append(op.load(pkl_path))
            op.save(embeddings, path.join(root_dir, all_embedding_name))
        else:
            pass
        return abstract_infos

    # 批量生成embeddings,并设置batch_size为32
    embeddings = embedding_model.batch_encode(need_process_abstract, batch_size=batch_size)
    if is_all:
        embeddings = np.stack(embeddings, axis=0)
    for i, paper_id in tqdm.tqdm(enumerate(need_process_paper_id), total=len(need_process_paper_id)):
        # 1. 保存embedding文件
        # 处理文件名中的非法字符
        filename = str(i) + ".pkl"
        file_path = path.join(embedding_folder_path, filename)
        
        # 保存为pkl格式
        op.save(np.array(embeddings[i]), file_path)

        # 2. 更新abstract_info
        if paper_id in abstract_infos_dict:
            # 更新已有条目
            abstract_infos_dict[paper_id]["has_embedding"] = True
            abstract_infos_dict[paper_id]["abstract_embedding_path"] = file_path
            abstract_infos_dict[paper_id]["embedding_model"] = "Qwen3-0.6B-embedding"
            # 确保摘要内容也同步(可选)
            if not abstract_infos_dict[paper_id].get("abstract"):
                abstract_infos_dict[paper_id]["abstract"] = need_process_abstract[i]
        else:
            # 创建新条目
            new_info = {
                "id": paper_id,
                "abstract": need_process_abstract[i],
                "abstract_embedding_path": file_path,
                "embedding_model": "Qwen3-0.6B-embedding",
                "has_embedding": True
            }
            abstract_infos.append(new_info)
            # abstract_infos_dict[paper_id] = new_info # 如果后续还要用dict可以加,这里不需要

    # 3. 保存回abstract_info.json
    with open(abstract_info_path, "w", encoding='utf-8') as f:
        json.dump(abstract_infos, f, ensure_ascii=False, indent=4)
    return abstract_infos

def merge_meta_abstract(conference_dir: str):
    # 我们约定,在conference dir里面的paper_meta和abstract_info都是最新的,所以只需要覆盖原有文件即可.不需要考虑合并问题.
    paper_meta_path = path.join(conference_dir, paper_meta_file_name)
    abstract_info_path = path.join(conference_dir, abstract_info_file_name)
    if not path.exists(paper_meta_path):
        raise FileNotFoundError(f"paper_meta.json not found in {conference_dir}")
    if not path.exists(abstract_info_path):
        raise FileNotFoundError(f"abstract_info.json not found in {conference_dir}")
    #检查是不是所有有abstract的paper都已经有了embedding
    paper_metas_data = json.load(open(paper_meta_path, "r", encoding="utf-8"))
    paper_metas = [paper_meta(**item) for item in paper_metas_data]
    abstract_infos_data = json.load(open(abstract_info_path, "r", encoding="utf-8"))
    abstract_infos = [abstract_info(**item) for item in abstract_infos_data]
    
    # 将abstract_infos转换为字典以便快速查找
    abstract_infos_dict = {item.id: item for item in abstract_infos}
    
    for paper_item in paper_metas:
        paper_id = paper_item.id
        if paper_item.has_abstract == False:
            continue
        
        # 检查是否存在
        if paper_id not in abstract_infos_dict:
            raise ValueError(f"abstract_info.json not found info for paper {paper_id}")
            
        abstract_item = abstract_infos_dict[paper_id]
        if not abstract_item.has_embedding:
             raise ValueError(f"abstract_info.json not found embedding for paper {paper_id}")
             
    #检查完毕,开始merge 生成paper_info.json
    paper_info_path = path.join(conference_dir, paper_info_file_name)
    paper_infos = []
    for paper_item in paper_metas:
        paper_id = paper_item.id
        if paper_item.has_abstract == False:
            continue
        abstract_info_item = abstract_infos_dict[paper_id]
        paper_infos.append(paper_info(
            meta=paper_item,
            abstract=abstract_info_item
        ))
    # 3. 保存回paper_info.json
    with open(paper_info_path, "w", encoding='utf-8') as f:
        # 使用asdict将dataclass转换为字典,支持嵌套
        json.dump([asdict(item) for item in paper_infos], f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    # test 1 generate the embedding for existing conferences
    conference_folder = r"E:\Project\paperreader\database2\conference"
    embedding_model = qwen3_embedding_interface.Qwen3_Embedding_Interface()
    for conference in os.listdir(conference_folder):
        print(f"Processing conference: {conference}")
        conference_path = path.join(conference_folder, conference)
        if not path.isdir(conference_path):
            continue
        paper_meta_path = path.join(conference_path, "paper_meta.json")
        if not path.exists(paper_meta_path):
            continue
            
        paper_metas_data = json.load(open(paper_meta_path, "r", encoding="utf-8"))
        paper_metas = [paper_meta(**item) for item in paper_metas_data]
        
        generate_embeddings(
            paper_metas=paper_metas,
            root_dir=conference_path,
            embedding_model=embedding_model,
            batch_size=32
        )

    # test 2 merge the paper_meta.json and abstract_info.json to paper_info.json
    # conference_folder = r"E:\Project\paperreader\database2\conference"
    # for conference in os.listdir(conference_folder):
    #     print(f"Processing conference: {conference}")
    #     conference_path = path.join(conference_folder, conference)
    #     if not path.isdir(conference_path):
    #         continue
    #     try:
    #         merge_meta_abstract(conference_path)
    #     except Exception as e:
    #         print(f"Error processing {conference}: {e}")
    paper_metas_data = json.load(open(r"E:\Project\paperreader\database2\conference\usenix2024\paper_meta.json", "r", encoding="utf-8"))
    paper_metas = [paper_meta(**item) for item in paper_metas_data]
    generate_embeddings(
        paper_metas=paper_metas,
        root_dir=r"E:\Project\paperreader\database2\conference\usenix2024",
        embedding_model=embedding_model,
        batch_size=32
    )
    merge_meta_abstract(r"E:\Project\paperreader\database2\conference\usenix2024")
