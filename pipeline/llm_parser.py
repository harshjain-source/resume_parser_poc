import os
import json
from typing import Dict, Any, Type
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from config.settings import settings
from dotenv import load_dotenv
from schemas.resume_schema import ContactInfo, Education, WorkExperience, Certification

load_dotenv()

class LLMParser:
    """
    Stage 7: LLM Parsing.
    Uses LLM to convert semantic buckets into structured JSON using Pydantic schemas.
    """
    
    # Map semantic buckets to Pydantic models for strict extraction
    SCHEMA_MAP: Dict[str, Type[BaseModel]] = {
        "PERSONAL_INFO": ContactInfo,
        "EDUCATION": Education, # The parser will handle list vs single object instructions
        "EXPERIENCE": WorkExperience,
        "LEGAL_CERTIFICATION": Certification
    }

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment.")
            
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            temperature=0, 
            google_api_key=self.api_key
        )

    def parse_bucket(self, bucket_name: str, text: str):
        """Converts a raw text bucket into structured JSON using schema enforcement."""
        
        # Check if we have a specific schema for this bucket
        schema = self.SCHEMA_MAP.get(bucket_name)
        
        if schema:
            # For lists like Education/Experience, we want the LLM to return a List of the schema
            parser = JsonOutputParser(pydantic_object=schema)
            instruction_note = "Return a JSON object matching the provided schema."
            if bucket_name in ["EDUCATION", "EXPERIENCE", "LEGAL_CERTIFICATION"]:
                instruction_note = "Return a LIST of JSON objects, where each object matches the provided schema."
        else:
            parser = JsonOutputParser()
            instruction_note = "Return a highly structured JSON object."

        prompt = PromptTemplate(
            template="You are a professional Resume Data Extractor.\n"
                     "Your goal is to extract ALL information from the {bucket_name} section.\n"
                     "CONTEXT: {instruction_note}\n\n"
                     "RULES:\n"
                     "1. Do not lose any details (dates, roles, project costs, etc.).\n"
                     "2. If values are unknown, use null.\n"
                     "3. {format_instructions}\n\n"
                     "TEXT TO PARSE:\n{text}\n",
            input_variables=["bucket_name", "text", "instruction_note"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        chain = prompt | self.llm | parser
        try:
            response = chain.invoke({
                "bucket_name": bucket_name, 
                "text": text,
                "instruction_note": instruction_note
            })
            return response
        except Exception as e:
            print(f"⚠️ Failed to parse {bucket_name}: {e}")
            return {"error": str(e), "raw_text": text[:500]}

    def run(self, resume_id: str):
        """Processes all semantic blocks for a given resume_id."""
        base_path = os.path.join(settings.RESUME_DIR, resume_id)
        input_file = os.path.join(base_path, "semantic_blocks.json")
        output_file = os.path.join(base_path, "final_resume.json")

        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Missing input artifact: {input_file}")

        with open(input_file, "r", encoding="utf-8") as f:
            buckets = json.load(f)

        final_data = {
            "resume_id": resume_id,
            "extracted_at": settings.get_timestamp(),
            "sections": {}
        }
        
        for bucket_name, content in buckets.items():
            if not content.strip() or len(content) < 10: 
                continue
            
            print(f"✨ Synthesizing: {bucket_name}...")
            res = self.parse_bucket(bucket_name, content)
            final_data["sections"][bucket_name] = res

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=4, ensure_ascii=False)
            
        return output_file

if __name__ == "__main__":
    # Runnable test debug
    TEST_UUID = "test_extraction_debug"
    print(f"🔬 Testing LLMParser for: {TEST_UUID}...")
    try:
        parser = LLMParser()
        path = parser.run(TEST_UUID)
        print(f"✅ Extracted! File: {path}")
    except Exception as e:
        print(f"❌ Parser failed: {e}")
