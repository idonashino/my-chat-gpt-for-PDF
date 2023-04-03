import os
import openai
import tenacity
from typing import List, Dict
from time import strftime, gmtime
from read_pdf import Paper


class ChatGPTResponse(object):
    def __init__(self, key_word: str) -> None:
        self.key_word = key_word
        self.gpt_api = r"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"

    def summary_process(self, pdfs: List) -> None:
        markdown_output = ""
        for pdf in pdfs:
            paper_info = Paper(pdf)
            summary_res = []
            # step 1: summarize abstract
            text = list(paper_info.section_text_dict.values())[0]
            try:
                summary_res.append(self.chat_abstract(text))
            except Exception as e:
                print(f"Step 1 Error! {e}")
            # step 2: summarize method
            text = list(paper_info.section_text_dict.values())[0]
            try:
                summary_res.append(self.chat_method(text))
            except Exception as e:
                print(f"Step 2 Error! {e}")
            # step 3: summarize conclusion
            text = list(paper_info.section_text_dict.values())[0]
            try:
                summary_res.append(self.chat_conclusion(text))
            except Exception as e:
                print(f"Step 3 Error! {e}")
            for res in summary_res:
                markdown_output += res

        self.export_markdown(markdown_output)

    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
                    stop=tenacity.stop_after_attempt(5),
                    reraise=True)
    def chat_abstract(self, text: str) -> str:
        messages = [
            {"role": "system", "content": f"You are a researcher in the field of {self.key_word} who is good at summarizing papers using concise statements"},
            {"role": "assistant", "content": "This is the title, author, link, abstract and introduction of an English document. I need your help to read and summarize the following questions: " + text},
            {"role": "user", "content": """                 
                1. Mark the title of the paper (with Chinese translation)
                2. list all the authors' names (use English)
                3. mark the first author's affiliation (output English translation only)                 
                4. mark the keywords of this article (use English)
                5. link to the paper, Github code link (if available, fill in Github:None if not)
                6. summarize according to the following four points.Be sure to use English answers (proper nouns need to be marked in English)
                - (1):What is the research background of this article?
                - (2):What are the past methods? What are the problems with them? Is the approach well motivated?
                - (3):What is the research methodology proposed in this paper?
                - (4):On what task and what performance is achieved by the methods in this paper? Can the performance support their goals?
                Follow the format of the output that follows:                  
                1. Title: xxx\n\n
                2. Authors: xxx\n\n
                3. Affiliation: xxx\n\n                 
                4. Keywords: xxx\n\n   
                5. Urls: xxx or xxx , xxx \n\n      
                6. Summary: \n\n
                - (1):xxx;\n 
                - (2):xxx;\n 
                - (3):xxx;\n  
                - (4):xxx.\n\n     
                
                Be sure to use English answers (proper nouns need to be marked in English), statements as concise and academic as possible, do not have too much repetitive information, numerical values using the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed.                 
                """},
        ]
        return self.chat_with_gpt(messages=messages)

    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
                    stop=tenacity.stop_after_attempt(5),
                    reraise=True)
    def chat_method(self, text: str) -> str:
        messages = [
                {"role": "system", "content": "You are a researcher in the field of ["+self.key_word+"] who is good at summarizing papers using concise statements"},  # chatgpt 角色
                {"role": "assistant", "content": "This is the <summary> and <Method> part of an English document, where <summary> you have summarized, but the <Methods> part, I need your help to read and summarize the following questions." + text},  # 背景知识
                {"role": "user", "content": """                 
                 7. Describe in detail the methodological idea of this article. Be sure to use English answers (proper nouns need to be marked in English). For example, its steps are.
                    - (1):...
                    - (2):...
                    - (3):...
                    - .......
                 Follow the format of the output that follows: 
                 7. Methods: \n\n
                    - (1):xxx;\n 
                    - (2):xxx;\n 
                    - (3):xxx;\n  
                    ....... \n\n     
                 
                 Be sure to use English answers (proper nouns need to be marked in English), statements as concise and academic as possible, do not repeat the content of the previous <summary>, the value of the use of the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed, ....... means fill in according to the actual requirements, if not, you can not write.                 
                 """},
            ]
        return self.chat_with_gpt(messages=messages)

    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
                    stop=tenacity.stop_after_attempt(5),
                    reraise=True)
    def chat_conclusion(self, text: str) -> str:
        messages = [
                {"role": "system", "content": "You are a reviewer in the field of ["+self.key_word+"] and you need to critically review this article"},  # chatgpt 角色
                {"role": "assistant", "content": "This is the <summary> and <conclusion> part of an English literature, where <summary> you have already summarized, but <conclusion> part, I need your help to summarize the following questions:" + text},  # 背景知识，可以参考OpenReview的审稿流程
                {"role": "user", "content": """                 
                 8. Make the following summary.Be sure to use English answers (proper nouns need to be marked in English).
                    - (1):What is the significance of this piece of work?
                    - (2):Summarize the strengths and weaknesses of this article in three dimensions: innovation point, performance, and workload.                   
                    .......
                 Follow the format of the output later: 
                 8. Conclusion: \n\n
                    - (1):xxx;\n                     
                    - (2):Innovation point: xxx; Performance: xxx; Workload: xxx;\n                      
                 
                 Be sure to use English answers (proper nouns need to be marked in English), statements as concise and academic as possible, do not repeat the content of the previous <summary>, the value of the use of the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed, ....... means fill in according to the actual requirements, if not, you can not write.                 
                 """},
            ]
        return self.chat_with_gpt(messages=messages)

    def chat_with_gpt(self, messages: List[Dict]) -> str:
        openai.api_key = self.gpt_api
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
        )
        result = ""
        for choice in response.choices:
            result += choice.message.content
        return result

    def export_markdown(self, markdown_str: str) -> None:
        save_path = os.path.join("./gpt_reviews", "reviews" + strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ".pdf")
        with open(save_path, 'w', encoding="utf-8") as f:
            f.write(markdown_str)


if __name__ == '__main__':
    src_path = r"./pdf_papers"
    file_list = [os.path.join(src_path, file) for file in os.listdir(src_path) if file.endswith('.pdf')]
    new_chat = ChatGPTResponse(key_word="medicine")
    new_chat.summary_process(file_list)


