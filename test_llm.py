import fitz
import os
import re
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, JsonOutputParser
from dotenv import load_dotenv

load_dotenv()

API_KEY = "AIzaSyDwX4nZOlkjWYO-YeKzwXssDhrZQeE0AVw"

model_name = "gemini-2.5-flash-lite"

# ==========================================
# FINAL STAGE: DYNAMIC DATA SCHEMAS
# ==========================================

class FlexibleExtraction(BaseModel):
    """A container for any structured data extracted by the LLM."""
    data: Any = Field(description="The structured JSON representation of the extracted section")

class FinalResumeSchema(BaseModel):
    """The master container for the entire resume."""
    sections: Dict[str, Any] = Field(default_factory=dict)

# ==========================================
# STEP 4: LLM PARSER (THE "EXTRACTOR")
# ==========================================
class LLMParser:
    """Uses LLM to convert semantic buckets into structured JSON."""
    
    def __init__(self):
        # We define a smart prompt that handles the engineering complexity
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0, google_api_key=API_KEY)

    def parse_bucket(self, bucket_name: str, text: str):
        # We use JsonOutputParser to allow the LLM to define the structure
        parser = JsonOutputParser()
        
        prompt = PromptTemplate(
            template="You are a professional Resume Data Extractor.\n"
                     "Your goal is to extract ALL information from the {bucket_name} text into a highly structured JSON format.\n"
                     "1. Do not lose any details (dates, numbers, descriptions, labels).\n"
                     "2. Use descriptive and consistent keys.\n"
                     "3. If there are multiple items (like jobs, projects, or degrees), structure them as a JSON list of objects.\n"
                     "4. If a field has many sub-details, create a nested object.\n\n"
                     "{format_instructions}\n"
                     "TEXT:\n{text}\n",
            input_variables=["bucket_name", "text"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        chain = prompt | self.llm | parser
        try:
            # Note: get_openai_callback only works for OpenAI. 
            # For Gemini, we extract usage from the response metadata.
            response = (prompt | self.llm).invoke({"bucket_name": bucket_name, "text": text})
            
            # Extract token usage if available (standard in newer LangChain versions)
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(response, 'usage_metadata'):
                prompt_tokens = response.usage_metadata.get('input_tokens', 0)
                completion_tokens = response.usage_metadata.get('output_tokens', 0)
            
            # Now parse the output text
            result = parser.parse(response.content)
            
            print(f"   📊 [{bucket_name}] Tokens: {prompt_tokens} (in) | {completion_tokens} (out)")
            
            # Return a tuple that looks like the previous one to avoid breaking the logic
            class DummyCB:
                def __init__(self, p, c):
                    self.prompt_tokens = p
                    self.completion_tokens = c
            
            return result, DummyCB(prompt_tokens, completion_tokens)
        except Exception as e:
            print(f"⚠️ Failed to parse {bucket_name}: {e}")
            return None, None

# ==========================================
# UPDATED PIPELINE
# ==========================================

# (Keeping Step 1, 2, 3 as they are for brevity but they are called in main)
# ... [PDFToMarkdown, TextCleaner, SectionSegmenter remain same as before] ...

if __name__ == "__main__":
    print("--- 🧠 LLM Parsing Strategy (Final Step) ---")
    STORAGE_BASE = "processed_resumes"
    
    # 1. Detect most recent folder
    if os.path.exists(STORAGE_BASE):
        folders = [f for f in os.listdir(STORAGE_BASE) if os.path.isdir(os.path.join(STORAGE_BASE, f))]
        if not folders:
            print("❌ No processed resumes found in 'processed_resumes/'. Run test.py first.")
            exit()
        
        # Sort by modification time to get latest
        latest_folder = max(folders, key=lambda f: os.path.getmtime(os.path.join(STORAGE_BASE, f)))
        output_dir = os.path.join(STORAGE_BASE, latest_folder)
        input_file = os.path.join(output_dir, "semantic_blocks.json")
        
        print(f"📂 Processing folder: {latest_folder}")

        if os.path.exists(input_file):
            with open(input_file, "r", encoding="utf-8") as f:
                buckets = json.load(f)
            
            parser = LLMParser()
            final_data = {"sections": {}}
            total_in = 0
            total_out = 0

            for bucket_name, content in buckets.items():
                if not content.strip(): continue
                print(f"✨ Synthesizing: {bucket_name}...")
                res, cb = parser.parse_bucket(bucket_name, content)
                
                if res:
                    final_data["sections"][bucket_name] = res
                    total_in += cb.prompt_tokens
                    total_out += cb.completion_tokens

            # -- D. Final Summary --
            print(f"\n✅ Extraction Complete!")
            print(f"📈 TOTAL TOKEN SPEND: {total_in} (Input) + {total_out} (Output) = {total_in + total_out}")

            output_file = os.path.join(output_dir, "final_resume.json")
            with open(output_file, "w", encoding="utf-8") as f:
               json.dump(final_data, f, indent=4)
            print(f"💾 Saved final JSON to: {output_file}")
        else:
            print(f"❌ '{input_file}' not found in the latest folder.")
    else:
        print("❌ 'processed_resumes/' base directory not found.")
