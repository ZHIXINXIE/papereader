import sys, json, os, tqdm, glob
sys.path.append("E:\Project\paperreader\code2")
from tool.gemini_interface import Gemini_interface
from config import paper_info, chat_turn, chat_session
import time
from typing import List, Dict, Union, Any, Optional
import requests

class session_manager:
    def __init__(self, model_name: str = "gemini-3-flash-preview", max_tokens: int = 4096) -> None:
        self.model_name = model_name
        self.gemini_interface = Gemini_interface(model_name=model_name)
    
    def start_new_session(self, paper_id: str, model_name: str, pdf_path: str) -> chat_session:
        """
        开始一个新的chat session.
        """
        if not paper_id or not model_name or not pdf_path:
            raise ValueError("paper_id, model_name, and pdf_path are required")
        return chat_session(
            paper_id=paper_id,
            session_id=time.strftime("%Y%m%d%H%M%S", time.localtime())+f"_{paper_id}",
            turns=[],
            cache_name = "",
            cache_display_name = "",
            model_name = model_name,
            pdf_local_path= pdf_path
        )
    
    def start_chat_turn(self, paper_id: str, model_name: str) -> chat_turn:
        """
        开始一个新的chat turn.
        """
        return chat_turn(
            paper_id=paper_id,
            user_content="",
            model_response="",
            cost=0.0,
            time_cost=0.0,
            time_stamp=time.strftime("%Y%m%d%H%M%S", time.localtime()),
            model_name=model_name,
        )

    def history_to_sessions(self, history_data: Dict, paper_id: str) -> chat_session:
        """
        将gemini的history数据转换为chat_session.
        支持 history dict (包含 'cache'/'turns').
        """
        if not isinstance(history_data, dict):
            raise ValueError("History data should be a dict")
            
        cache_info = history_data.get("cache", {})
        turns_data = history_data.get("turns", [])
        
        # 尝试从cache_info推断一些信息
        cache_name = cache_info.get("cache_name", "") if cache_info else ""
        cache_display_name = cache_info.get("display_name", "") if cache_info else ""

        chat_turns = []
        
        for turn_item in turns_data:
            user_data = turn_item.get("user", {})
            model_data = turn_item.get("model", {})
            meta_data = turn_item.get("meta", {})
            
            # Extract User Content
            user_content = ""
            for part in user_data.get("parts", []):
                if isinstance(part, str):
                    user_content += part
                elif isinstance(part, dict) and "text" in part:
                    user_content += part["text"]
            
            # Extract Model Response
            model_response = ""
            for part in model_data.get("parts", []):
                if isinstance(part, str):
                    model_response += part
                elif isinstance(part, dict) and "text" in part:
                    model_response += part["text"]
            
            # Extract Meta
            cost = meta_data.get("cost", 0.0)
            time_cost = meta_data.get("time_cost", 0.0)
            timestamp = meta_data.get("timestamp", "")
            model_name = meta_data.get("model_name", self.model_name)
            
            turn = chat_turn(
                paper_id=paper_id,
                user_content=user_content,
                model_response=model_response,
                cost=cost,
                time_cost=time_cost,
                time_stamp=timestamp,
                model_name=model_name
            )
            chat_turns.append(turn)
            
        return chat_session(
            session_id=time.strftime("%Y%m%d%H%M%S", time.localtime()) + f"_{paper_id}",
            paper_id=paper_id,
            turns=chat_turns,
            model_name=self.model_name,
            cache_name=cache_name,
            cache_display_name=cache_display_name,
            pdf_local_path=cache_display_name
        )

    def sessions_to_history(self, session: chat_session) -> Dict:
        """
        将chat_session转换为gemini的history dict.
        包含 'cache' 和 'turns' 两部分信息.
        """
        history_turns = []
        for turn in session.turns:
            user_msg = {'role': 'user', 'parts': [{'text': turn.user_content}]}
            model_msg = {'role': 'model', 'parts': [{'text': turn.model_response}]}
            
            meta = {
                "timestamp": turn.time_stamp,
                "cost": turn.cost,
                "time_cost": turn.time_cost,
                "model_name": turn.model_name
            }
            
            history_turns.append({
                "user": user_msg,
                "model": model_msg,
                "meta": meta
            })
        
        # 构建cache信息
        cache_info = {
            "cache_name": session.cache_name,
            "display_name": session.cache_display_name
        }
        
        return {
            "cache": cache_info,
            "turns": history_turns
        }

    def download_pdf(self, pdf_url:str, local_path:str) -> str:
        """
        下载PDF文件到本地.
        如果本地文件已存在且有效,直接返回路径.
        """
        if os.path.exists(local_path):
            # Check if it's a valid PDF (simple check)
            try:
                with open(local_path, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        return local_path
                    else:
                        print(f"Existing file {local_path} is not a valid PDF. Redownloading...")
            except Exception:
                pass
            
        # 确保目录存在
        directory = os.path.dirname(local_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        print(f"Downloading PDF from {pdf_url} to {local_path}...")
        
        # Optimize Arxiv URL to avoid reCAPTCHA and use export mirror
        if "arxiv.org" in pdf_url:
            pdf_url = pdf_url.replace("arxiv.org", "export.arxiv.org")
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        try:
            response = requests.get(pdf_url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()
            
            # Verify Content-Type
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' in content_type:
                 raise ValueError(f"URL returned HTML instead of PDF. Content-Type: {content_type}")
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify file header after download
            with open(local_path, 'rb') as f:
                if f.read(4) != b'%PDF':
                     raise ValueError("Downloaded file does not appear to be a PDF (Header check failed)")
                     
            print("Download completed.")
            return local_path
        except Exception as e:
            print(f"Failed to download PDF: {e}")
            # 如果下载失败但生成了空文件/不完整文件，最好删除
            if os.path.exists(local_path):
                os.remove(local_path)
            raise e

    def chat(self, query: str, paper: paper_info, pdf_path: str = "") -> chat_session:
        """
        进行一次chat,返回一个chat_session.
        会自动尝试从 paper.meta 加载现有 Session.
        Chat 完成后会自动保存到 paper.meta.session_path (如果未设置则报错).
        """
        existing_chat_session = None
        if not paper.meta.session_path:
            raise ValueError("paper.meta.session_path is empty. Session finds nowhere to be saved.")
        # 0. 获取或创建 Session
        # 尝试从 paper.meta 加载
        if paper.meta.has_session:
            history_path = paper.meta.session_path
            
            if os.path.exists(history_path):
                try:
                    loaded_history = self.gemini_interface.load_history(history_path)
                    existing_chat_session = self.history_to_sessions(loaded_history, paper.meta.id)
                    print(f"Loaded existing session from {history_path}")
                except Exception as e:
                    print(f"Failed to load session from {history_path}: {e}")

        # 如果仍未获取到 Session (加载失败或无记录)，则创建新的
        if existing_chat_session is None:
            if not pdf_path:
                raise ValueError("pdf_path is required when creating a new session")
            existing_chat_session = self.start_new_session(paper.meta.id, self.model_name, pdf_path)

        # 2. 准备History
        history = self.sessions_to_history(existing_chat_session)
        
        # 3. 确定PDF路径
        if not os.path.exists(existing_chat_session.pdf_local_path):
            raise ValueError(f"pdf_local_path {existing_chat_session.pdf_local_path} does not exist.") #无论是初次上传pdf,还是从缓存中加载(缓存非常容易过期,所以缓存本质上还是从cache.display_name中加载,而cache.display_name又是从existing_chat_session.pdf_local_path中获取的,所以无论是那种情况,pdf_local_path对应的那个文件都必须存在,事先就应该下载好)
        if existing_chat_session.cache_name == "":
            pdf_path = existing_chat_session.pdf_local_path
        else:
            pdf_path = "" #按照interface的规则,cache_display_name不为空时,pdf_path就必须为空.
            
        # 4. 调用Gemini Interface
        response_text, updated_history, cost, time_cost = self.gemini_interface.chat(
            pdf=pdf_path,
            text=query,
            history=history
        )
        
        # 5. 更新Session
        # 将更新后的history转换回session结构 (主要是为了获取新的turns和cache info)
        updated_session = self.history_to_sessions(updated_history, paper.meta.id)
        
        existing_chat_session.turns = updated_session.turns
        existing_chat_session.cache_name = updated_session.cache_name
        existing_chat_session.cache_display_name = updated_session.cache_display_name
        
        # 6. 自动保存:每次聊天都保存,每次多轮聊天,本质上每一轮都是读历史,处理新的query,然后保存新的history的过程.
        if paper.meta.session_path:
            save_path = paper.meta.session_path
            history_dict = self.sessions_to_history(existing_chat_session)
            self.gemini_interface.save_history(history_dict, save_path)
            
            # 确保 meta 状态正确
            if not paper.meta.has_session:
                paper.meta.has_session = True
        else:
            print("Warning: paper.meta.session_path is empty. Session NOT saved.")
        
        return existing_chat_session

if __name__ == "__main__":
    #模拟全过程:1. 用户对某一篇paper感兴趣,然后选择了他(也就是说给定paper_info);
    #2. 开始批量生成后,下载这个paper到某个地方.下载结束后,创建chat_session,并在其中记录这个地址.并且在paper_info中记录这个地址.
    #3. 用户向模型提问.(连续提两个问题吧) 结束后,session存储聊天记录.
    #4. 用户某一天又(通过paper)打开了这个对话窗口,接着提问.更新session.
    from config import paper_meta, abstract_info
    
    print("Testing Session Manager Flow...")
    
    # 0. Initialize Manager
    sm = session_manager()
    
    # 1. Mock Paper Info (Using a real arXiv paper for testing)
    # Paper: "Attention Is All You Need" (1706.03762)
    pdf_url = "https://arxiv.org/pdf/1706.03762.pdf"
    
    meta = paper_meta(
        id="1706.03762",
        conference="NIPS",
        year="2017",
        date="2017-06-12",
        title="Attention Is All You Need",
        authors=["Vaswani et al."],
        abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
        institution="Google Brain",
        pdf_url=pdf_url,
        has_abstract=True,
        has_institution=True,
        has_pdf_url=True,
        has_search_on_arxiv=True
    )
    abstract = abstract_info(
        id="1706.03762",
        abstract="The dominant sequence transduction models...",
        abstract_embedding_path="",
        embedding_model="test_model",
        has_embedding=False
    )
    paper = paper_info(meta=meta, abstract=abstract)
    print(f"[Step 1] Paper Selected: {paper.meta.title}")
    
    # 2. Download and Create Session
    local_pdf_dir = r"E:\Project\paperreader\code2\test\downloads"
    local_pdf_path = os.path.join(local_pdf_dir, "1706.03762.pdf")
    
    print(f"[Step 2] Downloading PDF to {local_pdf_path}...")
    try:
        real_path = sm.download_pdf(paper.meta.pdf_url, local_pdf_path)
        print("Download Success.")
    except Exception as e:
        print(f"Download Failed: {e}")
        # Create dummy file if download fails to allow test to proceed (mocking)
        if not os.path.exists(local_pdf_path):
             os.makedirs(os.path.dirname(local_pdf_path), exist_ok=True)
             with open(local_pdf_path, 'w') as f: f.write("Dummy PDF Content")
        real_path = local_pdf_path

    session = sm.start_new_session(paper.meta.id, sm.model_name, real_path)
    # paper.session = session # Removed
    print(f"Session Created. ID: {session.session_id}")
    
    # 3. Chat (2 turns)
    print("\n[Step 3] Starting Chat...")
    
    # 预先设置 session_path，以便 chat 函数可以自动保存
    save_path = r"E:\Project\paperreader\code2\test\temp_gemini_history\chat_history.json"
    paper.meta.session_path = save_path
    
    print(">>> User: What is the main contribution of this paper?")
    # Updated call signature: query, paper, pdf_path
    session = sm.chat("What is the main contribution of this paper?", paper, real_path)    
    print(f"<<< Model: {session.turns[-1].model_response[:100]}... (Cost: {session.turns[-1].cost})")
    
    print(">>> User: Explain the Transformer architecture briefly.")
    session = sm.chat("Explain the Transformer architecture briefly.", paper, real_path)
    print(f"<<< Model: {session.turns[-1].model_response[:100]}... (Cost: {session.turns[-1].cost})")
    
    # Verify auto-save
    if os.path.exists(save_path):
        print(f"Session successfully auto-saved to {save_path}")
    else:
        print(f"Error: Session was NOT auto-saved to {save_path}")
    
    # 4. Reload and Continue (Simulating a fresh start with only paper info)
    print("\n[Step 4] Reloading Session from Meta...")
    
    # Reset session variable (though chat doesn't take it anymore)
    session = None
    
    print(">>> User: What datasets were used?")
    # Pass empty pdf_path, relying on loaded session's cache
    reloaded_session = sm.chat("What datasets were used?", paper, "")
    print(f"<<< Model: {reloaded_session.turns[-1].model_response[:100]}... (Cost: {reloaded_session.turns[-1].cost})")
    
    print("\nTest Completed Successfully.")