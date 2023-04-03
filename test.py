from utils import parse_paper
import os
import PyPDF2


if __name__ == '__main__':
    src_path = r"./pdf_papers"
    file_list = [os.path.join(src_path, file) for file in os.listdir(src_path) if file.endswith('.pdf')]
    pdf_reader = PyPDF2.PdfReader(file_list[2])
    a = parse_paper(pdf_reader)
