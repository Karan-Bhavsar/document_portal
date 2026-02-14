# import sys
# import fitz
# from pathlib import Path
# from logger.custom_logger import CustomLogger
# from exception.custom_exception import DocumentPortalException

# class DocumentIngestion:

#     def __init__(self, base_dir:str="C:\\Users\\Karan\\document_portal\\data\\document_compare"):
#         self.log = CustomLogger().get_logger(__name__)
#         self.base_dir = Path(base_dir)
#         self.base_dir.mkdir(parents=True,exist_ok= True)

#     def delete_existing_files(self):
    
#         try:
#             if self.base_dir.exists() and self.base_dir.is_dir():
#                 for file in self.base_dir.iterdir():
#                     if file.is_file():
#                         file.unlink()
#                         self.log.info("File deleted", path=str(file))

#             self.log.info("Directory cleaned", directory=str(self.base_dir))
#         except Exception as e:
#             self.log.error(f"Error deleting PDF: {e}") 
#             raise DocumentPortalException(
#                 "An error occurred while deleting the file", sys
#             )
#     def save_uploaded_files(self, reference_file, actual_file):
#         try:
#             self.delete_existing_files()
#             self.log.info("Existing files deleted successfully.")
#             ref_path = self.base_dir / reference_file.name
#             act_path = self.base_dir / actual_file.name

#             if not reference_file.name.endswith(".pdf") or not actual_file.name.endswith(".pdf"):
#                 raise ValueError("Only PDF files are allowed.")
#             with open(ref_path, "wb") as f:
#                 f.write(reference_file.getbuffer())
#             with open(act_path, "wb") as f:
#                 f.write(actual_file.getbuffer())
#             self.log.info(
#                     "PDF saved successfully",
#                     reference=str(ref_path),
#                     actual=str(act_path)
#                     )    
#             return ref_path,act_path
        
#         except Exception as e:
#             self.log.error(f"Error uploading PDF: {e}") 
#             raise DocumentPortalException(
#                 "An error occurred while uploading the file", sys
#             )
#     def read_pdf(self, pdf_path: Path) ->str:
#         try:
#             with fitz.open(pdf_path) as doc:
#                 if doc.is_encrypted:
#                     raise ValueError(f"pdf is encrypted:{pdf_path.name}")
#                 all_text = []
#                 for page_num in range(doc.page_count):
#                     page = doc.load_page(page_num)
#                     text = page.get_text()  # type: ignore
#                     if text.strip():
#                         all_text.append(f"\n --- Page {page_num + 1} --- \n{text}")
#                 self.log.info(
#                     "PDF read successfully",
#                     file=str(pdf_path),
#                     pages=len(all_text)
#                     )

#                 return "\n".join(all_text)
                
#         except Exception as e:
#             self.log.error(f"Error reading PDF: {e}") 
#             raise DocumentPortalException(
#                 "An error occurred while reading the file", sys
#             )
        
#     def combine_documents(self) -> str:
#         try:
#             content_dict = {}
#             doc_parts = []

#             # Read all PDF files from base directory
#             for filename in sorted(self.base_dir.iterdir()):
#                 if filename.is_file() and filename.suffix == ".pdf":
#                     content_dict[filename.name] = self.read_pdf(filename)

#             # Combine contents with document names
#             for filename, content in content_dict.items():
#                 doc_parts.append(f"Document: {filename}\n{content}")

#             # Join all documents into one text
#             combined_text = "\n\n".join(doc_parts)

#             self.log.info("Documents combined", count=len(doc_parts))
#             return combined_text
#         except Exception as e:
#             self.log.error(f"Error Combining PDF: {e}") 
#             raise DocumentPortalException(
#                 "An error occurred while combining the pdf", sys
#             )


import sys
import fitz
import uuid
from datetime import datetime
from pathlib import Path
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

class DocumentIngestion:
    def __init__(self, base_dir: str = "C:\\Users\\Karan\\document_portal\\data\\document_compare"):
        self.log = CustomLogger().get_logger(__name__)
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.session_id = None
        self.session_dir = None

    def create_session(self) -> tuple[str, Path]:
        try:
            session_id = f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            session_dir = self.base_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            self.session_id = session_id
            self.session_dir = session_dir

            self.log.info("Session created", session_id=session_id, session_dir=str(session_dir))
            return session_id, session_dir
        except Exception as e:
            self.log.error(f"Error creating session: {e}")
            raise DocumentPortalException("An error occurred while creating the session", sys)

    def save_uploaded_files(self, reference_file, actual_file):
        try:
            # Create a new session for every upload/compare run
            if self.session_dir is None:
                self.create_session()

            if not reference_file.name.endswith(".pdf") or not actual_file.name.endswith(".pdf"):
                raise ValueError("Only PDF files are allowed.")

            ref_path = self.session_dir / reference_file.name
            act_path = self.session_dir / actual_file.name

            with open(ref_path, "wb") as f:
                f.write(reference_file.getbuffer())

            with open(act_path, "wb") as f:
                f.write(actual_file.getbuffer())

            self.log.info("PDFs saved successfully", reference=str(ref_path), actual=str(act_path))
            return ref_path, act_path, self.session_id, self.session_dir

        except Exception as e:
            self.log.error(f"Error uploading PDF: {e}")
            raise DocumentPortalException("An error occurred while uploading the file", sys)

    def read_pdf(self, pdf_path: Path) -> str:
        try:
            with fitz.open(pdf_path) as doc:
                if doc.is_encrypted:
                    raise ValueError(f"pdf is encrypted:{pdf_path.name}")
                all_text = []
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    text = page.get_text()  # type: ignore
                    if text.strip():
                        all_text.append(f"\n --- Page {page_num + 1} --- \n{text}")

                self.log.info("PDF read successfully", file=str(pdf_path), pages=len(all_text))
                return "\n".join(all_text)

        except Exception as e:
            self.log.error(f"Error reading PDF: {e}")
            raise DocumentPortalException("An error occurred while reading the file", sys)

    def combine_documents(self) -> str:
        try:
            if self.session_dir is None:
                raise ValueError("Session not created. Call save_uploaded_files() first.")

            content_dict = {}
            doc_parts = []

            for filename in sorted(self.session_dir.iterdir()):
                if filename.is_file() and filename.suffix == ".pdf":
                    content_dict[filename.name] = self.read_pdf(filename)

            for filename, content in content_dict.items():
                doc_parts.append(f"Document: {filename}\n{content}")

            combined_text = "\n\n".join(doc_parts)
            self.log.info("Documents combined", count=len(doc_parts), session_id=self.session_id)
            return combined_text

        except Exception as e:
            self.log.error(f"Error Combining PDF: {e}")
            raise DocumentPortalException("An error occurred while combining the pdf", sys)
