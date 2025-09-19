from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import tempfile
import os
from resume_analyzer.ai_analyzer import AIResumeAnalyzer
from resume_analyzer.resume_parser import ResumeParser
from resume_analyzer.scoring_engine import ATSScoringEngine
from resume_analyzer.strength_weakness_analyzer import StrengthWeaknessAnalyzer
from resume_analyzer.job_matcher import JobRoleMatcher
from resume_analyzer.pdf_extractor import PDFExtractor
from resume_analyzer.config import ATS_KEYWORDS, INDUSTRY_INSIGHTS


from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="Chatbot Module API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app = FastAPI(title="Chatbot Module API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize resume analyzer components
pdf_extractor = PDFExtractor()
resume_parser = ResumeParser()
scoring_engine = ATSScoringEngine()
strength_weakness_analyzer = StrengthWeaknessAnalyzer()
job_matcher = JobRoleMatcher()
ai_analyzer = AIResumeAnalyzer()

# Helper functions for resume analysis
def generate_executive_summary(sections, total_score, max_score, score_breakdown):
    """Generate executive summary from analysis results"""
    score_percentage = (total_score / max_score) * 100
    overall_assessment = score_breakdown.get('overall_assessment', {})
    
    return {
        "professional_profile": {
            "experience_level": sections.get('experience_level', 'Not determined'),
            "technical_skills_count": sections.get('skills_count', 0),
            "project_portfolio_size": sections.get('project_count', 0),
            "achievement_metrics": sections.get('quantified_achievements', 0),
            "technical_sophistication": sections.get('technical_sophistication', 'Basic')
        },
        "contact_presentation": {
            "email_address": "Present" if sections.get('email') else "Missing",
            "phone_number": "Present" if sections.get('phone') else "Missing",
            "education": "Documented" if sections.get('has_education') else "Missing",
            "resume_length": sections.get('word_count', 0),
            "action_verbs": sections.get('action_verb_count', 0)
        },
        "overall_assessment": {
            "score_percentage": score_percentage,
            "level": overall_assessment.get('level', 'Unknown'),
            "description": overall_assessment.get('description', ''),
            "recommendation": overall_assessment.get('recommendation', '')
        }
    }

def generate_detailed_scoring(score_breakdown):
    """Generate detailed scoring breakdown"""
    detailed_scores = {}
    
    for category, data in score_breakdown.items():
        if category == 'overall_assessment':
            continue
            
        category_name = category.replace('_', ' ').title()
        percentage = (data['score'] / data['max']) * 100
        
        detailed_scores[category] = {
            "score": data['score'],
            "max_score": data['max'],
            "percentage": percentage,
            "details": data.get('details', [])
        }
    
    return detailed_scores

def generate_improvement_plan(weaknesses_detailed):
    """Generate improvement plan from weaknesses"""
    # Group recommendations by priority
    critical_fixes = [w for w in weaknesses_detailed if w.get('fix_priority', '').startswith('CRITICAL')]
    high_priority = [w for w in weaknesses_detailed if w.get('fix_priority', '').startswith('HIGH')]
    medium_priority = [w for w in weaknesses_detailed if w.get('fix_priority', '').startswith('MEDIUM')]
    
    return {
        "critical_fixes": critical_fixes,
        "high_priority_improvements": high_priority,
        "medium_priority_enhancements": medium_priority,
        "implementation_timeline": [
            {"period": "Week 1-2", "task": "Fix critical contact and formatting issues", "priority": "🔴"},
            {"period": "Month 1-2", "task": "Enhance content quality and technical depth", "priority": "🟡"},
            {"period": "Month 2-3", "task": "Build project portfolio and quantified achievements", "priority": "🟠"},
            {"period": "Month 3-6", "task": "Advanced skill development and specialization", "priority": "🟢"}
        ]
    }

# Resume Analyzer Endpoints
@app.post("/analyze-resume")
async def analyze_resume(
    file: UploadFile = File(...), 
    target_role: str = None
):
    """
    Main endpoint to analyze a resume PDF and return comprehensive results
    """
    try:
        # Validate file type
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Set API key if provided
        if api_key:
            ai_analyzer.set_api_key(api_key)
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Extract text from PDF
            resume_text = pdf_extractor.extract_text_from_pdf_path(tmp_file_path)
            
            if not resume_text:
                raise HTTPException(status_code=400, detail="Failed to extract text from PDF")
            
            # Validate resume content
            is_valid, validation_message = pdf_extractor.validate_resume_content(resume_text)
            if not is_valid:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid resume content", "details": validation_message}
                )
            
            # Parse resume sections
            sections = resume_parser.extract_comprehensive_sections(resume_text)
            
            # Get AI analysis if API key is provided
            ai_comprehensive = None
            ai_targeted = None
            
            if api_key:
                try:
                    ai_comprehensive = ai_analyzer.get_comprehensive_ai_analysis(resume_text, target_role)
                    if target_role:
                        ai_targeted = ai_analyzer.get_targeted_role_analysis(resume_text, target_role)
                except Exception as e:
                    print(f"AI analysis error: {e}")
            
            # Calculate scores
            total_score, max_score, score_breakdown = scoring_engine.calculate_comprehensive_ats_score(
                resume_text, sections, target_role
            )
            
            # Get strengths and weaknesses
            strengths_detailed, weaknesses_detailed = strength_weakness_analyzer.analyze_comprehensive_strengths_weaknesses(
                resume_text, sections, target_role
            )
            
            # Get job market analysis
            job_analysis = job_matcher.get_comprehensive_job_analysis(resume_text, sections, target_role)
            
            # Prepare response
            response_data = {
                "success": True,
                "resume_metadata": {
                    "word_count": sections.get('word_count', 0),
                    "validation_message": validation_message,
                    "experience_level": sections.get('experience_level', 'Not determined'),
                    "skills_count": sections.get('skills_count', 0),
                    "project_count": sections.get('project_count', 0)
                },
                "executive_summary": generate_executive_summary(sections, total_score, max_score, score_breakdown),
                "detailed_scoring": generate_detailed_scoring(score_breakdown),
                "strengths_analysis": strengths_detailed,
                "weaknesses_analysis": weaknesses_detailed,
                "improvement_plan": generate_improvement_plan(weaknesses_detailed),
                "job_market_analysis": job_analysis,
                "ai_analysis": {
                    "comprehensive": ai_comprehensive,
                    "targeted": ai_targeted
                } if api_key else {"message": "API key required for AI analysis"}
            }
            
            return response_data
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
