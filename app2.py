import streamlit as st
import os
import pdfplumber
import re
import google.generativeai as genai
import unicodedata
from pdf2image import convert_from_path
import pytesseract

# Optional: set path to tesseract if needed
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Gemini API
genai.configure(api_key="AIzaSyBrWpabmaYMSpSJsM9RrDKPd1JKIr6quyM")
model = genai.GenerativeModel(model_name="gemini-2.0-flash")

st.set_page_config(page_title="Batch PDF Analyzer with Gemini", layout="wide")
st.title("📚 Batch PDF Analyzer with Gemini - With Error Handling")

uploaded_files = st.file_uploader("Upload multiple PDF files (Max 10MB each)", type=["pdf"], accept_multiple_files=True)
MAX_FILE_SIZE = 10 * 1024 * 1024

# -------- Utility Functions -------- #

def extract_pdf_text(pdf_path, txt_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            needs_ocr = False
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text += page_text + "\n"
                else:
                    needs_ocr = True
                    break

        if not text.strip() or needs_ocr:
            images = convert_from_path(pdf_path)
            text = "\n".join([pytesseract.image_to_string(img, lang='eng') for img in images])

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text.strip() if text.strip() else "No text extracted.")
        return text
    except Exception as e:
        raise RuntimeError(f"PDF text extraction failed: {e}")

def preprocess_text(text):
    try:
        text = unicodedata.normalize("NFC", text)
        lines = text.split('\n')
        cleaned_lines = [re.sub(r'\s+', ' ', line).strip() for line in lines]
        cleaned_text = '\n'.join(cleaned_lines)
        paragraphs = [line for line in cleaned_lines if line]
        return cleaned_text, paragraphs if paragraphs else [cleaned_text]
    except Exception as e:
        raise RuntimeError(f"Text preprocessing error: {e}")

def gemini_prompt(prompt_text):
    try:
        return model.generate_content(prompt_text).text.strip()
    except Exception as e:
        raise RuntimeError(f"Gemini API Error: {e}")

# -------- Main Logic -------- #

if uploaded_files:
    os.makedirs("data", exist_ok=True)

    # Dynamic top status
    status_message = st.empty()
    status_message.info(f"📂 Processing {len(uploaded_files)} document(s)...")

    progress = st.progress(0.0)

    for idx, file in enumerate(uploaded_files):
        st.markdown(f"---\n### 📘 Document {idx + 1}: `{file.name}`")
        file_status = st.empty()

        if file.size > MAX_FILE_SIZE:
            file_status.warning("⚠️ Skipped: File exceeds 10MB limit.")
            progress.progress((idx + 1) / len(uploaded_files))
            continue

        with st.spinner("Processing document..."):
            try:
                file_path = os.path.join("data", file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())

                txt_path = os.path.splitext(file_path)[0] + ".txt"
                original_text = extract_pdf_text(file_path, txt_path)
                cleaned_text, paragraphs = preprocess_text(original_text)

                st.subheader("📝 Text Comparison")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Original Text**")
                    st.text_area("Original", original_text, height=250)
                    wc_orig = len(original_text.split())
                    pc_orig = len([p for p in original_text.split('\n') if p.strip()])
                    st.markdown(f"**Words**: {wc_orig}, **Paragraphs**: {pc_orig}")
                with col2:
                    st.markdown("**Cleaned Text**")
                    st.text_area("Cleaned", cleaned_text, height=250)
                    wc_clean = len(cleaned_text.split())
                    pc_clean = len(paragraphs)
                    st.markdown(f"**Words**: {wc_clean}, **Paragraphs**: {pc_clean}")

                st.subheader("🧠 Summary")
                summary = gemini_prompt(f"Summarize this banking/compliance-related document:\n{cleaned_text}")
                st.write(summary)

                st.subheader("📌 Key Compliance Terms")
                key_terms = gemini_prompt(
                    "Extract key compliance terms or important points related to banking, finance, or regulations:\n\n" + cleaned_text)
                st.markdown(key_terms)

                st.subheader("🏷️ Keywords")
                keyword_text = gemini_prompt(
                    "Extract keywords from the following document. One keyword per line:\n\n" + cleaned_text)
                keywords = sorted(set([kw.strip().lower() for kw in keyword_text.split('\n') if len(kw.strip()) > 1]))
                search_term = st.text_input(f"Search keywords for `{file.name}`", key=file.name)
                filtered_keywords = [kw for kw in keywords if search_term.lower() in kw]
                if filtered_keywords:
                    st.markdown("### Tags:")
                    st.markdown(" ".join([f"`{kw}`" for kw in filtered_keywords]), unsafe_allow_html=True)
                else:
                    st.info("No matching keywords found." if search_term else "No keywords extracted.")

                st.subheader("📋 Requirements")
                requirements = gemini_prompt(
                    "Extract all mandatory requirements as numbered list:\n\n" + cleaned_text)
                st.markdown(requirements)

                for content, label, suffix in [
                    (key_terms, "⬇️ Download Key Terms", "_key_compliance_terms.txt"),
                    ("\n".join(keywords), "⬇️ Download Keywords", "_keywords.txt"),
                    (requirements, "⬇️ Download Requirements", "_requirements.txt"),
                    (cleaned_text, "⬇️ Download Cleaned Text", "_cleaned.txt")
                ]:
                    out_path = os.path.splitext(file_path)[0] + suffix
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    with open(out_path, "rb") as f:
                        st.download_button(label, f, file_name=os.path.basename(out_path), mime="text/plain")

                # ✅ Mark success for this file
                file_status.success("✅ Processed successfully.")

            except Exception as e:
                file_status.error(f"❌ Error: {str(e)}")

        progress.progress((idx + 1) / len(uploaded_files))

    status_message.success("✅ All documents processed!")
