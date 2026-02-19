from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr
from enum import Enum

# --- Enums for Standardization ---

class ExperienceType(str, Enum):
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    INTERNSHIP = "Internship"
    FREELANCE = "Freelance"

# --- Reusable Components ---

class DateRange(BaseModel):
    """Flexible date range that handles various formats"""
    start: Optional[str] = Field(None, description="Start date (any format: YYYY, MM/YYYY, DD/MM/YYYY)")
    end: Optional[str] = Field(None, description="End date or 'Present'")
    duration: Optional[str] = Field(None, description="Calculated duration (e.g., '2 years 3 months')")

class ContactInfo(BaseModel):
    """Universal contact information"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = Field(None, description="City, State, Country")
    
    # Social/Professional Links
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    website: Optional[str] = None
    other_links: Dict[str, str] = Field(default_factory=dict, description="Any other links")

# --- Work Experience (Universal) ---

class WorkExperience(BaseModel):
    """
    Universal work experience model.
    Works for ANY industry by keeping core fields generic.
    """
    company: str = Field(..., description="Organization/Company name")
    position: Optional[str] = Field(None, description="Job title/role")
    location: Optional[str] = None
    dates: Optional[DateRange] = None
    employment_type: Optional[ExperienceType] = None
    
    # Responsibilities & Achievements
    description: List[str] = Field(default_factory=list, description="Bullet points")
    achievements: List[str] = Field(default_factory=list, description="Quantifiable achievements")
    
    # Industry-specific (flexible)
    technologies: List[str] = Field(default_factory=list, description="Tech/tools/methods used")
    team_size: Optional[str] = Field(None, description="Team size managed (if applicable)")
    
    # Specific Engineering Details
    highway_details: Optional[Any] = Field(None, description="Detailed info about highways, lanes, and terrain")
    tunnel_details: Optional[Any] = Field(None, description="Detailed info about tunnels")
    bridge_details: Optional[Any] = Field(None, description="Detailed info about bridges")

    # Catch-all for industry-specific details
    additional_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Industry-specific fields (e.g., project_cost, client_name, etc.)"
    )

# --- Education (Universal) ---

class Education(BaseModel):
    institution: str = Field(..., description="School/University name")
    degree: Optional[str] = Field(None, description="Degree type (B.S., M.S., Ph.D., etc.)")
    field_of_study: Optional[str] = Field(None, description="Major/Specialization")
    dates: Optional[DateRange] = None
    gpa: Optional[str] = Field(None, description="GPA/Grade/Percentage")
    location: Optional[str] = None
    honors: List[str] = Field(default_factory=list, description="Dean's list, honors, etc.")
    relevant_coursework: List[str] = Field(default_factory=list)

# --- Projects (Universal) ---

class Project(BaseModel):
    """Works for software projects, research, construction, etc."""
    title: str
    description: Optional[str] = None
    role: Optional[str] = Field(None, description="Your role in the project")
    dates: Optional[DateRange] = None
    technologies: List[str] = Field(default_factory=list)
    url: Optional[str] = Field(None, description="Link to project/demo/repo")
    
    # Flexible details
    additional_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Project-specific fields (cost, client, team_size, etc.)"
    )

# --- Certifications ---

class Certification(BaseModel):
    name: str
    issuer: Optional[str] = None
    date_issued: Optional[str] = None
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    url: Optional[str] = None

# --- Skills (Flexible Categorization) ---

class SkillCategory(BaseModel):
    category: str = Field(..., description="E.g., 'Programming', 'Languages', 'Soft Skills'")
    skills: List[str]

# --- Publications/Research ---

class Publication(BaseModel):
    title: str
    authors: List[str] = Field(default_factory=list)
    publication_date: Optional[str] = None
    publisher: Optional[str] = Field(None, description="Journal/Conference name")
    url: Optional[str] = None
    description: Optional[str] = None

# --- Main Resume Model (Universal) ---

class Resume(BaseModel):
    """
    Universal Resume Schema - Handles ANY profession.
    
    Design Philosophy:
    1. Core fields are OPTIONAL (not everyone has everything)
    2. Flexible containers catch industry-specific data
    3. LLM decides what to populate based on resume content
    """
    
    # === CORE SECTIONS (Always attempted) ===
    contact_info: ContactInfo
    
    professional_summary: Optional[str] = Field(
        None, 
        description="Summary/Objective/Profile statement"
    )
    
    work_experience: List[WorkExperience] = Field(
        default_factory=list,
        description="Employment history"
    )
    
    education: List[Education] = Field(default_factory=list)
    
    # === COMMON OPTIONAL SECTIONS ===
    skills: List[str] = Field(
        default_factory=list,
        description="Flat list of all skills"
    )
    
    skill_categories: List[SkillCategory] = Field(
        default_factory=list,
        description="Skills organized by category"
    )
    
    projects: List[Project] = Field(default_factory=list)
    
    certifications: List[Certification] = Field(default_factory=list)
    
    # === SPECIALIZED SECTIONS (Populated if found) ===
    publications: List[Publication] = Field(
        default_factory=list,
        description="Academic/Research publications"
    )
    
    awards: List[str] = Field(
        default_factory=list,
        description="Awards, honors, recognitions"
    )
    
    languages: List[str] = Field(
        default_factory=list,
        description="Spoken/written languages"
    )
    
    volunteer_experience: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Volunteer work"
    )
    
    licenses: List[str] = Field(
        default_factory=list,
        description="Professional licenses (e.g., PE, CPA, Bar)"
    )
    
    # === CATCH-ALL FOR UNKNOWN SECTIONS ===
    custom_sections: Dict[str, Any] = Field(
        default_factory=dict,
        description="Any sections not covered above (e.g., 'Hobbies', 'References', 'Patents')"
    )
    
    # === METADATA (Extracted/Calculated) ===
    total_experience_years: Optional[float] = Field(
        None,
        description="Total years of professional experience"
    )
    
    industry: Optional[str] = Field(
        None,
        description="Primary industry/field (e.g., 'Software Engineering', 'Civil Engineering')"
    )
    
    seniority_level: Optional[str] = Field(
        None,
        description="E.g., 'Entry-level', 'Mid-level', 'Senior', 'Executive'"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "contact_info": {
                    "full_name": "Jane Smith",
                    "email": "jane@example.com",
                    "github": "github.com/janesmith"
                },
                "professional_summary": "Experienced software engineer...",
                "work_experience": [
                    {
                        "company": "Tech Corp",
                        "position": "Senior Engineer",
                        "dates": {"start": "2020", "end": "Present"},
                        "description": ["Built scalable systems"],
                        "technologies": ["Python", "AWS"]
                    }
                ],
                "skills": ["Python", "JavaScript", "Leadership"],
                "total_experience_years": 8.5,
                "industry": "Software Engineering"
            }
        }