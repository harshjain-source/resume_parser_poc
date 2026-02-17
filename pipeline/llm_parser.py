import os
import json
import time
import threading
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from config.settings import settings
from dotenv import load_dotenv
from schemas.resume_schema import ContactInfo, Education, WorkExperience, Certification, Project, SkillCategory
from pipeline.chunk_manager import ChunkManager
from config.logger_config import get_logger

# Dynamic Imports for Multi-Provider support
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

try:
    from langchain_ollama import ChatOllama
except ImportError:
    ChatOllama = None

try:
    from sarvam import SarvamChat
except ImportError:
    SarvamChat = None

load_dotenv()

class LLMParser:
    """
    Stage 7: LLM Parsing.
    Uses LLM to convert semantic buckets into structured JSON using Pydantic schemas.
    Supports Mega-Sections via ChunkManager.
    """
    
    # Map semantic buckets to Pydantic models for strict extraction
    SCHEMA_MAP: Dict[str, Type[BaseModel]] = {
        "PERSONAL_INFO": ContactInfo,
        "EDUCATION": Education,
        "EXPERIENCE": WorkExperience,
        "LEGAL_CERTIFICATION": Certification,
        "PROJECTS": Project,
        "SKILLS": SkillCategory
    }

    def __init__(self, provider: str = "Google", model_name: str = "gemini-2.5-flash-lite"):
        self.provider = provider
        self.model_name = model_name
        self.chunk_manager = ChunkManager(max_tokens=2000) # Reduced for safety
        self.logger = get_logger("LLMParser")
        self.logger.info(f"LLMParser initialized with provider: {provider}, model: {model_name}")
        self.llm = self._initialize_llm(provider, model_name)

    def _initialize_llm(self, provider: str, model_name: str):
        """Initializes the LLM based on the provider and model name."""
        if provider == "Google":
            if not ChatGoogleGenerativeAI:
                raise ImportError("Please install langchain-google-genai")
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0, 
                google_api_key=settings.GOOGLE_API_KEY
            )
        elif provider == "OpenAI":
            if not ChatOpenAI:
                raise ImportError("Please install langchain-openai")
            return ChatOpenAI(
                model=model_name,
                temperature=0,
                api_key=settings.OPENAI_API_KEY
            )
        elif provider == "Anthropic":
            if not ChatAnthropic:
                raise ImportError("Please install langchain-anthropic")
            return ChatAnthropic(
                model=model_name,
                temperature=0,
                api_key=settings.ANTHROPIC_API_KEY
            )
        elif provider == "Sarvam":
            if not SarvamChat:
                raise ImportError("Sarvam integration not found. Run: pip install langchain-sarvam-integration")
            return SarvamChat(
                model=model_name,
                api_key=settings.SARVAM_API_KEY
            )
        elif provider == "Ollama (Local)":
            if not ChatOllama:
                raise ImportError("Please install langchain-ollama")
            return ChatOllama(
                model=model_name,
                temperature=0
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def parse_chunk(self, bucket_name: str, content: str, metadata: Dict[str, Any], progress_callback=None):
        """Standardized entry point for parsing any piece of resume text."""
        # 1. Rules & Parser
        parser, instruction_note = self._setup_parser(bucket_name)

        # 2. Part & Continuation Context
        part_info, is_cont = self._prepare_context(metadata)

        # 3. Prompt Builder
        prompt = self._create_prompt_template(bucket_name, parser)
        
        # 4. Execution Gear
        return self._execute_llm_task(prompt, parser, bucket_name, content, metadata, part_info, instruction_note, is_cont)

    def _setup_parser(self, bucket_name: str):
        """Configures the JSON parser and extraction instructions based on the section type."""
        schema = self.SCHEMA_MAP.get(bucket_name)
        if schema:
            parser = JsonOutputParser(pydantic_object=schema)
            is_list = bucket_name in ["EDUCATION", "EXPERIENCE", "LEGAL_CERTIFICATION", "PROJECTS", "SKILLS"]
            instruction_note = "Return a LIST of JSON objects." if is_list else "Return a single JSON object."
        else:
            parser = JsonOutputParser()
            instruction_note = "Return structured JSON."
        return parser, instruction_note

    def _prepare_context(self, metadata: Dict[str, Any]):
        """Formats sticky context for chunked processing (Part X of Y, Continuation notes)."""
        part_num = metadata.get("part", 1)
        total_parts = metadata.get("total_parts", 1)
        
        part_info = f"(Part {part_num} of {total_parts})" if total_parts > 1 else ""
        
        is_cont = (
            "This is a continuation of a large section. Extract ONLY NEW entries found in THIS text. "
            "DO NOT repeat previous entries."
        ) if metadata.get("is_continuation") else "This is a new section start."
        
        return part_info, is_cont

    def _create_prompt_template(self, bucket_name, parser):
        """Constructs the prompt template for a specific bucket."""
        return PromptTemplate(
            template="You are a professional Resume Data Extractor.\n"
                     "Your Goal: Convert the following text into a structured JSON array of {bucket_name} objects.\n"
                     "Adhere strictly to the provided schema.\n\n"
                     "Context:\n"
                     "- Candidate: {candidate_name}\n"
                     "- Section: {bucket_name} {part_info}\n"
                     "- Continuation Note: {is_continuation_msg}\n\n"
                     "Rules:\n"
                     "1. Extract ONLY information present in the text below.\n"
                     "2. DO NOT hallucinate. Do not repeat entries from previous parts.\n"
                     "3. {instruction_note}\n"
                     "4. {format_instructions}\n"
                     "5. Be concise. Do not add conversational filler.\n\n"
                     "Text to Parse:\n{text}\n\n"
                     "JSON Output:",
            input_variables=["bucket_name", "text", "candidate_name", "part_info", "instruction_note", "is_continuation_msg"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )

    def _execute_llm_task(self, prompt, parser, bucket_name, content, metadata, part_info, instruction_note, is_cont):
        """Internal worker to execute the LLM chain and parse usage/data."""
        chain = prompt | self.llm
        try:
            raw_response = chain.invoke({
                "bucket_name": bucket_name,
                "text": content,
                "candidate_name": metadata.get("candidate_name", "Unknown"),
                "part_info": part_info,
                "instruction_note": instruction_note,
                "is_continuation_msg": is_cont
            })
            
            # Extract Token Usage
            tokens = self._extract_token_usage(raw_response)

            # Parse JSON
            parsed_data = parser.invoke(raw_response)
            self.logger.debug(f"Successfully parsed chunk {part_info}. Tokens used: {tokens}")
            return parsed_data, tokens
            
        except Exception as e:
            self.logger.error(f"⚠️ Chunk Error ({bucket_name} {part_info}): {e}", exc_info=True)
            return ([] if bucket_name in ["EDUCATION", "EXPERIENCE"] else {}), {"input": 0, "output": 0, "total": 0}

    def _extract_token_usage(self, response: Any) -> Dict[str, int]:
        """Deeply extracts token usage from various LLM provider response formats."""
        usage = getattr(response, 'usage_metadata', {})
        
        # 1. Try Standard LangChain Keys
        input_t = usage.get("input_tokens") or usage.get("prompt_tokens", 0)
        output_t = usage.get("output_tokens") or usage.get("candidates_tokens") or usage.get("completion_tokens", 0)
        total_t = usage.get("total_tokens", 0)
        
        # 2. Try Provider-Specific Fallbacks (Google/OpenAI/Sarvam)
        if total_t == 0:
            resp_meta = getattr(response, 'response_metadata', {})
            # Google GenAI specific
            if 'usage' in resp_meta:
                u = resp_meta['usage']
                input_t = u.get('prompt_token_count', input_t)
                output_t = u.get('candidates_token_count', output_t)
                total_t = u.get('total_token_count', total_t)
            # Generic token_usage dict
            elif 'token_usage' in resp_meta:
                u = resp_meta['token_usage']
                input_t = u.get('prompt_tokens', input_t)
                output_t = u.get('completion_tokens', output_t)
                total_t = u.get('total_tokens', total_t)

        # Final total calculation if still zero but parts exist
        if total_t == 0 and (input_t > 0 or output_t > 0):
            total_t = input_t + output_t

        return {
            "input": input_t,
            "output": output_t,
            "total": total_t
        }

    def _identify_candidate(self, buckets: Dict[str, str], final_data: Dict[str, Any], usage_lock: threading.Lock, progress_callback=None) -> str:
        """Initial step to identify candidate name and process personal info."""
        personal_text = buckets.get("PERSONAL_INFO", "")
        candidate_name = "Unknown"
        if personal_text:
            if progress_callback: progress_callback("🏷️ Identifying Candidate...")
            temp_res, tokens = self.parse_chunk("PERSONAL_INFO", personal_text, {"part": 1, "total_parts": 1, "candidate_name": "Unknown"})
            candidate_name = temp_res.get("full_name") or temp_res.get("name") or "Unknown"
            final_data["sections"]["PERSONAL_INFO"] = temp_res
            with usage_lock:
                for k in tokens: final_data["token_usage"][k] += tokens[k]
        return candidate_name

    def _process_all_sections_parallel(self, buckets: Dict[str, str], candidate_name: str, final_data: Dict[str, Any], usage_lock: threading.Lock, progress_callback=None) -> Dict[str, List]:
        """Orchestrates parallel extraction of all buckets and chunks."""
        all_tasks = []
        for bucket_name, content in buckets.items():
            if bucket_name == "PERSONAL_INFO" or not content.strip():
                continue
            
            chunks = self.chunk_manager.prepare_chunks(content, bucket_name, candidate_name)
            for chunk_data in chunks:
                all_tasks.append((bucket_name, chunk_data))

        def process_chunk_task(task):
            b_name, c_data = task
            part = c_data['metadata']['part']
            total = c_data['metadata']['total_parts']
            if progress_callback: progress_callback(f"⚡ Processing {b_name} (Chunk {part}/{total})...")
            res, tokens = self.parse_chunk(b_name, c_data['content'], c_data['metadata'], progress_callback)
            return (b_name, part, res, tokens)

        bucket_results = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(process_chunk_task, t) for t in all_tasks]
            for future in as_completed(futures):
                try:
                    b_name, part_num, res, tokens = future.result()
                    if b_name not in bucket_results:
                        bucket_results[b_name] = []
                    bucket_results[b_name].append((part_num, res))
                    with usage_lock:
                        for k in tokens: final_data["token_usage"][k] += tokens[k]
                except Exception as e:
                    self.logger.error(f"Worker Error: {e}", exc_info=True)
        return bucket_results

    def run(self, resume_id: str, progress_callback=None):
        """Processes all semantic blocks using Smart Chunking and Merging."""
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
            "sections": {},
            "token_usage": {"input": 0, "output": 0, "total": 0}
        }

        usage_lock = threading.Lock()

        # 1. Identify Candidate Name First (Sticky Identity)
        candidate_name = self._identify_candidate(buckets, final_data, usage_lock, progress_callback)

        # 2. Parallel Processing for other buckets
        bucket_results = self._process_all_sections_parallel(buckets, candidate_name, final_data, usage_lock, progress_callback)

        # 3. Merge Results Sequentially (preserving part order)
        final_data["sections"] = self._merge_chunk_results(bucket_results)
        
        # Log final token usage to console
        usage = final_data["token_usage"]
        print(f"📊 Total Token Usage: Input={usage['input']}, Output={usage['output']}, Total={usage['total']}")
        if progress_callback:
            progress_callback(f"📊 Token Usage: In={usage['input']} | Out={usage['output']} | Total={usage['total']}")

        # 4. Post-Processing Highlights (Total Exp, Education Tier)
        final_data["metadata"] = self._perform_post_processing(final_data["sections"])

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=4, ensure_ascii=False)
            
        return output_file

    def _get_education_tier(self, edu_list: list) -> str:
        """Determines the highest education tier from a list of education entries."""
        tiers = {
            "phd": 5, "doctorate": 5,
            "master": 4, "mtech": 4, "mba": 4, "m.sc": 4, "ma": 4, "ms": 4,
            "bachelor": 3, "btech": 3, "be": 3, "b.sc": 3, "ba": 3, "bs": 3,
            "diploma": 2,
            "high school": 1, "secondary": 1
        }
        
        highest_val = 0
        highest_label = "Not Specified"
        
        for edu in edu_list:
            degree = str(edu.get("degree", "")).lower()
            for label, val in tiers.items():
                if label in degree:
                    if val > highest_val:
                        highest_val = val
                        highest_label = degree.title()
                    break
        
        return highest_label

    def _calculate_total_experience(self, exp_list: list) -> float:
        """Calculates total unique years of experience using Python logic."""
        import datetime
        import re

        def parse_date(date_str):
            if not date_str:
                return None
            date_str = date_str.lower().strip()
            if "present" in date_str or "now" in date_str:
                return datetime.date.today()
            
            # Extract year (4 digits)
            year_match = re.search(r"20\d{2}|19\d{2}", date_str)
            if not year_match:
                return None
            year = int(year_match.group())
            
            # Extract month (name or digit)
            month = 1
            months_map = {
                "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
            }
            for m_name, m_val in months_map.items():
                if m_name in date_str:
                    month = m_val
                    break
            
            return datetime.date(year, month, 1)

        unique_months = set()
        for exp in exp_list:
            dates = exp.get("dates", {})
            if not dates: continue
            
            start = parse_date(dates.get("start"))
            end = parse_date(dates.get("end"))
            
            if start and end:
                curr = start
                # Loop through every month between start and end and add to set
                while curr <= end:
                    unique_months.add((curr.year, curr.month))
                    # Move to next month
                    if curr.month == 12:
                        curr = datetime.date(curr.year + 1, 1, 1)
                    else:
                        curr = datetime.date(curr.year, curr.month + 1, 1)

        return round(len(unique_months) / 12.0, 1) if unique_months else 0.0

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
