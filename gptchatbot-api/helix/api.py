from ninja import Router, File
from ninja.files import UploadedFile
from helix.engine import analyze_dataframe, build_pdf_answer
from helix.schemas import *
import pandas as pd
import io
from pypdf import PdfReader


# app = FastAPI(title="HELIX RAG API")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

router = Router()

DATASETS = {}
PDF_TEXT = ""
PDF_SOURCE = ""


@router.post("/ingest")
def ingest(request, file: UploadedFile = File(...)):

    global PDF_TEXT
    global PDF_SOURCE

    filename = file.name.lower()

    if filename.endswith(".csv"):
        contents = file.read()
        df = pd.read_csv(io.BytesIO(contents))

        DATASETS["current"] = df
        DATASETS["current_type"] = "csv"

        PDF_TEXT = ""

        return {
            "status": "success",
            "rows": len(df)
        }

    if filename.endswith(".pdf"):
        contents = file.read()

        reader = PdfReader(io.BytesIO(contents))

        text = ""
        for page in reader.pages:
            t = page.extract_text() or ""
            text += t + "\n"

        PDF_TEXT = text
        PDF_SOURCE = file.name

        DATASETS["current_type"] = "pdf"

        return {
            "status": "success",
            "pages": len(reader.pages)
        }

    return {"error": "Unsupported file"}


# @router.post("/query")
# def query(request, question: str, mode: str = "data"):
@router.post("/query")
def query(request, payload: QueryRequest):

    question = payload.question
    mode = payload.mode


    current_type = DATASETS.get("current_type")

    if current_type == "csv":
        df = DATASETS["current"]
        return analyze_dataframe(df, question, mode)

    if current_type == "pdf":
        return build_pdf_answer(PDF_TEXT, question, mode, PDF_SOURCE)

    return {"error": "No dataset ingested"}

# def normalize_df_columns(df):
#     df.columns = [str(c).strip() for c in df.columns]
#     return df


# def to_numeric(series):
#     return pd.to_numeric(series, errors="coerce").fillna(0)


# def detect_top_n(q, default=5):
#     for n in range(1, 21):
#         if f"top {n}" in q or f"{n} revenue" in q or f"{n} branches" in q:
#             return n
#     return default


# def safe_period_sort(series):
#     try:
#         sorted_index = sorted(
#             series.index,
#             key=lambda x: (int(str(x).split("-")[1]), int(str(x).split("-")[0]))
#         )
#         return series.reindex(sorted_index)
#     except Exception:
#         return series.sort_index()


# def extract_pdf_text(file_bytes: bytes) -> str:
#     reader = PdfReader(io.BytesIO(file_bytes))
#     text_parts = []

#     for page in reader.pages:
#         try:
#             t = page.extract_text() or ""
#         except Exception:
#             t = ""
#         if t.strip():
#             text_parts.append(t.strip())

#     return "\n\n".join(text_parts)


# def split_pdf_chunks(text: str, chunk_size: int = 1200, overlap: int = 150):
#     text = text.strip()
#     if not text:
#         return []

#     chunks = []
#     start = 0
#     n = len(text)

#     while start < n:
#         end = min(start + chunk_size, n)
#         chunk = text[start:end].strip()
#         if chunk:
#             chunks.append(chunk)
#         if end >= n:
#             break
#         start = max(0, end - overlap)

#     return chunks


# def build_executive_summary(df, branch_col, period_col, account_col, value):
#     summary: Dict[str, Any] = {
#         "total": float(value.sum())
#     }

#     if branch_col:
#         branch_totals = (
#             pd.DataFrame({"branch": df[branch_col], "value": value})
#             .groupby("branch")["value"]
#             .sum()
#             .sort_values(ascending=False)
#         )
#         if len(branch_totals) > 0:
#             summary["top_branch"] = str(branch_totals.index[0])
#             summary["top_branch_amt"] = float(branch_totals.iloc[0])
#             summary["top_branch_pct"] = (
#                 float(branch_totals.iloc[0]) / summary["total"] * 100
#                 if summary["total"] else 0.0
#             )

#     if period_col:
#         period_totals = (
#             pd.DataFrame({"period": df[period_col], "value": value})
#             .groupby("period")["value"]
#             .sum()
#         )
#         period_totals = safe_period_sort(period_totals)

#         if len(period_totals) > 0:
#             summary["best_period"] = str(period_totals.idxmax())
#             summary["best_amt"] = float(period_totals.max())
#             summary["worst_period"] = str(period_totals.idxmin())
#             summary["worst_amt"] = float(period_totals.min())

