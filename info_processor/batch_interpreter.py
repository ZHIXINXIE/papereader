import sys, json, os, tqdm
sys.path.append("E:\Project\paperreader\code2")
from tool.gemini_interface import Gemini_interface
from config import paper_info

def batch_interpret(paper_info_list: List[paper_info]) -> List[str]:
    """
    Interpret paper_info_list using Gemini_interface.
    返回值是一个list,每个元素都是一个history的地址.
    """