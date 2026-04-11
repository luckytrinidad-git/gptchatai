import fitz
import json
import io
import numpy as np
from PIL import Image
import easyocr
from docx import Document
import pandas as pd
import openpyxl
import xlrd

reader = easyocr.Reader(['en'], gpu=False)

def extract_text(file_name, file_bytes):

    filename = file_name.lower()

    # =========================
    # PDF (VECTOR + OCR)
    # =========================
    if filename.endswith(".pdf"):

        text = ""
        pdf = fitz.open(stream=file_bytes, filetype="pdf")

        for page in pdf:

            page_text = page.get_text("text")

            if page_text.strip():
                text += page_text + "\n"
                continue

            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

            img = Image.frombytes(
                "RGB",
                [pix.width, pix.height],
                pix.samples
            )

            img_np = np.array(img)

            result = reader.readtext(img_np, detail=0)

            text += " ".join(result) + "\n"

        return text.strip()

    # =========================
    # TXT / CSV
    # =========================
    elif filename.endswith((".txt", ".csv")):
        return file_bytes.decode("utf-8", errors="ignore")

    # =========================
    # JSON
    # =========================
    elif filename.endswith(".json"):
        try:
            data = json.loads(file_bytes.decode("utf-8", errors="ignore"))
            return json.dumps(data, indent=2)
        except:
            return file_bytes.decode("utf-8", errors="ignore")

    # =========================
    # XLSX (Excel modern)
    # =========================
    elif filename.endswith(".xlsx"):
        output = []

        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)

        for sheet in wb.sheetnames:
            ws = wb[sheet]
            output.append(f"--- Sheet: {sheet} ---")

            for row in ws.iter_rows(values_only=True):
                row_text = [str(cell) if cell is not None else "" for cell in row]
                output.append(" | ".join(row_text))

        return "\n".join(output)


    # =========================
    # XLS (Excel legacy)
    # =========================
    elif filename.endswith(".xls"):
        output = []

        workbook = xlrd.open_workbook(file_contents=file_bytes)

        for sheet in workbook.sheets():
            output.append(f"--- Sheet: {sheet.name} ---")

            for row_idx in range(sheet.nrows):
                row = sheet.row_values(row_idx)
                row_text = [str(cell) for cell in row]
                output.append(" | ".join(row_text))

        return "\n".join(output)

    # =========================
    # DOCX
    # =========================
    elif filename.endswith(".docx"):
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs])

    return file_bytes.decode("utf-8", errors="ignore")

def chunk_text(text, chunk_size=800, overlap=150):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap

    return chunks