#定义了一些数据结构等等.
from dataclasses import dataclass
from os import path
from typing import Optional, List

@dataclass
class paper_meta:
    id: str #conference_title
    conference: str #可以是具体的会议名称,也可以是arxiv.
    year: str 
    date: str #具体某一天,只有arxiv来源的paper才有这个特点.
    title: str
    authors: list[str]
    abstract: str
    institution: str #作者所属的机构.
    pdf_url: str #可以是arxiv的url,也可以是具体的pdf url.
    has_abstract: bool #是否有摘要.
    has_institution: bool #是否有机构信息.
    has_pdf_url: bool #是否有pdf的url.
    has_search_on_arxiv: bool #是否在arxiv上搜索过了.无论是否搜索成功,只要有过搜索尝试,就算是搜索过了
    session_path: Optional[str] = None #与这篇paper相关的chat session的存储路径.
    has_session: bool = False #是否有chat session.

@dataclass
class abstract_info:#以paper_meta为原料,整理出abstract的信息. 
    # 实验/思考了一下,本地做摘要总结和翻译实在是太慢了,所以就只弄一个embedding得了.
    id: str #paper id.
    abstract: str #摘要.
    # abstract_chinese: str #摘要的中文版本.
    # abstract_summary: str #摘要的中文总结.
    abstract_embedding_path: str #摘要的embedding路径.
    # summary_prompt: str #用于总结摘要的prompt. 
    # summary_model: str #用于总结摘要的大模型名称.
    # translate_model: str #用于翻译摘要的模型名称.
    embedding_model: str #用于生成摘要embedding的模型名称.
    has_embedding: bool #是否有摘要embedding.
    # has_summary: bool #是否有摘要总结.
    # has_translation: bool #是否有摘要翻译.

@dataclass
class chat_turn:
    paper_id: str #具体对哪篇paper进行的chat.
    user_content: str
    model_response: str
    cost: float = 0.0
    time_cost: float = 0.0 #记录花费的时间.
    time_stamp: str = "" #记录时间戳.
    model_name: str = "" #具体使用的模型名称.

@dataclass
class chat_session:
    session_id: str #每个session的id.
    paper_id: str #具体对哪篇paper进行的chat.
    turns: list[chat_turn]
    model_name: str #具体使用的模型名称.
    cache_name: str #缓存的名称.
    cache_display_name: str #缓存的显示名称.
    pdf_local_path: str #用来解读的pdf的本地路径.

@dataclass
class paper_info:#包含了meta info的更多的信息,主要是添加了预处理的一些信息.
    meta: paper_meta
    abstract: abstract_info #摘要的相关信息.

#model_name_path_pair
model_name_path_pair = {
    "Qwen3-0.6B": r"E:\Project\paperreader\resource\Qwen3-0.6B",
    "Qwen3-VL-2B": r"e:\Project\paperreader\resource\Qwen3-VL-2B-Instruct",
    "opus-mt-en-zh": r"e:\Project\paperreader\resource\opus-mt-en-zh",
    "glm-4.6-flash": "online",
    "gemini-3.5-flash": "online",
    "Qwen3-0.6B-embedding": r"E:\Project\paperreader\resource\Qwen3-Embedding-0.6B",
}

#database address related
database_root = r"e:\Project\paperreader\database2"
arxiv_folder = path.join(database_root, "arxiv")
conference_folder = path.join(database_root, "conference")
embedding_folder_name = "embedding"
paper_meta_file_name = "paper_meta.json"
abstract_info_file_name = "abstract_info.json"
paper_info_file_name = "paper_info.json"
all_embedding_name = "all.pkl"
private_root = path.join(database_root, "private")
session_history_folder = path.join(private_root, "session_history")
downloaded_pdf_folder = path.join(private_root, "downloaded_pdf")


#resource address
resource_root = r"e:\Project\paperreader\resource"
paper_list = path.join(resource_root, "paperlists")
paper_list_git = "https://github.com/papercopilot/paperlists"
awesome_ml_sp_papers = path.join(resource_root, "Awesome-ML-SP-Papers")
awesome_ml_sp_papers_git = "https://github.com/gnipping/Awesome-ML-SP-Papers"