#             if summary["worst_amt"] > 0:
#                 summary["volatility_pct"] = (
#                     (summary["best_amt"] - summary["worst_amt"]) / summary["worst_amt"]
#                 ) * 100

#     tx = df.copy()
#     tx["_value"] = value
#     tx = tx.sort_values("_value", ascending=False).head(1)

#     if not tx.empty:
#         row = tx.iloc[0]
#         summary["largest_tx_amt"] = float(row["_value"])
#         summary["largest_tx_branch"] = str(row[branch_col]) if branch_col else "N/A"
#         summary["largest_tx_period"] = str(row[period_col]) if period_col else "N/A"
#         summary["largest_tx_account"] = str(row[account_col]) if account_col else "N/A"

#     summary["takeaway"] = "Management takeaway: review top branches and investigate unusually large transactions."
#     return summary


# def format_data_primary(summary: Dict[str, Any]) -> str:
#     lines = []

#     if summary.get("total") is not None:
#         lines.append(f"Total financial activity: ${summary['total']:,.2f}")

#     if summary.get("top_branch"):
#         lines.append(
#             f"The strongest branch is {summary['top_branch']} with ${summary['top_branch_amt']:,.2f}."
#         )

#     if summary.get("best_period"):
#         lines.append(f"Highest period: {summary['best_period']}")

#     if summary.get("worst_period"):
#         lines.append(f"Lowest period: {summary['worst_period']}")

#     if summary.get("takeaway"):
#         lines.append(summary["takeaway"])

#     return "\n".join(lines)


# def format_insight_primary(summary: Dict[str, Any]) -> str:
#     lines = []

#     total = summary.get("total", 0.0)
#     top_branch = summary.get("top_branch")
#     top_branch_amt = summary.get("top_branch_amt", 0.0)
#     top_branch_pct = summary.get("top_branch_pct", 0.0)
#     best_period = summary.get("best_period")
#     best_amt = summary.get("best_amt", 0.0)
#     worst_period = summary.get("worst_period")
#     worst_amt = summary.get("worst_amt", 0.0)
#     volatility_pct = summary.get("volatility_pct")
#     largest_tx_amt = summary.get("largest_tx_amt")
#     largest_tx_branch = summary.get("largest_tx_branch")
#     largest_tx_period = summary.get("largest_tx_period")
#     largest_tx_account = summary.get("largest_tx_account")

#     lines.append("Executive Brief")
#     lines.append("")
#     lines.append("Overview")

#     if top_branch:
#         lines.append(
#             f"Financial activity totals ${total:,.2f}, with the highest concentration in {top_branch}, "
#             f"which contributes ${top_branch_amt:,.2f} and represents about {top_branch_pct:.1f}% of total activity."
#         )
#     else:
#         lines.append(f"Financial activity totals ${total:,.2f}.")

#     if best_period and worst_period:
#         lines.append(
#             f"Performance peaked in {best_period} at ${best_amt:,.2f} and weakened to ${worst_amt:,.2f} in {worst_period}."
#         )

#     lines.append("")
#     lines.append("Key Risks")

#     if top_branch:
#         if top_branch_pct >= 40:
#             lines.append(
#                 f"• Revenue concentration risk: {top_branch} drives {top_branch_pct:.1f}% of activity, which suggests dependency on one branch."
#             )
#         else:
#             lines.append(
#                 f"• Moderate concentration: {top_branch} is the leading branch and should be monitored as the primary activity driver."
#             )

#     if volatility_pct is not None:
#         lines.append(
#             f"• Volatility risk: the spread between the strongest and weakest period is about {volatility_pct:.1f}%."
#         )

#     if largest_tx_amt is not None:
#         lines.append(
#             f"• Large transaction exposure: the biggest single entry is ${largest_tx_amt:,.2f} in branch {largest_tx_branch}, period {largest_tx_period}, account {largest_tx_account}."
#         )

#     lines.append("")
#     lines.append("Opportunities")

#     if top_branch:
#         lines.append(
#             f"• Replicate what is working in {top_branch} across lower-performing branches."
#         )

#     if best_period and worst_period:
#         lines.append(
#             f"• Analyze what drove the strength in {best_period} and whether those drivers can be repeated."
#         )

#     lines.append(
#         "• Use this dataset together with COGS and SG&A to move from activity reporting to profitability insight."
#     )

