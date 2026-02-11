import sys
sys.path.append("E:\Project\paperreader\code2")
from config import model_name_path_pair
from transformers import MarianMTModel, MarianTokenizer
from typing import List
import time
import random
import string
import torch

class Opus_En_Zh_Interface:
    def __init__(self):
        # 优先使用本地模型,如果没有则使用在线模型
        # 注意: 这里的键名 opus-mt-en-zh 对应 config.py 中的配置
        self.model_path = model_name_path_pair.get("opus-mt-en-zh", "Helsinki-NLP/opus-mt-en-zh")
        print(f"Loading Opus-MT-En-Zh from {self.model_path}...")
        
        self.tokenizer = MarianTokenizer.from_pretrained(self.model_path)
        self.model = MarianMTModel.from_pretrained(self.model_path)
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def batch_translate(self, sentences_list: List[str]) -> List[str]:
        '''
        批量对sentences进行翻译(英->中),如果显存不够,就分两次进行translate
        '''
        if not sentences_list:
            return []

        try:
            # Tokenize
            # padding=True确保batch内长度一致, truncation=True防止过长
            batch = self.tokenizer(
                sentences_list, 
                return_tensors="pt", 
                padding=True, 
                truncation=True
            ).to(self.device)
            
            # Generate
            translated = self.model.generate(**batch)
            
            # Decode
            res = [self.tokenizer.decode(t, skip_special_tokens=True) for t in translated]
            return res
            
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                torch.cuda.empty_cache()
                if len(sentences_list) <= 1:
                    raise e
                
                # print(f"OOM detected, splitting batch of size {len(sentences_list)}...")
                mid = len(sentences_list) // 2
                left_batch = sentences_list[:mid]
                right_batch = sentences_list[mid:]
                
                return self.batch_translate(left_batch) + self.batch_translate(right_batch)
            else:
                raise e

    def test_speed(self, batch_num: int = 10, length: int = 100):
        '''
        测试batch_translate的速度
        随机生成英文文本进行翻译测试
        '''
        print(f"Generating {batch_num} random English inputs of length {length}...")
        # 生成随机英文文本 (字母+空格)
        test_input = [
            ''.join(random.choices(string.ascii_letters + " ", k=length))
            for _ in range(batch_num)
        ]
        
        print("Starting warmup...")
        self.batch_translate(["Warmup string"] * min(4, batch_num))
        
        print("Starting speed test...")
        start_time = time.time()
        
        res = self.batch_translate(test_input)
        
        end_time = time.time()
        duration = end_time - start_time
        
        message_speed = batch_num / duration
        
        print(f"Opus En-Zh 批量translate {batch_num} 个长度为 {length} 的文本, 速度为 {message_speed:.2f} messages/s")
        print("Sample translation:")
        if test_input:
            print(f"Input: {test_input[0][:50]}...")
            print(f"Output: {res[0][:50]}...")

if __name__ == "__main__":
    translator = Opus_En_Zh_Interface()
    # 测试不同batch size下的速度
    for batch_num in [2, 32, 64, 128, 256]:
        translator.test_speed(batch_num=batch_num, length=300)
