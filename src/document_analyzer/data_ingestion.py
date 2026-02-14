import os
import sys
import fitz
import uuid
from datetime import datetime
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

class DocumentHandler:
    def __init__(self, data_dir=None, session_id=None):
        try:
            self.log = CustomLogger().get_logger(__name__)

            base_dir = (
                data_dir
                or os.getenv("DATA_STORAGE_PATH")
                or os.path.join(os.getcwd(), "data", "document_analysis")
            )

            # Create session id
            self.session_id = session_id or (
                f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            )

            # Create session folder path
            self.data_dir = os.path.join(base_dir, self.session_id)

            # Create the session folder
            os.makedirs(self.data_dir, exist_ok=True)

            self.log.info("DocumentHandler initialized", data_dir=self.data_dir, session_id=self.session_id)

        except Exception as e:
            print("Initialization failed:", str(e))
            raise DocumentPortalException("Failed to initialize DocumentHandler", e)

    def save_pdf(self, uploaded_file) -> str:
        """
        Saves uploaded PDF file inside session directory.
        Returns saved file path.
        Works with Streamlit / FastAPI UploadFile.
        """
        try:
            # Get original filename
            filename = os.path.basename(uploaded_file.name)

            # Validate extension
            if not filename.lower().endswith(".pdf"):
                raise DocumentPortalException("Invalid file type. Only PDF files are allowed.")

            # Ensure session folder exists
            os.makedirs(self.data_dir, exist_ok=True)

            # Save path inside session directory
            save_path = os.path.join(self.data_dir, filename)

            # Write file
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Logging
            self.log.info(
                "PDF saved successfully",
                filename=filename,
                save_path=save_path,
                session_id=self.session_id
            )

            return save_path

        except Exception as e:
            self.log.error("Error saving PDF", error=str(e))
            raise DocumentPortalException("Failed to save PDF", e)

    def read_pdf(self, pdf_path: str) -> str:
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError("PDF file not found")

            text_chunks = []

            with fitz.open(pdf_path) as doc:
                for page_num, page in enumerate(doc, start=1):
                    text_chunks.append(
                        f"\n--- Page {page_num} ---\n{page.get_text()}"
                    )

            text = "\n".join(text_chunks)

            self.log.info(
                "PDF read successfully",
                pdf_path=pdf_path,
                session_id=self.session_id
            )

            return text

        except Exception as e:
            self.log.error(
                "Error reading PDF",
                error=str(e),
                pdf_path=pdf_path,
                session_id=self.session_id
            )
            raise DocumentPortalException("Error reading PDF", sys)

    # --------------------------------------------------
    # Delete PDF (optional utility)
    # --------------------------------------------------
    def delete_pdf(self, pdf_path: str):
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                self.log.info("PDF deleted", file_path=pdf_path)
        except Exception as e:
            self.log.error("Error deleting PDF", error=str(e))
            raise DocumentPortalException("Failed to delete PDF", e)


if __name__ == '__main__':
    from pathlib import Path
    from io import BytesIO

    handler = DocumentHandler()

    pdf_path = "C:\\Users\\Karan\\document_portal\\data\\document_analysis\\NIPS-2017-attention-is-all-you-need-Paper.pdf"

    class Dummyfile:
        def __init__(self, file_path):
            self.name = Path(file_path).name
            self.file_path = file_path

        def getbuffer(self):
            return open(self.file_path, 'rb').read()

    dummy_file = Dummyfile(pdf_path)
    handler = DocumentHandler(session_id='test_session')

    try:
        save_path = handler.save_pdf(dummy_file)
        print(save_path)
        content = handler.read_pdf(save_path)
        print(content[:500])
    except Exception as e:
        print(f'Error:{e}')
