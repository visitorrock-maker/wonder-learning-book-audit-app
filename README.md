# Wonder Learning – 10X Preschool Book Audit (Version 1.0)

## What this MVP does
- Responsive Streamlit web application for laptop and mobile browsers.
- Upload and preview PDF pages.
- Extract selectable PDF text page-by-page.
- AI-assisted visual + text audit using an OpenAI vision-capable model and your API key.
- Manual verification: Pending / Accepted / Rejected / Corrected / Needs Designer Review.
- Add manual findings.
- Export correction sheet to Excel/CSV and audit data to JSON.
- Basic technical preflight: page dimensions, orientation, image-object count and selectable-text presence.

## Important limitations
This is a first working MVP, not a certified publishing preflight system.
- AI audit requires your own OpenAI API key and may incur API charges.
- Start with 3–5 pages to validate output and cost before processing a full book.
- Scanned PDFs with no selectable text may need OCR; visual AI inspection still receives the rendered page image.
- Effective DPI, CMYK profile, font embedding, bleed and printer-specific compliance are NOT certified in v1.0.
- No cloud project history, user login, team collaboration or persistent database yet. Findings remain in the active app session; download the Excel/JSON outputs.
- Human verification is required before a print approval.

## Run locally (Windows / Mac)
1. Install Python 3.10 or newer.
2. Extract this ZIP.
3. Open a terminal in the extracted folder.
4. Run:
   `python -m venv .venv`
5. Activate it:
   Windows: `.venv\Scripts\activate`
   Mac/Linux: `source .venv/bin/activate`
6. Install packages:
   `pip install -r requirements.txt`
7. Start:
   `streamlit run app.py`
8. Open the local URL shown in the terminal (usually http://localhost:8501).

## AI setup
- Enter your OpenAI API key in the sidebar at runtime, or set OPENAI_API_KEY as an environment variable.
- The default model field is `gpt-4.1`; use a vision-capable model available to your API account.
- Never publish your API key in source code or share screenshots containing it.

## Deploy as a web app
This project can be deployed to Streamlit Community Cloud or another Python hosting provider:
- Upload `app.py` and `requirements.txt` to a private GitHub repository.
- Create a Streamlit app pointing to `app.py`.
- Add `OPENAI_API_KEY` and optionally `OPENAI_MODEL` as hosting secrets.
- Restrict access if the uploaded books are confidential.

## Included files
- app.py – application
- requirements.txt – Python dependencies
- README.md – setup and deployment guide
