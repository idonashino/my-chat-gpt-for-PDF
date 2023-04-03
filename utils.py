from typing import List, Dict


def parse_paper(pdf) -> List[Dict]:
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
