import sys
sys.path.append("E:\Project\paperreader\code2")
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
import torch
import time
import random
import string
from config import model_name_path_pair
from typing import Dict

class Qwen3_2B_Interface:
    def __init__(self, model_path=model_name_path_pair["Qwen3-VL-2B"]):
        print(f"Loading Qwen3.2B model from {model_path}...")
        self.processor = AutoProcessor.from_pretrained(model_path)
        if hasattr(self.processor, "tokenizer"):
            self.processor.tokenizer.padding_side = 'left'
        
        # User requested init way update: using from_pretrained with device_map="auto" and torch_dtype="auto"
        # For Qwen3-VL, we stick to Qwen2_5_VLForConditionalGeneration as it's the architectural match
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_path,
            torch_dtype="auto",
            device_map="auto"
        )
        
    def batch_generate(self, input_list: list[str], max_new_tokens: int = 2048) -> list[Dict[str, str]]:
        """
        根据输入列表批量生成文本.
        返回列表, 每个元素为字典: {"thinking": str, "content": str}
        """
        if not input_list:
            return []
            
        batch_messages = []
        for text in input_list:
            batch_messages.append([
                {
                    "role": "user",
                    "content": [{"type": "text", "text": text}]
                }
            ])
            
        try:
            # Preparation for inference
            # We try to apply the same logic as Qwen3-0.6B for thinking if supported by processor
            inputs = self.processor.apply_chat_template(
                batch_messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
                padding=True 
                # enable_thinking=True # Not enabled here as AutoProcessor for VL might differ
            )
            
            inputs = inputs.to(self.model.device)
            
            with torch.no_grad():
                generated_ids = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
            
            # Trim generated ids
            generated_ids_trimmed = [
                out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )
            
            # Since Qwen3-VL-2B logic for thinking is not confirmed to use the same token or method,
            # and the user snippet was for 0.6B, we will attempt to parse but default to empty thinking if not found.
            # However, for consistency with the requested interface change, we return the same dict structure.
            
            results = []
            for text_out in output_text:
                # Naive parsing if the model outputs <think>...</think> in text
                # Or if it uses special tokens that are stripped.
                # If special tokens are stripped, we might lose the boundaries.
                # But if we assume the model output behaves similarly (thinking first then content)
                # We can't distinguish without the special tokens if they are stripped.
                # The 0.6B snippet used decode(ids) with manual splitting by token ID.
                # Here we already decoded.
                # Let's just return content for now, unless we see the pattern.
                results.append({
                    "thinking": "",
                    "content": text_out
                })
            
            return results
            
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                torch.cuda.empty_cache()
                if len(input_list) <= 1:
                    raise e
                
                mid = len(input_list) // 2
                left_batch = input_list[:mid]
                right_batch = input_list[mid:]
                
                return self.batch_generate(left_batch) + self.batch_generate(right_batch)
            else:
                raise e

    def test_speed(self, batch_num: int = 1000, length: int = 100):
        """
        测试批量生成的速度.
        """
        print(f"Generating {batch_num} random inputs of length {length}...")
        test_input = [
            ''.join(random.choices(string.ascii_letters + string.digits, k=length))
            for _ in range(batch_num)
        ]
        
        print("Starting warmup...")
        self.batch_generate(["Warmup string"] * min(4, batch_num))
        
        print("Starting speed test...")
        start_time = time.time()
        
        res = self.batch_generate(test_input)
        
        end_time = time.time()
        duration = end_time - start_time
        
        message_speed = batch_num / duration
        
        print(f"Qwen3.2B 批量生成 {batch_num} 个长度为 {length} 的文本, 速度为 {message_speed:.2f} messages/s")
        if res:
             print("Sample result:")
             print(f"Content: {res[0]['content'][:100]}...")


if __name__ == "__main__":
    qwen3_2B = Qwen3_2B_Interface()
    for batch_num in [2,4,8,16]:
        qwen3_2B.test_speed(batch_num=batch_num,length = 300)
