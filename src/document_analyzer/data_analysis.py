import os
import sys
import json
import re
from typing import Any, Dict

from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from model.models import *
from langchain_core.output_parsers import JsonOutputParser
from langchain.output_parsers import OutputFixingParser
from langchain_core.exceptions import OutputParserException
from prompt.prompt_library import PROMPT_REGISTRY  # type: ignore

log = CustomLogger().get_logger(__name__)


class DocumentAnalyzer:
    """
    Analyzes documents using a pre-trained model.
    Automatically logs all actions and supports session-based organization.
    """

    def __init__(self):
        try:
            self.loader = ModelLoader()
            self.llm = self.loader.load_llm()

            # Prepare parsers
            self.parser = JsonOutputParser(pydantic_object=Metadata)
            self.fixing_parser = OutputFixingParser.from_llm(parser=self.parser, llm=self.llm)

            self.prompt = PROMPT_REGISTRY["document_analysis"]

            log.info("DocumentAnalyzer initialized successfully")

        except Exception as e:
            log.error(f"Error initializing DocumentAnalyzer: {e}")
            raise DocumentPortalException("Error in DocumentAnalyzer initialization", sys)

    def _extract_json_object(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from an LLM response that may contain markdown/code/text.
        """
        if not text or not isinstance(text, str):
            raise ValueError("Empty or invalid LLM output (expected a non-empty string).")

        # Remove fenced code block markers if present
        cleaned = re.sub(r"```[a-zA-Z]*\n?", "", text).replace("```", "").strip()

        # Find first JSON object in response
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise ValueError(f"No JSON object found in output. Preview:\n{cleaned[:500]}")

        return json.loads(match.group(0).strip())

    def _repair_to_json_only(self, document_text: str) -> Dict[str, Any]:
        """
        Fallback: Ask the LLM to output ONLY valid JSON, then parse safely.
        """
        repair_prompt = (
            "Return ONLY valid JSON. No markdown. No code. No explanation.\n\n"
            f"{self.parser.get_format_instructions()}\n\n"
            "Document:\n"
            f"{document_text}"
        )

        raw = self.llm.invoke(repair_prompt)
        raw_text = getattr(raw, "content", raw)
        if not isinstance(raw_text, str):
            raw_text = str(raw_text)

        return self._extract_json_object(raw_text)

    def analyze_document(self, document_text: str) -> dict:
        """
        Analyze a document's text and extract structured metadata & summary.
        """
        try:
            chain = self.prompt | self.llm | self.fixing_parser

            log.info("Meta-data analysis chain initialized")

            response = chain.invoke({
                "format_instructions": self.parser.get_format_instructions(),
                "document_text": document_text
            })

            # Your existing behavior: log keys (but avoid crashing if not dict)
            if isinstance(response, dict):
                log.info("Metadata extraction successful", keys=list(response.keys()))
                return response

            # If response isn't a dict, attempt to parse it anyway
            parsed = self._extract_json_object(str(response))
            log.info("Metadata extraction successful (parsed from non-dict)", keys=list(parsed.keys()))
            return parsed

        except OutputParserException as e:
            # This is the "Invalid json output" path
            log.error("Invalid JSON output from model; trying repair fallback", error=str(e))
            try:
                repaired = self._repair_to_json_only(document_text)
                log.info("Metadata extraction successful after repair", keys=list(repaired.keys()))
                return repaired
            except Exception as repair_err:
                log.error("Repair fallback failed", error=str(repair_err))
                raise DocumentPortalException("Metadata extraction failed after repair", sys)

        except Exception as e:
            log.error("Metadata analysis failed", error=str(e))
            raise DocumentPortalException("Metadata extraction failed", sys)