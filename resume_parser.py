import pdfplumber
import docx
import io

def extract_text(uploaded_file):
    filename = uploaded_file.name

    if filename.endswith(".pdf"):
        text = ""
        with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text

    elif filename.endswith(".docx"):
        doc = docx.Document(io.BytesIO(uploaded_file.read()))
        return "\n".join([p.text for p in doc.paragraphs])

    return "Unsupported file format"
