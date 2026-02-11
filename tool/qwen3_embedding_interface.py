import sys
sys.path.append("E:\Project\paperreader\code2")
from config import model_name_path_pair
from sentence_transformers import SentenceTransformer, util
from typing import List
import numpy as np
import time
import random
import string
import torch

class Qwen3_Embedding_Interface:
    def __init__(self):
        
        self.model_path = model_name_path_pair.get("Qwen3-0.6B-embedding", "Qwen/Qwen3-Embedding-0.6B")
        print(f"Loading Qwen3-Embedding-0.6B from {self.model_path}...")
        self.model = SentenceTransformer(self.model_path)

    def get_detailed_instruct(self, task_description: str, query: str) -> str:
        return f'Instruct: {task_description}\nQuery:{query}'

    def batch_encode(self, sentences_list: List[str], batch_size: int = 32) -> List[List[float]]:
        '''
        批量对sentences进行encode,如果显存不够,就分两次进行encode
        '''
        if not sentences_list:
            return []

        try:
            embeddings = self.model.encode(
                sentences_list, 
                batch_size=batch_size,
                show_progress_bar=False, 
                convert_to_numpy=True
            )
            return embeddings.tolist()
            
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                torch.cuda.empty_cache()
                if len(sentences_list) <= 1:
                    raise e
                
                # print(f"OOM detected, splitting batch of size {len(sentences_list)}...")
                mid = batch_size // 2
                left_batch = sentences_list[:mid]
                right_batch = sentences_list[mid:]
                
                return self.batch_encode(left_batch) + self.batch_encode(right_batch)
            else:
                raise e

    def test_speed(self, batch_num: int = 1000, length: int = 100):
        '''
        测试batch_encode的速度
        随机生成batch_num个长度为length的句子然后对他们进行embedding, 并记录时间
        '''
        print(f"Generating {batch_num} random inputs of length {length}...")
        test_input = [
            ''.join(random.choices(string.ascii_letters + string.digits, k=length))
            for _ in range(batch_num)
        ]
        
        print("Starting warmup...")
        self.batch_encode(["Warmup string"] * min(4, batch_num))
        
        print("Starting speed test...")
        start_time = time.time()
        
        self.batch_encode(test_input)
        
        end_time = time.time()
        duration = end_time - start_time
        
        tokens_speed = (batch_num * length) / duration
        message_speed = batch_num / duration
        
        print(f"Qwen3.0.6B 批量encode {batch_num} 个长度为 {length} 的文本, 速度为 {tokens_speed:.2f} tokens/s")
        print(f"Qwen3.0.6B 批量encode {batch_num} 个长度为 {length} 的文本, 速度为 {message_speed:.2f} messages/s")

if __name__ == "__main__":
    embedder = Qwen3_Embedding_Interface()
    for batch_num in [2, 32, 64, 128, 256]:
        embedder.test_speed(batch_num=batch_num, length=300)
