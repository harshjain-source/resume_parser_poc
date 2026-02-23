import os
import json
from typing import Dict, Any, Type
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
import httpx
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from config.settings import settings
from dotenv import load_dotenv
# from schemas.resume_schema import ContactInfo, Education, WorkExperience, Certification

load_dotenv()

class LLMParser:
    """
    Stage 7: LLM Parsing.
    Converts semantic blocks into high-accuracy JSON using One-Shot templates.
    """
    
    # Master Template (High-Fidelity Enterprise Schema)
    MASTER_TEMPLATES = {
        "DOCUMENT_METADATA": {
            "source_file_name": None,
            "extraction_timestamp": None,
            "total_pages": None,
            "note": "NO PROJECTS SHOULD BE EXTRACTED HERE"
        },
        "PERSONAL_INFORMATION": {
            "name": None,
            "date_of_birth": None,
            "nationality": None,
            "contact_details": {
                "primary_mobile": None,
                "alternate_mobile": None,
                "landline": None,
                "email": None
            },
            "identity_details": {
                "pan_number": None,
                "aadhar_number": None,
                "passport_number": None
            },
            "addresses": {
                "current_address": None,
                "permanent_address": None
            },
            "professional_registration_details": {
                "registration_number": None,
                "registration_date": None,
                "registration_validity": None,
                "verification_status": None,
                "verification_remarks": None,
                "raw_registration_text": None
            }
        },
        "proposed_assignment_details": {
            "proposed_position": None,
            "firm_name": None,
            "profession": None,
            "years_with_firm": None,
            "proposed_project_title": None,
            "proposed_project_location": None,
            "raw_assignment_text": None
        },
        "EDUCATION": [
            {
                "degree_title": None,
                "education_level": None,
                "specialization": None,
                "institution_name": None,
                "university_name": None,
                "enrollment_number": None,
                "roll_number": None,
                "gpa_or_percentage": None,
                "passing_year": None,
                "start_year": None,
                "education_notes": None,
                "raw_text_block": None
            }
        ],
        "PROFESSIONAL_EXPERIENCE": [
            {
                "company_name": None,
                "company_location": None,
                "employment_start_date": None,
                "employment_end_date": None,
                "designation": None,
                "employment_type": None,
                "mode_of_execution": None,
                "employment_notes": None,
                "projects": [
                    {
                        "project_name": None,
                        "project_location": None,
                        "client_name": None,
                        "project_type": None,
                        "project_category": None,
                        "project_cost": {"value": None, "currency": None, "unit": None},
                        "funding_type": None,
                        "project_duration": {"start_date": None, "end_date": None, "duration_text": None},
                        "role_in_project": None,
                        "scope_of_work": None,
                        "road_numbers": {
                             "nh": None,
                             "sh": None,
                             "mdr": None,
                             "odr": None
                        },
                        "detailed_description": None,
                        "highway_details": {
                            "lane_entries": [
                                {"lane_type": None, "length_km": None, "surface_type": None, "terrain_type": None},
                                {"lane_type": None, "length_km": None, "surface_type": None, "terrain_type": None},
                                {"lane_type": None, "length_km": None, "surface_type": None, "terrain_type": None}
                            ],
                            "arbitration_details": None, 
                            "financial_closure": None,
                            "eia_infrastructure": None,
                            "raw_highway_text": None
                        },
                        "bridge_details": {
                            "bridge_entries": [
                                {"bridge_type": None, "longest_span_m": None, "total_length_m": None, "foundation_type": None, "cost": None, "technology": None}
                            ],
                            "bridge_length_ranges": {
                                "6m_60m": None,
                                "60m_200m": None,
                                "200m_500m": None,
                                "500m_1000m": None,
                                "greater_than_1000m": None
                            },     
                            "max_individual_span": None,
                            "total_bridge_length": None,
                            "No. Of Major Bridges with Pile/Well foundation": None,
                            "No. Of Bridges where Rehabilitation and repair work was done": None,
                            "raw_bridge_section_text": None
                        },
                        "tunnel_details": {
                            "tunnel_entries": [{"length_m": None, "type": None, "tube_type": None, "cost": None, "technology_used": None, "geology_type": None}],
                            "tunnel_length_ranges": {
                                "upto_200m": None,
                                "200m_500m": None,
                                "500m_1000m": None,
                                "greater_than_1000m": None
                            },
                            "total_length": None,
                            "maximum_individual_length": None,
                            "evaluation_details": {"slope_stability": None, "hydrological_studies": None, "software_used": None},
                            "raw_tunnel_section_text": None
                        },
                        "other_project_attributes": [], 
                        "raw_project_text": None
                    }
                ]
            }
        ],
        "LEGAL_DECLARATIONS": {
            "candidate_declaration": None,
            "firm_declaration": None,
            "signature_date": None,
            "other_legal_text": None
        },
        "ADDITIONAL_INFORMATION": {
            "professional_memberships": [],
            "certifications": [],
            "software_skills": [],
            "technical_skills": [],
            "languages_known": [],
            "other_sections": []
        },
        "RAW_UNMAPPED_TEXT": []
    }


    class SarvamClient:
        """Manual implementation for Sarvam AI as it's not natively supported in LangChain."""
        def __init__(self, api_key: str, model: str):
            self.api_key = api_key
            self.model = model
            self.base_url = f"{settings.SARVAM_BASE_URL}/v1/chat/completions"

        def invoke(self, prompt: str) -> AIMessage:
            headers = {
                "api-subscription-key": self.api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0
            }
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(self.base_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                content = data["choices"][0]["message"]["content"]
                # Mimic LangChain response metadata for token tracking
                usage = data.get("usage", {})
                response_metadata = {
                    "usage_metadata": {
                        "prompt_token_count": usage.get("prompt_tokens", 0),
                        "candidates_token_count": usage.get("completion_tokens", 0),
                        "total_token_count": usage.get("total_tokens", 0)
                    }
                }
                return AIMessage(content=content, response_metadata=response_metadata)

    def __init__(self, provider: str = None, model: str = None):
        self.provider = provider or settings.DEFAULT_PROVIDER
        
        if self.provider == "google":
            self.api_key = os.getenv("GOOGLE_API_KEY")
            if not self.api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment.")
            self.llm = ChatGoogleGenerativeAI(
                model=model or settings.GEMINI_MODEL,
                temperature=0, 
                google_api_key=self.api_key
            )
        elif self.provider == "groq":
            self.api_key = os.getenv("GROQ_API_KEY")
            if not self.api_key:
                raise ValueError("GROQ_API_KEY not found in environment.")
            self.llm = ChatGroq(
                model=model or settings.GROQ_MODEL,
                temperature=0,
                groq_api_key=self.api_key
            )
        elif self.provider == "sarvam":
            self.api_key = os.getenv("SARVAM_API_KEY")
            if not self.api_key:
                raise ValueError("SARVAM_API_KEY not found in environment.")
            self.llm = self.SarvamClient(
                api_key=self.api_key,
                model=model or settings.SARVAM_MODEL
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    # def parse_bucket(self, bucket_name: str, text: str):
    #     """Converts raw text into JSON using a one-shot format template with zero-deletion rules."""
        
        # # Check if we have a specific schema for this bucket
        # schema = self.SCHEMA_MAP.get(bucket_name)
        
        # if schema:
        #     # For lists like Education/Experience, we want the LLM to return a List of the schema
        #     # parser = JsonOutputParser(pydantic_object=schema)
        #     parser = JsonOutputParser()
        #     instruction_note = "Return a JSON object matching the provided schema."
        #     if bucket_name in ["EDUCATION", "EXPERIENCE", "LEGAL_CERTIFICATION"]:
        #         instruction_note = "Return a LIST of JSON objects, where each object matches the provided schema."
        # else:

        #   # 1. Select the relevant portion of the master template
        # example_format = self.MASTER_TEMPLATES.get(bucket_name, {"Note": "Extract all data from the text into valid JSON."})
        
        # # 2. Use a generic Parser (No strict schema filtering)
        # parser = JsonOutputParser()
        # instruction_note = "Return a highly structured JSON object."

    def parse_bucket(self, bucket_name: str, text: str):
        """Converts raw text into JSON using a one-shot format template and captures tokens."""
        example_format = self.MASTER_TEMPLATES.get(bucket_name, {"Note": "Extract all data from the text into valid JSON."})
        parser = JsonOutputParser()

        prompt = PromptTemplate(
            template="""You are a deterministic resume extraction engine.

Your task is to convert the PAGE TEXT into structured JSON strictly following the provided JSON STRUCTURE.

STRICT RULES (CRITICAL):

1. DO NOT extract projects into DOCUMENT_METADATA.
   - All projects must reside ONLY inside PROFESSIONAL_EXPERIENCE -> projects list.
   - DOCUMENT_METADATA is for file-level info ONLY.

2. TABLE EXTRACTION (GRID MAPPING):
   - For Lane Details: Every row in a lane table MUST be a separate dictionary in the `lane_entries` list.
     - e.g., Row 1 (2 Lane) -> Dict 1, Row 2 (4 Lane) -> Dict 2. 
     - Do NOT combine them into one string.
   - For Bridge Details: Every row in a bridge table MUST be a separate dictionary in the `bridge_entries` list.
     - One Dict per bridge. Do NOT combine bridges.
   - For Education: Every qualification is a separate dictionary in the list.

3. ROAD & PROJECT METADATA:
   - Always extract "National Highway No." and "State Highway No." into the `road_numbers` dictionary.
   - Do NOT ignore these values.

4. PROJECT IDENTITY:
   - Projects are unique. Do NOT merge 2 different projects even if they are under the same company.
   - Data belonging to "Project A" must NOT be merged into "Project B" object.

5. ATTACHMENT RULE:
   - Attach tables (Lanes, Bridges, Tunnels) ONLY to the project immediately preceding the table in the PAGE TEXT.
   - Do NOT copy metrics across projects.

6. NO ANALYTICS:
   - Do NOT analyze or infer terrain, lane types, totals, or ranges.
   - Extract exactly what is written. If it says "2 Lane", map it to "2 Lane".

7. VALUES:
   - If a value is missing, use null. NEVER guess or invent data.
   - Leave `raw_highway_text` and `raw_bridge_section_text` for the complete unformatted text of those sections.

8. OUTPUT:
   - Strictly valid JSON only. No explanations. No markdown.

JSON STRUCTURE:
{json_example}

PAGE TEXT:
{text}""",
            input_variables=["text", "json_example"],
        )
        
        # Format the prompt
        formatted_prompt = prompt.format(text=text, json_example=json.dumps(example_format, indent=4))
        
        try:
            # We use invoke directly on the model to get response_metadata
            msg = self.llm.invoke(formatted_prompt)
            
            # Extract Tokens using utility
            from utils.resume_utils import extract_tokens_from_response
            tokens = extract_tokens_from_response(msg)
            
            # Parse the text content into JSON
            response = parser.parse(msg.content)
            return response, tokens
        except Exception as e:
            return {"error": str(e), "raw_text": text[:500]}, {"input": 0, "output": 0}

    def run(self, resume_id: str):
        # 1. Immediate Configuration Check
        if not self.api_key:
            raise ConnectionError("LLM Parser Error: No Google API Key found. Call canceled.")
        
        if not self.llm:
            raise NameError("LLM Parser Error: LLM Client failed to initialize.")

        base_path = os.path.join(settings.RESUME_DIR, resume_id)
        input_file = os.path.join(base_path, "semantic_blocks.json")
        output_file = os.path.join(base_path, "final_resume.json")
    
        # 2. Input File Check
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"LLM Parser Error: Input missing at {input_file}")

        # 3. Output Path Check (Check if we can write the final file)
        try:
            with open(output_file, "a"): pass # "Touching" the file to check write access
        except Exception:
            raise PermissionError(f"LLM Parser Error: System cannot write to {base_path}. Check permissions.")

        # --- IF WE REACH HERE, IT IS SAFE TO SPEND MONEY/REQUESTS ---
        with open(input_file, "r", encoding="utf-8") as f:
            buckets = json.load(f)

        final_data = {
            "resume_id": resume_id,
            "extracted_at": settings.get_timestamp(),
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            "sections": {}
        }
        
        for bucket_name, content in buckets.items():
            if not content.strip() or len(content) < 10: 
                continue
            
            print(f"✨ Synthesizing: {bucket_name}...")
            res, tokens = self.parse_bucket(bucket_name, content)
            
            # Aggregate Tokens
            final_data["usage"]["input_tokens"] += tokens["input"]
            final_data["usage"]["output_tokens"] += tokens["output"]
            final_data["usage"]["total_tokens"] += (tokens["input"] + tokens["output"])
            
            final_data["sections"][bucket_name] = res

        # Console Verification
        usage = final_data["usage"]
        print(f"📊 Aggregated Token Usage -> Input: {usage['input_tokens']}, Output: {usage['output_tokens']}, Total: {usage['total_tokens']}")

        # Post-Processing: Calculate Total Experience
        from utils.resume_utils import calculate_total_experience
        # Look for the new key first, then fallback to others
        proc_list = final_data["sections"].get("PROFESSIONAL_EXPERIENCE", [])
        if not proc_list:
            exp_data = final_data["sections"].get("EXPERIENCE", {})
            if isinstance(exp_data, dict) and "employments" in exp_data:
                proc_list = exp_data["employments"]
            else:
                proc_list = exp_data if isinstance(exp_data, list) else [exp_data]
        
        final_data["computed"] = {
            "total_experience_years": calculate_total_experience(proc_list)
        }

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
