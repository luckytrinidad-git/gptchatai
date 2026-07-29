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
import re

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

DOCUMENT_MAP = {
    "RAO": "REVENUE ADMINISTRATIVE ORDER",
    "RMO": "REVENUE MEMORANDUM ORDER",
    "RMC": "REVENUE MEMORANDUM CIRCULAR",
    "RR": "REVENUE REGULATIONS",
    "RDAO": "REVENUE DELEGATION AUTHORITY ORDER",
    "RAMO": "REVENUE ADMINISTRATIVE MEMORANDUM ORDER",
    "CMC": "CUSTOMS MEMORANDUM CIRCULAR",
}


def normalize_document_number(number: str) -> str:
    """
    0004-2026
        ↓
    4-2026
    """

    number = number.strip()

    m = re.match(r"^0*(\d+)\s*[-–]\s*(\d{4})$", number)

    if m:
        left = str(int(m.group(1)))
        right = m.group(2).replace(" ", "")
        return f"{left}-{right}"

    return re.sub(r"\s+", "", number)

def build_title_variants(doc_type: str, doc_number: str):
    """
    Example

    RAO
    2-2026

    Generates many searchable title variants.
    """

    doc_number = normalize_document_number(doc_number)

    full_name = DOCUMENT_MAP.get(doc_type)

    variants = set()

    variants.add(f"{doc_type} {doc_number}")
    variants.add(f"{doc_type} NO {doc_number}")
    variants.add(f"{doc_type} NO. {doc_number}")
    variants.add(f"{doc_type} NO.{doc_number}")

    if full_name:

        variants.add(f"{full_name} {doc_number}")
        variants.add(f"{full_name} NO {doc_number}")
        variants.add(f"{full_name} NO. {doc_number}")
        variants.add(f"{full_name} NO.{doc_number}")

    variants.add(doc_number)

    return sorted(variants)

def extract_document_reference(question: str):
    """
    Detects references like

    RAO No. 2-2026

    Revenue Administrative Order No. 2-2026

    RMC 63-2025

    RR No 9-2024

    etc.
    """

    pattern = re.compile(
        r"""
        \b
        (
            RAO|
            RMO|
            RMC|
            RR|
            RDAO|
            RAMO|
            CMC|
            REVENUE\s+ADMINISTRATIVE\s+ORDER|
            REVENUE\s+MEMORANDUM\s+ORDER|
            REVENUE\s+MEMORANDUM\s+CIRCULAR|
            REVENUE\s+REGULATIONS|
            REVENUE\s+DELEGATION\s+AUTHORITY\s+ORDER
        )
        \s*
        (?:NO\.?)?
        \s*
        ([0-9\s\-–]+)
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    match = pattern.search(question)

    if not match:
        return None

    doc_type = match.group(1).upper()

    reverse = {
        "REVENUE ADMINISTRATIVE ORDER": "RAO",
        "REVENUE MEMORANDUM ORDER": "RMO",
        "REVENUE MEMORANDUM CIRCULAR": "RMC",
        "REVENUE REGULATIONS": "RR",
        "REVENUE DELEGATION AUTHORITY ORDER": "RDAO",
    }

    doc_type = reverse.get(doc_type, doc_type)

    doc_number = normalize_document_number(match.group(2))

    return {
        "doc_type": doc_type,
        "doc_number": doc_number,
        "variants": build_title_variants(doc_type, doc_number),
    }