#     lines.append("")
#     lines.append("Recommended Actions")
#     lines.append("1. Review the top 10 transactions by value.")
#     lines.append("2. Compare branch performance to identify concentration and underperformance.")
#     lines.append("3. Investigate whether weaker periods reflect seasonality, execution issues, or demand softness.")
#     lines.append("4. Combine this file with cost datasets to measure true profitability.")

#     lines.append("")
#     lines.append("Suggested next questions")
#     lines.append("• Show revenue by branch")
#     lines.append("• Show revenue trends")
#     lines.append("• Show the largest transactions")
#     lines.append("• Which branch has the weakest performance?")
#     lines.append("• Compare this dataset with COGS")

#     return "\n".join(lines)


# # -----------------------------
# # INGEST
# # -----------------------------

# @app.post("/ingest")
# async def ingest(file: UploadFile = File(...)):
#     global PDF_TEXT
#     global PDF_SOURCE

#     filename = (file.filename or "").lower()

#     if filename.endswith(".csv"):
#         contents = await file.read()
#         df = pd.read_csv(io.BytesIO(contents))

#         DATASETS["current"] = df
#         DATASETS["current_type"] = "csv"
#         DATASETS["filename"] = file.filename

#         PDF_TEXT = ""
#         PDF_SOURCE = ""

#         return {
#             "status": "success",
#             "rows": len(df),
#             "message": "CSV ingested successfully"
#         }

#     if filename.endswith(".pdf"):
#         contents = await file.read()
#         pdf_text = extract_pdf_text(contents)

#         PDF_TEXT = pdf_text
#         PDF_SOURCE = file.filename

#         DATASETS["current_type"] = "pdf"
#         DATASETS["filename"] = file.filename

#         return {
#             "status": "success",
#             "message": "PDF ingested successfully",
#             "pages": len(PdfReader(io.BytesIO(contents)).pages)
#         }

#     return {"status": "error", "message": "Unsupported file type"}


# # -----------------------------
# # CSV ANALYSIS
# # -----------------------------

# def analyze_dataframe(df: pd.DataFrame, question: str, mode: str = "data") -> Dict[str, Any]:
#     df = normalize_df_columns(df)
#     q = question.lower()

#     branch_col = None
#     period_col = None
#     debit_col = None
#     credit_col = None
#     desc_col = None
#     account_col = None

#     for c in df.columns:
#         cl = c.lower()

#         if "branch" in cl:
#             branch_col = c

#         if "period" in cl or "month" in cl:
#             period_col = c

#         if "debit" in cl:
#             debit_col = c

#         if "credit" in cl or "amount" in cl:
#             credit_col = c

#         if "desc" in cl or "memo" in cl:
#             desc_col = c

#         if "account" in cl:
#             account_col = c

#     debit = to_numeric(df[debit_col]) if debit_col else pd.Series([0] * len(df))
#     credit = to_numeric(df[credit_col]) if credit_col else pd.Series([0] * len(df))

#     value = credit.copy()
#     if float(value.sum()) == 0:
#         value = debit.copy()

#     # Revenue by branch
#     if "branch" in q and "revenue" in q:
#         if not branch_col:
#             return {
#                 "title": "Top revenue branches",
#                 "text": "No branch column was found in this dataset."
#             }

#         grouped = (
#             pd.DataFrame({
#                 "branch": df[branch_col].astype(str),
#                 "value": value
#             })
#             .groupby("branch")["value"]
#             .sum()
#             .sort_values(ascending=False)
#         )

#         top_n = detect_top_n(q, default=5)
#         top = grouped.head(top_n)

#         lines = ["Top revenue branches:", ""]
#         items = []

#         for i, (branch, amt) in enumerate(top.items(), 1):
#             lines.append(f"{i}. {branch} — ${amt:,.0f}")
#             items.append({
#                 "label": str(branch),
#                 "value": float(amt)
#             })

#         return {
#             "title": "Top revenue branches",
#             "text": "\n".join(lines),
#             "items": items,
#             "chart_type": "bar"
#         }

#     # Branch comparison
#     if "compare" in q and "branch" in q:
#         if not branch_col:
#             return {
#                 "title": "Branch comparison",
#                 "text": "No branch column was found in this dataset."
#             }

#         grouped = (
#             pd.DataFrame({"branch": df[branch_col].astype(str), "value": value})
#             .groupby("branch")["value"]
#             .sum()
#             .sort_values(ascending=False)
#         )

#         lines = ["Branch comparison:", ""]
#         items = []

#         for branch, amt in grouped.items():
#             lines.append(f"{branch} — ${amt:,.2f}")
#             items.append({"label": str(branch), "value": float(amt)})

