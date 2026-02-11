import sys
import os
import time
from gemini_interface_test import Gemini_interface



chatbot = Gemini_interface()
response_text, history, cost, time_cost = chatbot.chat(r"E:\Project\paperreader\code2\test\Security26_SFake.pdf", "请你解读一下这篇文章.")
print(response_text)
print(history)
print(cost)
print(time_cost)
response_text, history, cost, time_cost = chatbot.chat(pdf = None, text = "请你看看这篇文章如何复现.", history=history)
print(response_text)
print(history)
print(cost)
print(time_cost)
chatbot.save_history(history, r"E:\Project\paperreader\code2\test\temp_gemini_history")
history = chatbot.load_history(r"E:\Project\paperreader\code2\test\temp_gemini_history\chat_history_20260209_205632.json")
response_text, history, cost, time_cost = chatbot.chat(pdf = None, text = "我刚刚问了哪些问题,这篇论文作者是谁", history=history)
print(response_text)
print(history)
print(cost)
print(time_cost)
# uploaded_file = chatbot.client.files.upload(file=r"E:\Project\paperreader\code2\test\Security26_SFake.pdf", config={"mime_type": "application/pdf"})
# response_text = chatbot.client.models.generate_content(
#     model="gemini-3-flash-preview",
#     contents=[
#         {
#             "parts": [uploaded_file, "请你解读一下这篇文章."],
#             "role": "user"
#         }
#     ]
# )
# response_text = chatbot.client.models.generate_content(
#     model="gemini-3-flash-preview",
#     contents=[
#         {
#             "parts": [uploaded_file, "请你解读一下这篇文章."],
#             "role": "user"
#         },
#         {
#             "parts": [response_text],
#             "role": "model"
#         },
#         {
#             "parts": ["请你看看这篇文章如何复现."],
#             "role": "user"
#         }
#     ]
# )
