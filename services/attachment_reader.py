import os
import pdfplumber
from docx import Document
from PIL import Image
import pytesseract
import pandas as pd

# Tesseract Path
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Allowed Extensions
ALLOWED_EXTENSIONS = [
    ".pdf",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".xlsx",
    ".xls",
    ".dwg"
]

# 5 MB Limit
MAX_FILE_SIZE = 5 * 1024 * 1024


def is_valid_attachment(file_path):

    if not os.path.exists(file_path):
        return False

    extension = (
        os.path.splitext(file_path)[1]
        .lower()
    )

    if extension not in ALLOWED_EXTENSIONS:
        return False

    file_size = os.path.getsize(
        file_path
    )

    if file_size > MAX_FILE_SIZE:
        return False

    return True


def extract_pdf_text(file_path):

    text = ""

    try:

        with pdfplumber.open(
            file_path
        ) as pdf:

            for page in pdf.pages:

                page_text = (
                    page.extract_text()
                )

                if page_text:
                    text += (
                        page_text + "\n"
                    )

    except Exception as e:

        print(
            f"PDF Error: {e}"
        )

    return text


def extract_docx_text(file_path):

    text = ""

    try:

        document = Document(
            file_path
        )

        for para in document.paragraphs:

            text += (
                para.text + "\n"
            )

    except Exception as e:

        print(
            f"DOCX Error: {e}"
        )

    return text

def extract_excel_text(file_path):

    text = ""

    try:

        df = pd.read_excel(
            file_path,
            dtype=str
        )

        text = df.fillna("").to_string(
            index=False
        )

    except Exception as e:

        print(
            f"Excel Error: {e}"
        )

    return text



def extract_image_text(file_path):

    try:

        image = Image.open(
            file_path
        )

        text = (
            pytesseract
            .image_to_string(
                image
            )
        )

        return text

    except Exception as e:

        print(
            f"OCR Error: {e}"
        )

    return ""


def extract_attachment_text(
    file_path
):

    if not is_valid_attachment(
        file_path
    ):

        print(
            "Invalid Attachment"
        )

        return ""

    extension = (
        os.path.splitext(
            file_path
        )[1]
        .lower()
    )

    if extension == ".pdf":

        return extract_pdf_text(
            file_path
        )

    elif extension == ".docx":

        return extract_docx_text(
            file_path
        )

    elif extension in [
        ".png",
        ".jpg",
        ".jpeg"
    ]:

        return extract_image_text(
            file_path
        )

    elif extension in [
        ".xlsx",
        ".xls"
    ]:

        return extract_excel_text(
            file_path
        )

    elif extension == ".dwg":

        print(
            "DWG File Detected"
        )

        return ""

    return ""


if __name__ == "__main__":

    file_path = input(
        "Enter File Path: "
    )

    text = (
        extract_attachment_text(
            file_path
        )
    )

    print(
        "\nExtracted Text:\n"
    )

    print(text)