import fitz
import json
import io
import numpy as np
from PIL import Image
# import easyocr
from docx import Document
import pandas as pd
import openpyxl
import xlrd
from rapidocr_onnxruntime import RapidOCR
from pathlib import Path
import requests
from gptchatbot.settings import IPFS_SERVER_URL

def extract_text(file_name, file_bytes):

    filename = file_name.lower()

    # =========================
    # PDF (VECTOR + OCR)
    # =========================
    if filename.endswith(".pdf"):

        text = ""
        pdf = fitz.open(stream=file_bytes, filetype="pdf")
        ocr = RapidOCR()

        for i, page in enumerate(pdf):

            pix = page.get_pixmap(
                matrix=fitz.Matrix(2, 2),  # ~144 DPI
                colorspace=fitz.csRGB,
                alpha=False,
            )

            img = np.frombuffer(
                pix.samples,
                dtype=np.uint8,
            ).reshape(
                pix.height,
                pix.width,
                3,
            )

            result, _ = ocr(img)

            text = ""

            if result:
                text = "\n".join(
                    line[1] for line in result
                )

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

def upload_to_ipfs(uploaded_file):
    """
    uploaded_file:
        Django -> request.FILES["file"]
        FastAPI -> UploadFile.file
        Flask -> request.files["file"]

    Returns:
        {
            "cid": "...",
            "name": "...",
            "size": "..."
        }
    """
    print("Uploading to", f"{IPFS_SERVER_URL}/add")
    print(type(uploaded_file))
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file,
            uploaded_file.content_type
            if hasattr(uploaded_file, "content_type")
            else "application/octet-stream",
        )
    }
    print(files)

    print("Before POST")

    response = requests.post(
        f"{IPFS_SERVER_URL}/add",
        files=files,
        params={"pin": "true"},
        timeout=(10, 300),
    )

    print("After POST")
    print(response.status_code)

    result = response.json()

    cid = result["Hash"]

    return cid