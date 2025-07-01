import streamlit as st
import os
import pdfplumber
import re
import google.generativeai as genai

# Page setup
st.title("📄 PDF Text Analyzer with Gemini")

uploaded_file = st.file_uploader("Upload a PDF file (max 10MB)", type=["pdf"])
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Configure Gemini API
genai.configure(api_key="AIzaSyBr_-UymcVSddETUssf6RSNIVjoZlBa6r8")  # Replace with your API key
model = genai.GenerativeModel(model_name="gemini-2.0-flash")

# Extract text from PDF
def extract_pdf_text(pdf_path, txt_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
            with open(txt_path, "w", encoding="utf-8") as txt_file:
                txt_file.write(text.strip() if text.strip() else "No text could be extracted.")
            return text
    except Exception as e:
        return f"Error extracting text: {str(e)}"

# Clean and structure the text
def preprocess_text(text):
    if isinstance(text, str) and text:
        lines = text.split('\n')
        cleaned_lines = [re.sub(r'\s+', ' ', line.strip()) for line in lines if line.strip()]
        cleaned_text = '\n'.join(cleaned_lines)
        cleaned_text = re.sub(r'[•\-](?=\s)|[^\w\s\.\,\:\-]', '', cleaned_text)
        paragraphs = [p.strip() for p in cleaned_text.split('\n') if p.strip()]
        return cleaned_text, paragraphs if paragraphs else [cleaned_text]
    return text, [text] if text else ["No text available"]

# Summarize using Gemini
def summarize_text(text):
    try:
        prompt = f"Summarize this banking/compliance-related document:\n{text}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error summarizing text: {str(e)}"

# Extract key compliance terms
def extract_compliance_terms(text):
    try:
        prompt = (
            "From the following document, extract all key compliance terms or important points relevant to banking, finance, or regulations. "
            "Present them clearly as bullet points or structured items:\n\n" + text
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error extracting key terms: {str(e)}"

# Extract keywords
def extract_keywords(text):
    try:
        prompt = (
            "Extract important keywords and key compliance-related terms from the following document. "
            "Return them as a simple list, one keyword or phrase per line, without numbering or bullets:\n\n" + text
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error extracting keywords: {str(e)}"

# Extract requirements
def extract_requirements(text):
    try:
        prompt = "Extract all mandatory requirements from this text. Present them as a numbered list:\n\n" + text
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error extracting requirements: {str(e)}"

# Main app logic
if uploaded_file is not None:
    file_size = uploaded_file.size
    if file_size <= MAX_FILE_SIZE:
        st.write(f"**File Name**: {uploaded_file.name}")
        st.write(f"**File Size**: {file_size / 1024 / 1024:.2f} MB")

        os.makedirs("data", exist_ok=True)
        pdf_path = os.path.join("data", uploaded_file.name)
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        txt_path = os.path.splitext(pdf_path)[0] + ".txt"
        original_text = extract_pdf_text(pdf_path, txt_path)

        cleaned_text, paragraphs = preprocess_text(original_text)
        cleaned_txt_path = os.path.splitext(pdf_path)[0] + "_cleaned.txt"
        with open(cleaned_txt_path, "w", encoding="utf-8") as f:
            f.write(cleaned_text)

        st.success("PDF uploaded and processed successfully!")
        st.write(f"Text saved to: `{cleaned_txt_path}`")

        # Show original and cleaned text
        st.subheader("📃 Text Comparison")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Original Text**")
            st.text_area("Original", original_text, height=300)
            wc_orig = len(" ".join(original_text.split()).split())
            pc_orig = len([p for p in original_text.split('\n') if p.strip()])
            st.write(f"Words: {wc_orig}, Paragraphs: {pc_orig}")
        with col2:
            st.markdown("**Cleaned Text**")
            st.text_area("Cleaned", cleaned_text, height=300)
            wc_clean = len(cleaned_text.split())
            pc_clean = len(paragraphs)
            st.write(f"Words: {wc_clean}, Paragraphs: {pc_clean}")

        # --- Step 1: Summary ---
        st.subheader("🧠 AI Summary of Document")
        summary = summarize_text(cleaned_text)
        st.write("**Summary:**")
        st.write(summary)

        # --- Step 2: Key Compliance Terms ---
        st.subheader("📌 Key Compliance Terms & Important Points")
        key_terms = extract_compliance_terms(cleaned_text)
        st.markdown("### Extracted Terms:")
        st.markdown(key_terms)

        terms_path = os.path.splitext(pdf_path)[0] + "_key_compliance_terms.txt"
        with open(terms_path, "w", encoding="utf-8") as f:
            f.write(key_terms)
        with open(terms_path, "rb") as f:
            st.download_button("⬇️ Download Key Compliance Info", f, file_name="key_compliance_terms.txt", mime="text/plain")

        # --- Step 3: Keywords as Tags ---
        st.subheader("🏷️ Extracted Keywords")
        keyword_text = extract_keywords(cleaned_text)
        keywords = [kw.strip().lower() for kw in keyword_text.split('\n') if len(kw.strip()) > 1]
        keywords = sorted(set(keywords))  # Deduplicate
        search_term = st.text_input("Search keywords")
        filtered_keywords = [kw for kw in keywords if search_term.lower() in kw]
        if filtered_keywords:
            st.markdown("### Tags:")
            st.markdown(" ".join([f"`{kw}`" for kw in filtered_keywords]), unsafe_allow_html=True)
        else:
            st.info("No matching keywords found." if search_term else "No keywords extracted.")
        keyword_file_path = os.path.splitext(pdf_path)[0] + "_keywords.txt"
        with open(keyword_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(keywords))
        with open(keyword_file_path, "rb") as f:
            st.download_button("⬇️ Download Keywords", f, file_name="keywords.txt", mime="text/plain")

        # --- Step 4: Requirements Extraction ---
        st.subheader("📋 Extracted Compliance Requirements")
        requirements = extract_requirements(cleaned_text)
        st.markdown("### Mandatory Requirements:")
        st.markdown(requirements)

        requirements_path = os.path.splitext(pdf_path)[0] + "_requirements.txt"
        with open(requirements_path, "w", encoding="utf-8") as f:
            f.write(requirements)
        with open(requirements_path, "rb") as f:
            st.download_button("⬇️ Download Requirements", f, file_name="requirements.txt", mime="text/plain")

    else:
        st.error("File size exceeds the 10MB limit.")