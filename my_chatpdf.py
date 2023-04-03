import os
import pandas as pd
from openai.embeddings_utils import get_embedding, cosine_similarity
import openai
import PyPDF2
from typing import List, Dict, Optional
from time import strftime, gmtime


openai.api_key = r"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"


class Chatbot(object):
    def __init__(self) -> None:
        self.user_input = """
            Please summarize this paper. The output should follow the format bellow:
            1. Summary: xxx;
            2. Method: xxx;
            3. Conclusion: xxx;
            Be sure to use Chinese answers
            """

    def parse_paper(self, pdf) -> List[Dict]:
        print("Parsing paper")
        number_of_pages = len(pdf.pages)
        print(f"Total number of pages: {number_of_pages}")
        paper_text = []
        for i in range(number_of_pages):
            page = pdf.pages[i]
            page_text = []

            def visitor_body(text, cm, tm, fontDict, fontSize):
                x = tm[4]
                y = tm[5]
                # ignore header/footer
                if (50 < y < 720) and (len(text.strip()) > 1):
                    page_text.append({
                        'fontsize': fontSize,
                        'text': text.strip().replace('\x03', ''),
                        'x': x,
                        'y': y
                    })

            _ = page.extract_text(visitor_text=visitor_body)

            blob_font_size = None
            blob_text = ''
            processed_text = []

            for t in page_text:
                if t['fontsize'] == blob_font_size:
                    blob_text += f" {t['text']}"
                    if len(blob_text) >= 2000:
                        processed_text.append({
                            'fontsize': blob_font_size,
                            'text': blob_text,
                            'page': i
                        })
                        blob_font_size = None
                        blob_text = ''
                else:
                    if blob_font_size is not None and len(blob_text) >= 1:
                        processed_text.append({
                            'fontsize': blob_font_size,
                            'text': blob_text,
                            'page': i
                        })
                    blob_font_size = t['fontsize']
                    blob_text = t['text']
                paper_text += processed_text
        print("Done parsing paper")
        return paper_text

    def paper_df(self, pdf: List[Dict[str, str]]) -> pd.DataFrame:
        print('Creating dataframe')
        filtered_pdf = []
        for row in pdf:
            if len(row['text']) < 30:
                continue
            if len(row['text']) > 8000:
                row['text'] = row['text'][:8000]
            filtered_pdf.append(row)
        df = pd.DataFrame(filtered_pdf)
        # remove elements with identical df[text] and df[page] values
        df = df.drop_duplicates(subset=['text', 'page'], keep='first')
        df['length'] = df['text'].apply(lambda x: len(x))
        print('Done creating df')
        return df

    def calculate_embeddings(self, df: pd.DataFrame) -> pd.DataFrame:
        print('Calculating embeddings')
        embedding_model = "text-embedding-ada-002"
        embeddings = df.text.apply([lambda x: get_embedding(x, engine=embedding_model)])
        df["embeddings"] = embeddings
        print('Done calculating embeddings')
        return df

    def search_embeddings(self, df: pd.DataFrame, query: str, n: int = 2) -> pd.DataFrame:
        query_embedding = get_embedding(
            query,
            engine="text-embedding-ada-002"
        )
        df["similarity"] = df.embeddings.apply(lambda x: cosine_similarity(x, query_embedding))

        results = df.sort_values("similarity", ascending=False, ignore_index=True)
        results = results.head(n)
        global sources
        sources = []
        for i in range(n):
            # append the page number and the text as a dict to the sources list
            sources.append({'Page ' + str(results.iloc[i]['page']): results.iloc[i]['text'][:150] + '...'})
        print(sources)
        return results.head(n)

    def create_prompt(self, df: pd.DataFrame, user_input: str, strategy: Optional[str] = "paper") -> str:
        result = self.search_embeddings(df, user_input)
        if strategy == "paper":
            prompt = """You are a large language model whose expertise is reading and summarizing scientific papers.
            You are given a query and a series of text embeddings from a paper in order of their cosine similarity to the query.
            You must take the given embeddings and return a very detailed summary of the paper that answers the query.
                Given the question: """ + user_input + """

                and the following embeddings as data: 

                1.""" + str(result.iloc[0]['text']) + """
                2.""" + str(result.iloc[1]['text']) + """

                Return a concise and accurate answer:"""
        else:
            prompt = """As a language model specialized in reading and summarizing documents, your task is to provide a concise answer in Chinese based on a given query and a series of text embeddings from the document. 
            The embeddings are provided in order of their cosine similarity to the query. Your response should use as much original text as possible. 
            Your answer should be highly concise and accurate, providing relevant information that directly answers the query. 
            You should also ensure that your response is written in clear and concise Chinese, using appropriate grammar and vocabulary. 
            Please note that you must use the provided text embeddings to generate your response, which means you will need to understand how they relate to the original document. 
            Additionally, your response should focus on answering the specific query provided..
                Given the question: """ + user_input + """

                and the following embeddings as data: 

                1.""" + str(result.iloc[0]['text']) + """
                2.""" + str(result.iloc[1]['text']) + """

                Return a concise and accurate answer:"""
        print('Done creating prompt')
        return prompt

    def response(self, df: pd.DataFrame, prompt: str) -> Dict:
        print('Sending request to GPT-3')
        prompt = self.create_prompt(df, prompt)
        r = openai.Completion.create(model="text-davinci-003", prompt=prompt, temperature=0.4, max_tokens=1500)
        answer = r.choices[0]['text']
        print('Done sending request to GPT-3.5')
        response = {'answer': answer, 'sources': sources}
        return response

    def do_process(self, pdf_list: List[str]) -> None:
        markdown_res = ""
        for pdf in pdf_list:
            pdf_reader = PyPDF2.PdfReader(pdf)
            markdown_res += f"## {pdf_reader.metadata.title}\n"
            pdf_text = self.parse_paper(pdf_reader)
            df = self.paper_df(pdf_text)
            df = self.calculate_embeddings(df)
            prompt = self.create_prompt(df, self.user_input)
            response = self.response(df, prompt)
            markdown_res += response['answer']
            markdown_res += '\n\n'
        self.export_markdown(markdown_res)

    def export_markdown(self, markdown_str: str) -> None:
        save_path = os.path.join("./gpt_reviews", "reviews" + strftime("%Y%m%d%H%M", gmtime()) + ".md")
        with open(save_path, 'w', encoding="utf-8") as f:
            f.write(markdown_str)


if __name__ == '__main__':
    src_path = r"./pdf_papers"
    file_list = [os.path.join(src_path, file) for file in os.listdir(src_path) if file.endswith('.pdf')]

    chatbot = Chatbot()
    # chatbot.do_process(file_list)

    pdf_reader = PyPDF2.PdfReader(file_list[2])
    pdf_text = chatbot.parse_paper(pdf_reader)
    df = chatbot.paper_df(pdf_text)
    df = chatbot.calculate_embeddings(df)
    prompt = chatbot.create_prompt(df, chatbot.user_input)
    r = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
    answer = r.choices[0].message.content
