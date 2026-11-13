
import os, re, io, json, base64, hashlib
from datetime import datetime
import streamlit as st
import fitz
import pandas as pd
from PIL import Image
from openai import OpenAI

st.set_page_config(page_title="Wonder Learning | 10X Book Audit", page_icon="📚", layout="wide")

st.markdown("""
<style>
.block-container {padding-top:1.2rem; padding-bottom:2rem; max-width:1450px;}
.main-title {font-size:2rem;font-weight:800;color:#174A72;line-height:1.15}
.subtle {color:#667085}
.metric-card {background:#F4F7FA;border:1px solid #E1E8EF;border-radius:12px;padding:14px}
div[data-testid="stMetric"] {background:#F4F7FA;border:1px solid #E1E8EF;padding:12px;border-radius:12px}
.stButton button {border-radius:9px}
@media (max-width: 700px) {.main-title{font-size:1.5rem}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">Wonder Learning</div>', unsafe_allow_html=True)
st.subheader("10X Preschool Book Quality Audit")
st.caption("Version 1.0 · AI-assisted audit + human verification · Mobile & Laptop Web App")

with st.sidebar:
    st.header("⚙️ Audit Settings")
    age_group = st.selectbox("Target age group", ["2–3 years (Playgroup)", "3–4 years (Nursery)", "4–5 years (LKG)", "5–6 years (UKG)", "2–6 years (All preschool)"])
    language = st.selectbox("Book language", ["English", "Hindi", "Marathi", "Bilingual", "Other"])
    book_type = st.selectbox("Book type", ["Concept Book", "Activity Book", "Workbook", "Phonics Book", "EVS Book", "Curriculum Book", "Other"])
    book_size = st.text_input("Book size (optional)", placeholder="e.g. 8.5 × 11.25 inches")
    framework = st.selectbox("Curriculum reference", ["NEP 2020 / NCF 2023 (where applicable)", "NCF 2023", "NEP 2020", "Not specified"])
    st.divider()
    st.caption("AI visual/content audit requires an OpenAI API key. The app also provides PDF inspection and manual review without a key.")
    api_key = st.text_input("OpenAI API key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    model = st.text_input("Vision-capable model", value=os.getenv("OPENAI_MODEL", "gpt-4.1"))
    st.caption("Keep your API key private. Do not share it in screenshots or reports.")

if "issues" not in st.session_state: st.session_state.issues = []
if "audit_meta" not in st.session_state: st.session_state.audit_meta = {}
if "pdf_hash" not in st.session_state: st.session_state.pdf_hash = ""

def priority_from_severity(s):
    return {"Critical":"P0","High":"P1","Medium":"P2","Low":"P3"}.get(s,"P2")

def render_page(doc, idx, zoom=1.3):
    page = doc.load_page(idx)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("png")))

def extract_page_text(page):
    return page.get_text("text").strip()

def add_issue(page_no, category, issue, evidence="", severity="Medium", recommendation="", source="Rule-based", status="Pending"):
    st.session_state.issues.append({
        "PDF Page": page_no, "Printed Page": "", "Category": category,
        "Issue": issue, "Evidence / Original Text": evidence,
        "Severity": severity, "Priority": priority_from_severity(severity),
        "Recommended Correction": recommendation, "Source": source,
        "Verification Status": status, "Reviewer Notes": ""
    })

def ai_page_audit(client, image, page_text, page_no):
    buff = io.BytesIO()
    image.save(buff, format="JPEG", quality=78)
    img64 = base64.b64encode(buff.getvalue()).decode("utf-8")
    prompt = f"""
You are a senior preschool publishing QA auditor. Audit PDF page {page_no} for a {book_type} for age group {age_group}; language: {language}; curriculum reference: {framework}.
Inspect BOTH the page image and extracted text. Report only evidence-supported issues. Separate confirmed errors from subjective suggestions.
Check spelling/grammar, factual and educational accuracy, image-text match, illustration clarity, age appropriateness, child safety, layout/alignment, colour contrast, typography/readability, page numbering clues and print risks visible in the image.
Do not infer DPI, CMYK, font embedding, bleed or other PDF metadata from appearance. Say these require technical verification.
Return ONLY valid JSON with this schema:
{{"issues":[{{"category":"Spelling & Grammar | Content Accuracy | Image Accuracy | Image-Text Match | Design & Layout | Colour | Typography | Age Appropriateness | Child Safety | Pagination | Other","issue":"short precise issue","evidence":"exact visible text or visual evidence","severity":"Critical | High | Medium | Low","recommendation":"specific correction"}}],"page_summary":"one concise sentence","not_verifiable":["..."]}}
If no issue is confirmed, return an empty issues array. Do not invent mistakes.
Extracted text:
{page_text[:7000]}
"""
    response = client.responses.create(
        model=model,
        input=[{"role":"user","content":[
            {"type":"input_text","text":prompt},
            {"type":"input_image","image_url":f"data:image/jpeg;base64,{img64}"}
        ]}],
        max_output_tokens=1800
    )
    raw = response.output_text.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I)
    return json.loads(raw)

uploaded = st.file_uploader("Upload a preschool book PDF", type=["pdf"], help="Recommended: one book per audit. The app supports page-by-page processing.")
if uploaded:
    data = uploaded.getvalue()
    digest = hashlib.sha256(data).hexdigest()
    if digest != st.session_state.pdf_hash:
        st.session_state.issues = []
        st.session_state.audit_meta = {}
        st.session_state.pdf_hash = digest
    try:
        pdf = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        st.error(f"Could not open this PDF: {e}")
        st.stop()

    page_count = len(pdf)
    meta = pdf.metadata or {}
    st.session_state.audit_meta = {"filename":uploaded.name, "pages":page_count, "age_group":age_group, "language":language, "book_type":book_type, "book_size":book_size, "framework":framework, "uploaded_at":datetime.now().isoformat(timespec="minutes")}
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("PDF pages", page_count)
    c2.metric("File size", f"{len(data)/1024/1024:.1f} MB")
    c3.metric("Text-bearing pages", sum(bool(extract_page_text(p)) for p in pdf))
    c4.metric("Audit findings", len(st.session_state.issues))
    st.info("PDF page index and printed page number are tracked separately. Printed page numbers must be visually verified; they are not assumed from PDF order.")

    tabs = st.tabs(["📄 Page Inspection", "🤖 AI Audit", "🧑‍💼 Manual Verification", "📊 Reports & Export", "🛠 Technical Checks"])
    with tabs[0]:
        left,right = st.columns([1,2])
        with left:
            selected = st.number_input("Select PDF page", min_value=1, max_value=page_count, value=1, step=1)
            zoom = st.select_slider("Preview size", options=[0.8,1.0,1.3,1.6,2.0], value=1.3)
            page = pdf.load_page(int(selected)-1)
            txt = extract_page_text(page)
            st.markdown("**Extracted text**")
            st.text_area("Text on selected page", txt or "[No selectable text detected – visual/OCR inspection needed]", height=320, label_visibility="collapsed")
        with right:
            st.image(render_page(pdf, int(selected)-1, zoom), caption=f"PDF page {selected}", use_container_width=True)
        st.caption("Visual preview is the source of truth for layout. Extracted text may contain OCR/encoding errors; compare it with the rendered page.")

    with tabs[1]:
        st.markdown("#### AI-assisted page audit")
        if not api_key:
            st.warning("Enter your OpenAI API key in the sidebar to enable AI text + image auditing. PDF preview, technical checks and manual review remain available.")
        else:
            start_col,end_col = st.columns(2)
            with start_col: start_page = st.number_input("Start page",1,page_count,1,key="ai_start")
            with end_col: end_page = st.number_input("End page",int(start_page),page_count,min(page_count,int(start_page)+4),key="ai_end")
            st.caption("Process a small batch first to review quality and API cost. Each page sends its rendered image and extracted text to the AI model.")
            if st.button("Run AI audit for selected pages", type="primary"):
                client = OpenAI(api_key=api_key)
                progress = st.progress(0)
                status = st.empty()
                for n in range(int(start_page),int(end_page)+1):
                    status.write(f"Auditing page {n} of {end_page}…")
                    pg = pdf.load_page(n-1)
                    try:
                        result = ai_page_audit(client, render_page(pdf,n-1,1.15), extract_page_text(pg), n)
                        for item in result.get("issues",[]):
                            add_issue(n,item.get("category","Other"),item.get("issue",""),item.get("evidence",""),item.get("severity","Medium"),item.get("recommendation",""),"AI-assisted")
                        if result.get("not_verifiable"):
                            for item in result["not_verifiable"]:
                                add_issue(n,"Technical / Verification",f"Not verifiable from page image: {item}","", "Low","Verify using source artwork/PDF preflight or printer specification.","AI note")
                    except Exception as e:
                        add_issue(n,"AI Audit Error",str(e),"","High","Check API key, model access, network and retry.","System")
                    progress.progress((n-int(start_page)+1)/(int(end_page)-int(start_page)+1))
                status.success("Selected page audit completed. Review all findings before accepting them.")
                st.rerun()

    with tabs[2]:
        st.markdown("#### Manual verification")
        st.caption("Review every finding. AI suggestions are not automatically treated as confirmed errors.")
        if st.session_state.issues:
            df = pd.DataFrame(st.session_state.issues)
            edited = st.data_editor(df, use_container_width=True, hide_index=True, num_rows="dynamic",
                column_config={
                    "Verification Status": st.column_config.SelectboxColumn(options=["Pending","Accepted","Rejected","Corrected","Needs Designer Review"]),
                    "Severity": st.column_config.SelectboxColumn(options=["Critical","High","Medium","Low"]),
                    "Reviewer Notes": st.column_config.TextColumn(),
                    "Recommended Correction": st.column_config.TextColumn(width="large")
                }, key="issue_editor")
            if st.button("Save manual verification changes"):
                st.session_state.issues = edited.to_dict("records")
                st.success("Review changes saved for this session.")
        else:
            st.info("No findings yet. Run AI audit or add manual findings below.")
        with st.expander("Add a manual finding"):
            with st.form("manual_issue"):
                pno = st.number_input("PDF page",1,page_count,1)
                cat = st.selectbox("Category",["Spelling & Grammar","Content Accuracy","Image Accuracy","Image-Text Match","Design & Layout","Colour","Typography","Age Appropriateness","Child Safety","Pagination","Technical"])
                issue = st.text_input("Issue")
                evidence = st.text_area("Evidence / Original text")
                sev = st.selectbox("Severity",["Critical","High","Medium","Low"])
                rec = st.text_area("Recommended correction")
                if st.form_submit_button("Add finding"):
                    add_issue(int(pno),cat,issue,evidence,sev,rec,"Manual")
                    st.success("Manual finding added.")
                    st.rerun()

    with tabs[3]:
        issues_df = pd.DataFrame(st.session_state.issues)
        if len(issues_df):
            total=len(issues_df); pending=int((issues_df["Verification Status"]=="Pending").sum())
            critical=int((issues_df["Priority"]=="P0").sum())
            accepted=int((issues_df["Verification Status"]=="Accepted").sum())
        else: total=pending=critical=accepted=0
        a,b,c,d = st.columns(4)
        a.metric("Total findings",total); b.metric("Pending",pending); c.metric("Critical P0",critical); d.metric("Accepted",accepted)
        st.markdown("#### Audit status")
        if not len(issues_df):
            st.info("No findings recorded yet.")
        else:
            st.dataframe(issues_df, use_container_width=True, hide_index=True)
            csv = issues_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("Download correction sheet (CSV)",csv,file_name="book_correction_sheet.csv",mime="text/csv")
            xbuf=io.BytesIO()
            with pd.ExcelWriter(xbuf,engine="openpyxl") as writer:
                issues_df.to_excel(writer,index=False,sheet_name="Correction Sheet")
                pd.DataFrame([st.session_state.audit_meta]).to_excel(writer,index=False,sheet_name="Book Details")
            st.download_button("Download correction sheet (Excel)",xbuf.getvalue(),file_name="book_correction_sheet.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.download_button("Download audit data (JSON)",json.dumps({"book":st.session_state.audit_meta,"findings":st.session_state.issues},ensure_ascii=False,indent=2).encode("utf-8"),file_name="book_audit.json",mime="application/json")
        st.markdown("#### Publishing decision")
        pending_now = sum(1 for x in st.session_state.issues if x.get("Verification Status")=="Pending")
        p0_now = sum(1 for x in st.session_state.issues if x.get("Priority")=="P0")
        if p0_now or pending_now:
            st.error("NOT READY FOR PRINT – critical or unverified findings remain.")
        elif total:
            st.warning("REQUIRES HUMAN REVIEW – verify corrections against the revised PDF before approval.")
        else:
            st.info("No findings recorded is not proof of a clean book. Complete all page inspections and technical preflight before approval.")

    with tabs[4]:
        st.markdown("#### PDF-level technical preflight")
        rows=[]
        for i,p in enumerate(pdf):
            rect=p.rect
            images=p.get_images(full=True)
            rows.append({"PDF Page":i+1,"Width (pt)":round(rect.width,1),"Height (pt)":round(rect.height,1),"Orientation":"Landscape" if rect.width>rect.height else "Portrait","Embedded image objects":len(images),"Selectable text":bool(extract_page_text(p))})
        tech=pd.DataFrame(rows)
        st.dataframe(tech,use_container_width=True,hide_index=True)
        st.download_button("Download technical preflight (CSV)",tech.to_csv(index=False).encode("utf-8-sig"),"technical_preflight.csv","text/csv")
        st.warning("This first version reports page geometry, image-object counts and selectable text. It does not certify effective DPI, CMYK, font embedding, bleed or printer-specific compliance. Use a professional PDF preflight tool and confirm specifications with the printer.")
else:
    st.markdown("### Start a new book audit")
    st.write("Upload one PDF to inspect pages, run AI-assisted checks, record manual corrections and export a correction sheet.")
    st.markdown("""
    **Recommended workflow**
    1. Upload the book PDF.
    2. Inspect page previews and extracted text.
    3. Run AI audit in small batches (start with 3–5 pages).
    4. Verify every AI finding manually.
    5. Add designer/editor observations.
    6. Export Excel correction sheet.
    7. Upload the corrected PDF in a new session and repeat the audit.
    """)
    st.info("Version 1.0 is a working MVP. Project history, multi-user login, cloud database, automatic OCR for scanned PDFs and annotated page-level markup are planned for later versions.")

st.divider()
st.caption("Wonder Learning · 10X Preschool Book Quality Audit · Version 1.0 | AI output is advisory and requires human verification.")