#         return {
#             "title": "Branch comparison",
#             "text": "\n".join(lines),
#             "items": items,
#             "chart_type": "bar"
#         }

#     # Trend by period
#     if "trend" in q or "period" in q or "month" in q:
#         if not period_col:
#             return {
#                 "title": "Revenue by period",
#                 "text": "No period column was found in this dataset."
#             }

#         grouped = (
#             pd.DataFrame({
#                 "period": df[period_col].astype(str),
#                 "value": value
#             })
#             .groupby("period")["value"]
#             .sum()
#         )

#         grouped = safe_period_sort(grouped)

#         lines = ["Revenue by period:", ""]
#         items = []

#         for period, amt in grouped.items():
#             lines.append(f"{period} — ${amt:,.2f}")
#             items.append({
#                 "label": str(period),
#                 "value": float(amt)
#             })

#         return {
#             "title": "Revenue by period",
#             "text": "\n".join(lines),
#             "items": items,
#             "chart_type": "line"
#         }

#     # Largest transactions
#     if "largest" in q or "transactions" in q or "top 10 transactions" in q:
#         work = df.copy()
#         work["value"] = value
#         limit = 10 if "10" in q else 5
#         work = work.sort_values("value", ascending=False).head(limit)

#         lines = ["Largest transactions:", ""]

#         for _, row in work.iterrows():
#             branch = row[branch_col] if branch_col else "N/A"
#             period = row[period_col] if period_col else "N/A"
#             desc = row[desc_col] if desc_col else ""
#             amt = row["value"]
#             lines.append(f"{branch} | {period} | {desc} | ${amt:,.2f}")

#         return {
#             "title": "Largest transactions",
#             "text": "\n".join(lines)
#         }

#     # Executive / insight / CFO mode
#     if any(x in q for x in [
#         "summary",
#         "summarize",
#         "leadership",
#         "insight",
#         "analyst",
#         "cfo",
#         "management",
#         "reviewing",
#         "what stands out",
#         "risk",
#         "risks",
#         "executive"
#     ]):
#         summary = build_executive_summary(df, branch_col, period_col, account_col, value)

#         if mode == "insight":
#             text = format_insight_primary(summary)
#             title = "Executive insights"
#         else:
#             text = format_data_primary(summary)
#             title = "Key financial insights"

#         return {
#             "title": title,
#             "text": text
#         }

#     return {
#         "title": "HELIX analysis",
#         "text": "Try asking about branch revenue, trends, largest transactions, summaries, or executive insights."
#     }


# # -----------------------------
# # PDF ANALYSIS
# # -----------------------------

# def build_pdf_answer(pdf_text: str, question: str, mode: str = "data", source: str = "") -> Dict[str, Any]:
#     if not pdf_text.strip():
#         return {
#             "title": "PDF Answer",
#             "text": "No readable text was extracted from the PDF.",
#             "source": source
#         }

#     q = question.lower().strip()
#     chunks = split_pdf_chunks(pdf_text)

#     if any(x in q for x in ["summary", "summarize", "executive", "overview", "what is this document about"]):
#         snippet = pdf_text[:2500].strip()
#         title = "Executive PDF summary" if mode == "insight" else "PDF summary"
#         return {
#             "title": title,
#             "text": snippet,
#             "source": source
#         }

#     keywords = [w for w in q.replace("?", " ").replace(",", " ").split() if len(w) > 3]
#     scored = []

#     for chunk in chunks:
#         chunk_lower = chunk.lower()
#         score = sum(1 for kw in keywords if kw in chunk_lower)
#         if score > 0:
#             scored.append((score, chunk))

#     scored.sort(key=lambda x: x[0], reverse=True)

#     if scored:
#         top_chunks = [c for _, c in scored[:3]]
#         title = "Executive PDF insights" if mode == "insight" else "PDF Answer"
#         return {
#             "title": title,
#             "text": "\n\n".join(top_chunks),
#             "source": source
#         }

#     return {
#         "title": "PDF Answer",
#         "text": pdf_text[:2000].strip(),
#         "source": source
#     }


# # -----------------------------
# # QUERY
# # -----------------------------

# @app.post("/query")
# async def query(question: str = Form(...), mode: str = Form("data")):
#     current_type = DATASETS.get("current_type", "")

#     if current_type == "csv" and "current" in DATASETS:
#         df = DATASETS["current"]
#         return analyze_dataframe(df, question, mode)

#     if current_type == "pdf" and PDF_TEXT:
#         return build_pdf_answer(PDF_TEXT, question, mode, PDF_SOURCE)

#     return {"error": "No dataset ingested"}