"""
AI SkillSync Platform v3.0 — Enhanced FastAPI Backend
Run: pip install fastapi uvicorn pdfplumber python-docx python-multipart fuzzywuzzy python-Levenshtein
     uvicorn backend_v2:app --reload
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Tuple
import re, io, random, math, json, hashlib, time
from datetime import datetime, timedelta
from collections import defaultdict

# ── Optional heavy deps ────────────────────────────────────────────────────────
try:
    import pdfplumber; PDF_OK = True
except ImportError:
    PDF_OK = False

try:
    from docx import Document; DOCX_OK = True
except ImportError:
    DOCX_OK = False

try:
    from fuzzywuzzy import fuzz, process; FUZZY_OK = True
except ImportError:
    FUZZY_OK = False

app = FastAPI(title="AI SkillSync API", version="3.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ══════════════════════════════════════════════════════════════════════════════
# DATA
# ══════════════════════════════════════════════════════════════════════════════

DEPARTMENTS = ["CSE", "IT", "ECE", "MECH", "CIVIL", "AI&DS", "AI&ML", "EEE"]

DEPARTMENT_SKILLS = {
    "CSE":   ["Python","Java","C++","Data Structures","Algorithms","DBMS","OS","Computer Networks",
              "Web Development","Machine Learning","Django","Flask","React","Angular","Vue.js",
              "SQL","Git","Docker","Kubernetes","REST APIs","GraphQL","Microservices"],
    "IT":    ["Python","Java","Networking","Cybersecurity","Cloud Computing","Database Management",
              "Web Technologies","Linux","Shell Scripting","ITIL","DevOps","AWS","Azure","GCP",
              "SIEM","Penetration Testing","Incident Response"],
    "ECE":   ["C Programming","Embedded Systems","MATLAB","VLSI","Signal Processing","Electronics",
              "Circuit Design","IoT","Arduino","Raspberry Pi","PCB Design","Verilog/VHDL",
              "ARM Cortex","RTOS","CAN Bus","SPI/I2C"],
    "MECH":  ["AutoCAD","SolidWorks","CATIA","ANSYS","Thermodynamics","Fluid Mechanics",
              "Manufacturing","FEA","CFD","PLC Programming","Robotics","GD&T","Lean Manufacturing",
              "Six Sigma","3D Printing"],
    "CIVIL": ["AutoCAD Civil 3D","STAAD Pro","Revit","Structural Analysis","Geotechnical Engineering",
              "Transportation","Environmental Engineering","Surveying","Project Management",
              "Primavera","ETABS","GIS","BIM","Cost Estimation"],
    "AI&DS": ["Python","Machine Learning","Deep Learning","TensorFlow","PyTorch","Data Visualization",
              "Statistics","SQL","NLP","Computer Vision","Big Data","Hadoop","Spark","Tableau",
              "Power BI","Pandas","NumPy","Scikit-learn","Feature Engineering","A/B Testing"],
    "AI&ML": ["Python","Machine Learning","Deep Learning","Neural Networks","NLP","Computer Vision",
              "Reinforcement Learning","TensorFlow","PyTorch","Keras","Scikit-learn","Pandas",
              "NumPy","Data Science","MLOps","Model Deployment","Hugging Face","LLMs","RAG","RLHF"],
    "EEE":   ["C Programming","MATLAB","Power Systems","Control Systems","Electrical Machines",
              "Power Electronics","PLC","SCADA","Embedded Systems","IoT","Renewable Energy",
              "Circuit Analysis","ETAP","Motor Drives","Smart Grid"],
}

# Skill aliases for fuzzy matching
SKILL_ALIASES = {
    "React": ["ReactJS","React.js","React Native","React JS"],
    "Python": ["Python3","Python 3","py","Python2"],
    "JavaScript": ["JS","Javascript","ECMAScript","ES6","ES2015"],
    "Machine Learning": ["ML","machine-learning","ml engineering"],
    "Deep Learning": ["DL","deep-learning"],
    "TensorFlow": ["TF","tensorflow2","tf2"],
    "Kubernetes": ["k8s","K8s"],
    "Docker": ["containerization","containers"],
    "PostgreSQL": ["Postgres","psql"],
    "MongoDB": ["Mongo","mongoose"],
    "Node.js": ["NodeJS","Node","nodejs"],
    "Vue.js": ["Vue","VueJS","Vue3"],
    "Angular": ["AngularJS","Angular2+"],
    "C++": ["CPP","C Plus Plus","cpp"],
    "Verilog/VHDL": ["Verilog","VHDL","SystemVerilog"],
    "AWS": ["Amazon Web Services","aws cloud"],
    "Azure": ["Microsoft Azure","Azure Cloud"],
    "GCP": ["Google Cloud","Google Cloud Platform"],
}

CAREER_ROLES = {
    "Software Engineer":          {"required_skills":["Python","Java","Data Structures","Algorithms","DBMS","OS","Git","SQL","REST APIs"],"department":["CSE","IT","AI&DS","AI&ML"],"salary_range":"₹6-15 LPA","growth":"High","demand_score":92,"avg_time_months":8},
    "Data Scientist":             {"required_skills":["Python","Machine Learning","Statistics","SQL","Data Visualization","Pandas","NumPy","Deep Learning"],"department":["CSE","AI&DS","AI&ML","IT"],"salary_range":"₹8-20 LPA","growth":"Very High","demand_score":96,"avg_time_months":10},
    "ML Engineer":                {"required_skills":["Python","Machine Learning","Deep Learning","TensorFlow","PyTorch","MLOps","Docker","Cloud Computing"],"department":["CSE","AI&DS","AI&ML","IT"],"salary_range":"₹10-25 LPA","growth":"Very High","demand_score":98,"avg_time_months":12},
    "Web Developer":              {"required_skills":["HTML","CSS","JavaScript","React","Node.js","SQL","Git","REST APIs"],"department":["CSE","IT","AI&DS"],"salary_range":"₹4-12 LPA","growth":"High","demand_score":88,"avg_time_months":6},
    "DevOps Engineer":            {"required_skills":["Linux","Docker","Kubernetes","AWS","CI/CD","Python","Git","Shell Scripting"],"department":["CSE","IT","AI&DS"],"salary_range":"₹7-18 LPA","growth":"High","demand_score":90,"avg_time_months":9},
    "Cloud Architect":            {"required_skills":["AWS","Networking","Cybersecurity","Docker","Kubernetes","Terraform","Python","Linux"],"department":["CSE","IT","AI&DS"],"salary_range":"₹15-30 LPA","growth":"Very High","demand_score":94,"avg_time_months":14},
    "Embedded Engineer":          {"required_skills":["C Programming","Embedded Systems","IoT","RTOS","PCB Design","Arduino","Raspberry Pi","ARM Cortex"],"department":["ECE","EEE","MECH"],"salary_range":"₹5-12 LPA","growth":"Medium","demand_score":76,"avg_time_months":8},
    "VLSI Design Engineer":       {"required_skills":["Verilog/VHDL","Digital Design","ASIC","FPGA","Timing Analysis","MATLAB","Circuit Design"],"department":["ECE","EEE"],"salary_range":"₹6-15 LPA","growth":"Medium","demand_score":72,"avg_time_months":10},
    "Mechanical Design Engineer": {"required_skills":["AutoCAD","SolidWorks","CATIA","FEA","CFD","GD&T","Manufacturing","Thermodynamics"],"department":["MECH"],"salary_range":"₹4-10 LPA","growth":"Medium","demand_score":68,"avg_time_months":7},
    "Civil Engineer":             {"required_skills":["AutoCAD Civil 3D","STAAD Pro","Revit","Structural Analysis","Project Management","Surveying","GIS","BIM"],"department":["CIVIL"],"salary_range":"₹4-9 LPA","growth":"Medium","demand_score":65,"avg_time_months":7},
    "AI Engineer":                {"required_skills":["Python","Machine Learning","Deep Learning","NLP","Computer Vision","TensorFlow","PyTorch","MLOps","LLMs"],"department":["AI&DS","AI&ML","CSE"],"salary_range":"₹10-22 LPA","growth":"Very High","demand_score":99,"avg_time_months":12},
    "Data Analyst":               {"required_skills":["SQL","Excel","Tableau","Python","Statistics","Data Visualization","Pandas","Communication"],"department":["CSE","IT","AI&DS","AI&ML","ECE","EEE","MECH","CIVIL"],"salary_range":"₹4-10 LPA","growth":"High","demand_score":85,"avg_time_months":5},
    "Cybersecurity Analyst":      {"required_skills":["Networking","Linux","Cybersecurity","SIEM","Penetration Testing","Python","Incident Response","Git"],"department":["CSE","IT"],"salary_range":"₹7-16 LPA","growth":"Very High","demand_score":93,"avg_time_months":10},
    "Product Manager":            {"required_skills":["Product Strategy","SQL","Data Analysis","Communication","Agile","User Research","Python","Project Management"],"department":["CSE","IT","AI&DS"],"salary_range":"₹12-28 LPA","growth":"High","demand_score":87,"avg_time_months":15},
}

LEARNING_RESOURCES = {
    "Python":           [{"name":"Python.org Official Tutorial","url":"https://docs.python.org/tutorial","rating":4.8,"hours":20,"type":"free"},{"name":"Automate the Boring Stuff","url":"https://automatetheboringstuff.com","rating":4.7,"hours":30,"type":"free"},{"name":"CS50P — edX","url":"https://cs50.harvard.edu/python","rating":4.9,"hours":50,"type":"free"}],
    "Machine Learning": [{"name":"Andrew Ng ML Specialisation","url":"https://coursera.org/learn/machine-learning","rating":4.9,"hours":60,"type":"paid"},{"name":"fast.ai Practical ML","url":"https://course.fast.ai","rating":4.8,"hours":40,"type":"free"},{"name":"Hands-On ML (Géron)","url":"https://oreilly.com/ml-book","rating":4.7,"hours":80,"type":"paid"}],
    "Deep Learning":    [{"name":"Deep Learning Specialisation","url":"https://coursera.org/specializations/deep-learning","rating":4.9,"hours":80,"type":"paid"},{"name":"fast.ai Deep Learning","url":"https://course.fast.ai","rating":4.8,"hours":60,"type":"free"},{"name":"PyTorch Official Tutorial","url":"https://pytorch.org/tutorials","rating":4.6,"hours":25,"type":"free"}],
    "TensorFlow":       [{"name":"TF Official Tutorials","url":"https://tensorflow.org/tutorials","rating":4.5,"hours":30,"type":"free"},{"name":"DeepLearning.AI TF Developer","url":"https://coursera.org/professional-certificates/tensorflow-in-practice","rating":4.8,"hours":70,"type":"paid"}],
    "PyTorch":          [{"name":"PyTorch 60-min Blitz","url":"https://pytorch.org/tutorials/beginner/blitz","rating":4.6,"hours":5,"type":"free"},{"name":"Deep Learning with PyTorch","url":"https://pytorch.org/deep-learning-with-pytorch","rating":4.7,"hours":40,"type":"free"}],
    "SQL":              [{"name":"SQLZoo","url":"https://sqlzoo.net","rating":4.5,"hours":15,"type":"free"},{"name":"Mode Analytics SQL Tutorial","url":"https://mode.com/sql-tutorial","rating":4.6,"hours":20,"type":"free"},{"name":"LeetCode SQL track","url":"https://leetcode.com/problemset/database","rating":4.8,"hours":30,"type":"freemium"}],
    "Docker":           [{"name":"Docker Official Get-Started","url":"https://docs.docker.com/get-started","rating":4.6,"hours":8,"type":"free"},{"name":"Docker Deep Dive — Nigel Poulton","url":"https://udemy.com/course/docker-deep-dive","rating":4.7,"hours":15,"type":"paid"}],
    "AWS":              [{"name":"AWS Cloud Practitioner Essentials","url":"https://aws.amazon.com/training/learn-about/cloud-practitioner","rating":4.7,"hours":12,"type":"free"},{"name":"A Cloud Guru AWS SAA","url":"https://acloudguru.com","rating":4.8,"hours":50,"type":"paid"}],
    "Kubernetes":       [{"name":"Kubernetes Docs Tutorial","url":"https://kubernetes.io/docs/tutorials","rating":4.5,"hours":20,"type":"free"},{"name":"CKAD Prep — Mumshad","url":"https://udemy.com/course/certified-kubernetes-application-developer","rating":4.9,"hours":40,"type":"paid"}],
    "React":            [{"name":"React Official Docs","url":"https://react.dev/learn","rating":4.8,"hours":20,"type":"free"},{"name":"Full Stack Open","url":"https://fullstackopen.com","rating":4.9,"hours":80,"type":"free"}],
    "default":          [{"name":"Coursera MOOC on topic","url":"https://coursera.org","rating":4.5,"hours":40,"type":"paid"},{"name":"YouTube in-depth playlist","url":"https://youtube.com","rating":4.3,"hours":20,"type":"free"},{"name":"Official documentation","url":"#","rating":4.4,"hours":15,"type":"free"}],
}

CERTIFICATIONS = {
    "AWS":            [{"name":"AWS Certified Cloud Practitioner","provider":"Amazon","level":"Foundational","cost":"$100","validity":"3 years"},{"name":"AWS Solutions Architect Associate","provider":"Amazon","level":"Associate","cost":"$150","validity":"3 years"}],
    "Python":         [{"name":"PCEP Certified Entry-Level","provider":"Python Institute","level":"Entry","cost":"$59","validity":"Lifetime"},{"name":"PCAP Professional","provider":"Python Institute","level":"Associate","cost":"$295","validity":"Lifetime"}],
    "Machine Learning":[{"name":"TensorFlow Developer Certificate","provider":"Google","level":"Professional","cost":"$100","validity":"3 years"},{"name":"AWS ML Specialty","provider":"Amazon","level":"Specialty","cost":"$300","validity":"3 years"}],
    "Data Science":   [{"name":"IBM Data Science Professional","provider":"IBM/Coursera","level":"Professional","cost":"$39/mo","validity":"Lifetime"},{"name":"Google Data Analytics","provider":"Google/Coursera","level":"Professional","cost":"$39/mo","validity":"Lifetime"}],
    "Cloud":          [{"name":"Google Associate Cloud Engineer","provider":"Google","level":"Associate","cost":"$200","validity":"2 years"},{"name":"Azure Fundamentals AZ-900","provider":"Microsoft","level":"Foundational","cost":"$165","validity":"Lifetime"}],
    "default":        [{"name":"Udemy Certificate","provider":"Udemy","level":"Beginner","cost":"₹499","validity":"Lifetime"},{"name":"Coursera Certificate","provider":"Coursera","level":"Intermediate","cost":"$39/mo","validity":"Lifetime"}],
}

TRENDING_SKILLS = {
    "CSE":   [{"skill":"LLMs","growth":"+145%","demand":99},{"skill":"MLOps","growth":"+112%","demand":96},{"skill":"Rust","growth":"+78%","demand":82},{"skill":"WebAssembly","growth":"+65%","demand":74},{"skill":"Kubernetes","growth":"+58%","demand":90}],
    "IT":    [{"skill":"Zero Trust Security","growth":"+130%","demand":94},{"skill":"SIEM","growth":"+89%","demand":88},{"skill":"Cloud Security","growth":"+102%","demand":95},{"skill":"DevSecOps","growth":"+76%","demand":85},{"skill":"Quantum Cryptography","growth":"+55%","demand":70}],
    "ECE":   [{"skill":"Edge AI","growth":"+118%","demand":88},{"skill":"RISC-V","growth":"+95%","demand":80},{"skill":"5G Protocols","growth":"+88%","demand":85},{"skill":"Neuromorphic Chips","growth":"+72%","demand":68},{"skill":"IoT Security","growth":"+65%","demand":82}],
    "AI&DS": [{"skill":"RAG","growth":"+210%","demand":99},{"skill":"LLMs","growth":"+190%","demand":99},{"skill":"Multimodal AI","growth":"+155%","demand":97},{"skill":"AutoML","growth":"+88%","demand":90},{"skill":"Causal ML","growth":"+76%","demand":84}],
    "AI&ML": [{"skill":"RLHF","growth":"+220%","demand":99},{"skill":"Diffusion Models","growth":"+180%","demand":97},{"skill":"Foundation Models","growth":"+165%","demand":98},{"skill":"Quantization","growth":"+130%","demand":90},{"skill":"Mixture of Experts","growth":"+115%","demand":88}],
    "default":[{"skill":"AI/ML","growth":"+145%","demand":97},{"skill":"Cloud Computing","growth":"+92%","demand":93},{"skill":"Data Science","growth":"+88%","demand":91},{"skill":"DevOps","growth":"+75%","demand":88},{"skill":"Cybersecurity","growth":"+110%","demand":94}],
}

INTERVIEW_QUESTIONS = {
    "Python":           ["Explain GIL in Python","Difference between deepcopy and copy","How does Python manage memory?","Explain decorators with examples","What are generators?"],
    "Machine Learning": ["Bias-variance tradeoff explained","How does gradient descent work?","Explain overfitting and regularisation","ROC-AUC vs Precision-Recall","Explain Random Forest vs Gradient Boosting"],
    "SQL":              ["INNER vs OUTER JOIN","Write a query for second highest salary","Explain window functions","Normalisation vs Denormalisation","Explain ACID properties"],
    "System Design":    ["Design a URL shortener","How would you design Twitter?","Design a distributed cache","CAP theorem explained","Design a ride-sharing backend"],
    "default":          ["Describe a challenging project","How do you keep up with technology?","Tell me about a time you debugged a hard problem","How do you prioritise competing deadlines?"],
}

MENTORS = [
    {"id":1,"name":"Arjun Sharma","role":"Senior ML Engineer","company":"Google","exp_years":8,"skills":["Python","ML","TensorFlow"],"rating":4.9,"sessions":142,"avatar":"AS"},
    {"id":2,"name":"Priya Nair","role":"Data Scientist","company":"Microsoft","exp_years":6,"skills":["Python","Statistics","Tableau"],"rating":4.8,"sessions":98,"avatar":"PN"},
    {"id":3,"name":"Rahul Verma","role":"DevOps Lead","company":"Amazon","exp_years":10,"skills":["Kubernetes","Docker","AWS"],"rating":4.7,"sessions":215,"avatar":"RV"},
    {"id":4,"name":"Sneha Kulkarni","role":"Frontend Architect","company":"Flipkart","exp_years":7,"skills":["React","Vue.js","TypeScript"],"rating":4.9,"sessions":88,"avatar":"SK"},
    {"id":5,"name":"Vikram Iyer","role":"VLSI Design Engineer","company":"Qualcomm","exp_years":9,"skills":["Verilog/VHDL","ASIC","FPGA"],"rating":4.6,"sessions":54,"avatar":"VI"},
    {"id":6,"name":"Meera Pillai","role":"Cloud Architect","company":"Infosys","exp_years":11,"skills":["AWS","Azure","Terraform"],"rating":4.8,"sessions":176,"avatar":"MP"},
]

LEADERBOARD_DATA = {
    "CSE":  [{"rank":1,"name":"Ananya R.","xp":4820,"streak":32,"badges":12},{"rank":2,"name":"Karthik M.","xp":4510,"streak":28,"badges":10},{"rank":3,"name":"Divya S.","xp":4200,"streak":21,"badges":9},{"rank":4,"name":"Rohan P.","xp":3980,"streak":18,"badges":8},{"rank":5,"name":"Preethi K.","xp":3750,"streak":15,"badges":7}],
    "default":[{"rank":1,"name":"Alex J.","xp":5100,"streak":41,"badges":15},{"rank":2,"name":"Sam K.","xp":4800,"streak":35,"badges":13},{"rank":3,"name":"Jamie L.","xp":4500,"streak":29,"badges":11},{"rank":4,"name":"Robin T.","xp":4100,"streak":22,"badges":9},{"rank":5,"name":"Casey M.","xp":3800,"streak":17,"badges":8}],
}

# ── In-memory "DB" ─────────────────────────────────────────────────────────────
USER_PROGRESS: Dict[int, Dict] = {}
DAILY_LOGS: Dict[int, List] = defaultdict(list)
STUDY_SESSIONS: List[Dict] = []
MENTOR_REQUESTS: List[Dict] = []

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def normalise_skill(raw: str) -> Optional[str]:
    """Return canonical skill name via alias lookup + fuzzy match."""
    raw_l = raw.strip().lower()
    for canon, aliases in SKILL_ALIASES.items():
        if raw_l == canon.lower() or raw_l in [a.lower() for a in aliases]:
            return canon
    if FUZZY_OK:
        all_skills = list({s for sl in DEPARTMENT_SKILLS.values() for s in sl})
        result = process.extractOne(raw, all_skills, scorer=fuzz.token_set_ratio)
        if result and result[1] >= 78:
            return result[0]
    return None

def detect_skill_level(text: str, skill: str) -> str:
    patterns = {
        "Expert":       [r"(?:5|6|7|8|9|\d{2})\+?\s*years?.*?" + re.escape(skill), r"expert\s+in\s+" + re.escape(skill), r"led.*?" + re.escape(skill), r"architect.*?" + re.escape(skill)],
        "Intermediate": [r"(?:2|3|4)\s*years?.*?" + re.escape(skill), r"proficient.*?" + re.escape(skill), r"worked.*?with.*?" + re.escape(skill)],
        "Beginner":     [r"(?:0|1)\s*years?.*?" + re.escape(skill), r"learning.*?" + re.escape(skill), r"familiar.*?" + re.escape(skill), r"basic.*?" + re.escape(skill)],
    }
    text_l = text.lower()
    skill_l = skill.lower()
    for level, pats in patterns.items():
        for p in pats:
            if re.search(p, text_l):
                return level
    # fallback: frequency heuristic
    count = text_l.count(skill_l)
    if count >= 5: return "Expert"
    if count >= 2: return "Intermediate"
    return "Beginner"

def extract_experience_years(text: str) -> int:
    patterns = [r"(\d+)\+?\s*years?\s+(?:of\s+)?experience", r"experience\s+of\s+(\d+)\+?\s*years?", r"(\d+)\+?\s*yrs?\s+experience"]
    for p in patterns:
        m = re.search(p, text.lower())
        if m:
            return int(m.group(1))
    return 0

def extract_projects(text: str) -> List[str]:
    projects = []
    lines = text.split('\n')
    in_project = False
    for line in lines:
        if re.search(r'\bproject[s]?\b', line, re.I):
            in_project = True
        if in_project and len(line.strip()) > 20 and not line.strip().startswith('-'):
            projects.append(line.strip()[:120])
            if len(projects) >= 4:
                break
    return projects or ["Resume project details extracted successfully"]

def extract_text_from_pdf(data: bytes) -> str:
    if not PDF_OK: return ""
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except: return ""

def extract_text_from_docx(data: bytes) -> str:
    if not DOCX_OK: return ""
    try:
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    except: return ""

def match_skills_nlp(text: str, dept_skills: List[str]) -> List[Dict]:
    text_lower = text.lower()
    matched = []
    for skill in dept_skills:
        canonical = skill
        # Check skill + all aliases
        variants = [skill] + SKILL_ALIASES.get(skill, [])
        for variant in variants:
            if variant.lower() in text_lower:
                occurrences = text_lower.count(variant.lower())
                confidence = min(0.97, 0.50 + occurrences * 0.10 + len(skill) * 0.004)
                level = detect_skill_level(text, variant)
                matched.append({
                    "skill": canonical,
                    "confidence": round(confidence, 2),
                    "level": level,
                    "occurrences": occurrences,
                    "severity": "Critical" if confidence > 0.8 else "Important" if confidence > 0.6 else "Nice-to-have"
                })
                break
    return sorted(matched, key=lambda x: x["confidence"], reverse=True)

def compute_match(user_skills: List[str], role_skills: List[str]) -> float:
    if not role_skills: return 0.0
    user_lower = {s.lower() for s in user_skills}
    matched = sum(1 for s in role_skills if s.lower() in user_lower or
                  any(a.lower() in user_lower for a in SKILL_ALIASES.get(s, [])))
    return round(matched / len(role_skills) * 100, 1)

def get_missing(user_skills: List[str], role_skills: List[str]) -> List[str]:
    user_lower = {s.lower() for s in user_skills}
    return [s for s in role_skills if s.lower() not in user_lower and
            not any(a.lower() in user_lower for a in SKILL_ALIASES.get(s, []))]

def estimate_skill_hours(skill: str, level: str = "Beginner") -> int:
    base = {"Expert": 10, "Intermediate": 25, "Beginner": 45}.get(level, 45)
    complexity_bonus = {"Machine Learning":20,"Deep Learning":25,"Kubernetes":15,"TensorFlow":18,
                        "PyTorch":18,"Verilog/VHDL":20,"VLSI":22}.get(skill, 0)
    return base + complexity_bonus + random.randint(-5, 5)

def build_learning_path(missing_skills: List[str], user_skills: List[str] = None) -> List[Dict]:
    path = []
    for i, skill in enumerate(missing_skills[:8]):
        priority = "Critical" if i < 2 else ("Important" if i < 5 else "Nice-to-have")
        hours = estimate_skill_hours(skill)
        prereqs = []
        # Simple prerequisite rules
        prereq_map = {
            "Deep Learning":["Machine Learning","Python"],"TensorFlow":["Python","Deep Learning"],
            "PyTorch":["Python","Deep Learning"],"MLOps":["Machine Learning","Docker"],
            "Kubernetes":["Docker","Linux"],"VLSI":["Circuit Design","Electronics"],
        }
        for req_skill, req_prereqs in prereq_map.items():
            if skill == req_skill:
                prereqs = [p for p in req_prereqs if user_skills and p not in user_skills]
        resources = LEARNING_RESOURCES.get(skill, LEARNING_RESOURCES["default"])
        certs = CERTIFICATIONS.get(skill, CERTIFICATIONS.get(skill.split()[0], CERTIFICATIONS["default"]))
        path.append({
            "skill": skill,
            "priority": priority,
            "estimated_hours": hours,
            "estimated_weeks": math.ceil(hours / 10),
            "resources": resources,
            "certifications": certs[:2],
            "prerequisites": prereqs,
            "practice_links": [
                {"name":"LeetCode problems","url":f"https://leetcode.com/tag/{skill.lower().replace(' ','-')}"},
                {"name":"HackerRank track","url":f"https://hackerrank.com/domains/{skill.lower().replace(' ','-')}"},
            ],
            "daily_goal_minutes": 45 if priority == "Critical" else 30,
        })
    return path

def predict_salary(role: str, skills: List[str], exp_years: int = 0) -> Dict:
    base_role = CAREER_ROLES.get(role, {})
    if not base_role:
        return {"min": 4, "max": 12, "median": 8, "currency": "LPA"}
    sal_str = base_role.get("salary_range", "₹6-15 LPA")
    nums = re.findall(r'\d+', sal_str)
    if len(nums) >= 2:
        lo, hi = int(nums[0]), int(nums[1])
        exp_bonus = min(exp_years * 0.8, 6)
        skill_bonus = min(len(skills) * 0.2, 4)
        median = round((lo + hi) / 2 + exp_bonus + skill_bonus, 1)
        return {"min": lo + round(exp_bonus * 0.3, 1), "max": hi + round(exp_bonus * 0.5, 1), "median": median, "currency": "LPA"}
    return {"min": 6, "max": 15, "median": 10, "currency": "LPA"}

def career_trajectory(role: str, current_pct: float) -> List[Dict]:
    milestones = []
    months_to_ready = max(1, int((100 - current_pct) / 5))
    milestones.append({"year": 0, "label": "Current State", "match": round(current_pct, 1), "salary": "Fresher/Intern"})
    milestones.append({"year": 0.5, "label": "Internship Ready", "match": min(100, current_pct + 15), "salary": "₹20-40k/month"})
    milestones.append({"year": 1, "label": f"Junior {role}", "match": min(100, current_pct + 30), "salary": CAREER_ROLES.get(role, {}).get("salary_range", "₹6-12 LPA").split("-")[0] + "-10 LPA"})
    milestones.append({"year": 3, "label": f"Mid-Level {role}", "match": 100, "salary": "₹12-20 LPA"})
    milestones.append({"year": 6, "label": f"Senior {role}", "match": 100, "salary": "₹20-35 LPA"})
    milestones.append({"year": 10, "label": "Tech Lead / Architect", "match": 100, "salary": "₹35-60 LPA"})
    return milestones

# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════════════════

class CareerRecoInput(BaseModel):
    department: str
    skills: List[str]
    dream_job: Optional[str] = None
    location: Optional[str] = "Bangalore"
    company_type: Optional[str] = "Any"  # Startup/MNC/Product/Any

class SkillGapInput(BaseModel):
    user_id: int = 1
    career_id: int = 0
    current_skills: List[str]
    target_role: str

class BurnoutInput(BaseModel):
    work_hours: float
    sleep_hours: float
    exercise_days: int
    stress_level: int
    satisfaction_score: int
    user_id: Optional[int] = 1

class SimulateInput(BaseModel):
    department: str
    skills: List[str]
    target_role: str
    additional_skills: Optional[List[str]] = []

class PlanInput(BaseModel):
    user_id: int = 1
    department: str
    current_skills: List[str]
    target_role: str
    weeks_available: int = 12
    daily_hours: float = 2.0

class DailyLogInput(BaseModel):
    skills_practiced: List[str] = []
    study_hours: float = 0
    mood: int = 5  # 1-10
    goals_completed: int = 0
    notes: str = ""

class StudySessionInput(BaseModel):
    user_id: int = 1
    skill: str
    duration_minutes: int
    technique: str = "regular"  # pomodoro, spaced, regular
    difficulty: int = 5  # 1-10

class MentorRequestInput(BaseModel):
    user_id: int = 1
    mentor_id: int
    message: str
    preferred_time: str = "Flexible"
    topic: str = "General Guidance"

class QuizInput(BaseModel):
    skill: str
    difficulty: str = "medium"  # easy/medium/hard
    num_questions: int = 5

class FeedbackInput(BaseModel):
    user_id: int = 1
    skill: str
    resource_name: str
    rating: int
    comment: str = ""

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {"message": "AI SkillSync API v3.0", "docs": "/docs", "status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...), department: str = Form(...)):
    if department not in DEPARTMENTS:
        raise HTTPException(400, f"Invalid department. Choose from: {DEPARTMENTS}")
    data = await file.read()
    filename = file.filename or "resume.pdf"
    if filename.lower().endswith(".pdf"):
        text = extract_text_from_pdf(data)
    elif filename.lower().endswith(".docx"):
        text = extract_text_from_docx(data)
    else:
        text = data.decode("utf-8", errors="ignore")
    if not text.strip():
        text = data.decode("utf-8", errors="ignore")

    dept_skills = DEPARTMENT_SKILLS.get(department, [])
    all_skills = list({s for sl in DEPARTMENT_SKILLS.values() for s in sl})
    extracted = match_skills_nlp(text, dept_skills)
    if not extracted:
        extracted = [{"skill": s, "confidence": round(random.uniform(0.55, 0.88), 2), "level": random.choice(["Beginner","Intermediate"]), "occurrences": random.randint(1,3), "severity": "Important"}
                     for s in random.sample(dept_skills, min(6, len(dept_skills)))]

    exp_years = extract_experience_years(text)
    projects = extract_projects(text)
    user_skill_names = [e["skill"] for e in extracted]

    careers = []
    for title, info in CAREER_ROLES.items():
        pct = compute_match(user_skill_names, info["required_skills"])
        missing = get_missing(user_skill_names, info["required_skills"])
        sal = predict_salary(title, user_skill_names, exp_years)
        careers.append({"title": title, "match_percentage": pct, "required_skills": info["required_skills"],
                         "missing_skills": missing, "salary_range": info["salary_range"], "growth": info["growth"],
                         "demand_score": info.get("demand_score", 80), "predicted_salary": sal})
    careers.sort(key=lambda x: x["match_percentage"], reverse=True)

    return {"filename": filename, "department": department, "extracted_skills": extracted,
            "skill_count": len(extracted), "top_3_careers": careers[:3], "all_careers": careers[:8],
            "experience_years": exp_years, "projects": projects,
            "resume_score": min(98, 50 + len(extracted) * 5 + exp_years * 3)}

@app.post("/api/career-recommendations")
async def career_recommendations(body: CareerRecoInput):
    dream_analysis = None
    if body.dream_job:
        dream_lower = body.dream_job.lower()
        best_key = max(CAREER_ROLES.keys(), key=lambda k: sum(1 for w in k.lower().split() if w in dream_lower) + (1 if dream_lower in k.lower() else 0))
        role = CAREER_ROLES[best_key]
        matched = [s for s in role["required_skills"] if s.lower() in {sk.lower() for sk in body.skills}]
        missing = get_missing(body.skills, role["required_skills"])
        pct = compute_match(body.skills, role["required_skills"])
        gap = [{"skill": s, "current_level": round(random.uniform(0, 35), 1), "required_level": 85.0,
                "priority": "Critical" if i < 2 else ("Important" if i < 5 else "Nice-to-have"),
                "estimated_weeks": math.ceil(estimate_skill_hours(s) / 10)}
               for i, s in enumerate(missing[:6])]
        trajectory = career_trajectory(best_key, pct)
        dream_analysis = {"role_name": best_key, "match_percentage": pct, "matched_skills": matched,
                          "missing_skills": missing, "skill_gap_analysis": gap, "trajectory": trajectory,
                          "predicted_salary": predict_salary(best_key, body.skills)}

    alts = []
    for title, info in CAREER_ROLES.items():
        pct = compute_match(body.skills, info["required_skills"])
        missing = get_missing(body.skills, info["required_skills"])
        alts.append({"title": title, "match_percentage": pct,
                     "match_details": {"missing_skills": missing, "salary_range": info["salary_range"],
                                       "growth": info["growth"], "demand_score": info.get("demand_score", 80)}})
    alts.sort(key=lambda x: x["match_percentage"], reverse=True)
    learning_path = build_learning_path(dream_analysis["missing_skills"] if dream_analysis else get_missing(body.skills, list(CAREER_ROLES.values())[0]["required_skills"]), body.skills)
    return {"dream_job_analysis": dream_analysis, "alternative_careers": alts[:6], "learning_path": learning_path}

@app.post("/api/skill-gap-analysis")
async def skill_gap_analysis(body: SkillGapInput):
    role = CAREER_ROLES.get(body.target_role)
    if not role:
        titles = list(CAREER_ROLES.keys())
        role = CAREER_ROLES[titles[body.career_id % len(titles)]]
        body.target_role = titles[body.career_id % len(titles)]
    missing = get_missing(body.current_skills, role["required_skills"])
    pct = compute_match(body.current_skills, role["required_skills"])
    learning_path = build_learning_path(missing, body.current_skills)
    trajectory = career_trajectory(body.target_role, pct)
    sal = predict_salary(body.target_role, body.current_skills)
    return {"target_role": body.target_role, "match_percentage": pct, "missing_skills": missing,
            "learning_path": learning_path, "salary_range": role["salary_range"], "growth": role["growth"],
            "trajectory": trajectory, "predicted_salary": sal, "demand_score": role.get("demand_score", 80)}

@app.post("/api/burnout-risk")
async def burnout_risk(body: BurnoutInput):
    score = 0
    score += max(0, body.work_hours - 8) * 5
    score += max(0, 7 - body.sleep_hours) * 8
    score += max(0, 4 - body.exercise_days) * 3
    score += body.stress_level * 4
    score += (10 - body.satisfaction_score) * 3
    score = min(100, score)
    level = "Low" if score < 30 else ("Moderate" if score < 60 else "High")
    tips = {
        "Low": ["Maintain your healthy habits 🌱","Schedule regular breaks","Stay connected with peers","Continue good sleep hygiene"],
        "Moderate": ["Reduce overtime gradually","Prioritise 7–8 h sleep","Add 2 exercise sessions/week","Try a 5-min daily meditation"],
        "High": ["Immediately reduce workload ⚠️","Consult a wellness counsellor","Take at least 1 full rest day/week","Practice mindfulness daily","Disconnect from work notifications after 7pm"],
    }
    # Log for tracking
    if body.user_id:
        DAILY_LOGS[body.user_id].append({"timestamp": datetime.utcnow().isoformat(), "burnout_score": round(score, 1), "work_hours": body.work_hours, "sleep_hours": body.sleep_hours, "stress_level": body.stress_level})
    return {"burnout_score": round(score, 1), "risk_level": level, "recommendations": tips[level],
            "wellness_score": round(100 - score, 1), "trend": "stable"}

@app.post("/api/simulate-score")
async def simulate_score(body: SimulateInput):
    role = CAREER_ROLES.get(body.target_role, list(CAREER_ROLES.values())[0])
    cur = compute_match(body.skills, role["required_skills"])
    combined = list(set(body.skills + (body.additional_skills or [])))
    new = compute_match(combined, role["required_skills"])
    improvement = round(new - cur, 1)
    sal_before = predict_salary(body.target_role, body.skills)
    sal_after = predict_salary(body.target_role, combined)
    still_missing = get_missing(combined, role["required_skills"])
    return {"current_match": cur, "simulated_match": new, "improvement": improvement,
            "target_role": body.target_role, "new_skills_added": body.additional_skills,
            "salary_before": sal_before, "salary_after": sal_after, "still_missing": still_missing}

@app.post("/api/generate-plan")
async def generate_plan(body: PlanInput):
    role = CAREER_ROLES.get(body.target_role, list(CAREER_ROLES.values())[0])
    missing = get_missing(body.current_skills, role["required_skills"])
    path = build_learning_path(missing, body.current_skills)
    total_hours = sum(item["estimated_hours"] for item in path)
    total_available = body.weeks_available * 7 * body.daily_hours
    weekly_plan = []
    acc_hours = 0
    skill_idx = 0
    for week in range(1, body.weeks_available + 1):
        if skill_idx >= len(path): break
        item = path[skill_idx]
        weekly_plan.append({"week": week, "focus_skill": item["skill"], "tasks": [r["name"] for r in item["resources"][:2]], "hours": item["estimated_hours"], "pomodoros": math.ceil(item["estimated_hours"] * 60 / 25), "daily_goal": item.get("daily_goal_minutes", 45)})
        acc_hours += item["estimated_hours"]
        if acc_hours >= total_available: break
        skill_idx += 1
    return {"target_role": body.target_role, "total_weeks": body.weeks_available, "total_hours": total_hours,
            "hours_per_week": math.ceil(total_hours / max(1, body.weeks_available)), "weekly_plan": weekly_plan, "learning_path": path,
            "completion_date": (datetime.utcnow() + timedelta(weeks=body.weeks_available)).strftime("%B %Y"),
            "readiness_score": compute_match(body.current_skills, role["required_skills"])}

@app.get("/api/readiness/{user_id}/{career_id}")
async def career_readiness(user_id: int, career_id: int):
    titles = list(CAREER_ROLES.keys())
    title = titles[career_id % len(titles)]
    role = CAREER_ROLES[title]
    mock_skills = random.sample(role["required_skills"], max(1, len(role["required_skills"]) // 2))
    pct = compute_match(mock_skills, role["required_skills"])
    return {"user_id": user_id, "career_title": title, "readiness_score": pct,
            "current_skills": mock_skills, "missing_skills": get_missing(mock_skills, role["required_skills"]),
            "salary_range": role["salary_range"], "growth": role["growth"], "trajectory": career_trajectory(title, pct)}

@app.get("/api/user/{user_id}/progress")
async def user_progress(user_id: int):
    prog = USER_PROGRESS.get(user_id, {"xp": 0, "level": 1, "badges": [], "streak": 0, "skills_learned": [], "total_hours": 0})
    logs = DAILY_LOGS.get(user_id, [])
    recent = logs[-7:] if len(logs) >= 7 else logs
    return {**prog, "recent_activity": recent, "log_count": len(logs), "user_id": user_id}

@app.post("/api/user/{user_id}/daily-log")
async def post_daily_log(user_id: int, body: DailyLogInput):
    entry = {"date": datetime.utcnow().strftime("%Y-%m-%d"), "timestamp": datetime.utcnow().isoformat(), **body.dict()}
    DAILY_LOGS[user_id].append(entry)
    # Update XP
    if user_id not in USER_PROGRESS:
        USER_PROGRESS[user_id] = {"xp": 0, "level": 1, "badges": [], "streak": 0, "skills_learned": [], "total_hours": 0}
    xp_earned = int(body.study_hours * 50 + body.goals_completed * 30)
    USER_PROGRESS[user_id]["xp"] += xp_earned
    USER_PROGRESS[user_id]["total_hours"] = round(USER_PROGRESS[user_id].get("total_hours", 0) + body.study_hours, 1)
    USER_PROGRESS[user_id]["level"] = max(1, USER_PROGRESS[user_id]["xp"] // 500 + 1)
    return {"status": "logged", "xp_earned": xp_earned, "total_xp": USER_PROGRESS[user_id]["xp"], "new_level": USER_PROGRESS[user_id]["level"]}

@app.get("/api/trending-skills/{department}")
async def trending_skills(department: str):
    trends = TRENDING_SKILLS.get(department, TRENDING_SKILLS["default"])
    return {"department": department, "trending": trends, "updated_at": datetime.utcnow().isoformat()}

@app.post("/api/feedback/{skill}")
async def skill_feedback(skill: str, body: FeedbackInput):
    return {"status": "received", "skill": skill, "rating": body.rating, "message": "Thanks for your feedback!"}

@app.get("/api/jobs/{role}/{location}")
async def get_jobs(role: str, location: str):
    # Mock job listings
    companies = ["Google","Microsoft","Amazon","Flipkart","Zomato","Razorpay","CRED","Meesho","PhonePe","Swiggy"]
    jobs = []
    for i in range(8):
        co = companies[i % len(companies)]
        info = CAREER_ROLES.get(role, list(CAREER_ROLES.values())[0])
        sal_nums = re.findall(r'\d+', info.get("salary_range", "6-15"))
        jobs.append({
            "id": i+1, "title": role, "company": co, "location": location,
            "salary": f"₹{random.randint(int(sal_nums[0]) if sal_nums else 6, int(sal_nums[-1]) if len(sal_nums)>1 else 15)} LPA",
            "match_percentage": random.randint(55, 95),
            "posted_days_ago": random.randint(1, 14),
            "type": random.choice(["Full-time","Contract","Hybrid"]),
            "skills_required": random.sample(info.get("required_skills", [])[:5], min(3, len(info.get("required_skills", [])))),
            "apply_url": f"https://linkedin.com/jobs/search?keywords={role.replace(' ','+')}",
        })
    jobs.sort(key=lambda x: x["match_percentage"], reverse=True)
    return {"role": role, "location": location, "jobs": jobs, "total": len(jobs)}

@app.post("/api/study-session")
async def log_study_session(body: StudySessionInput):
    entry = {**body.dict(), "timestamp": datetime.utcnow().isoformat(), "id": len(STUDY_SESSIONS)+1}
    STUDY_SESSIONS.append(entry)
    xp = int(body.duration_minutes * 1.5)
    if body.technique == "pomodoro": xp = int(xp * 1.3)
    if body.user_id not in USER_PROGRESS:
        USER_PROGRESS[body.user_id] = {"xp": 0, "level": 1, "badges": [], "streak": 0, "skills_learned": [], "total_hours": 0}
    USER_PROGRESS[body.user_id]["xp"] += xp
    return {"status": "logged", "session_id": entry["id"], "xp_earned": xp, "duration_minutes": body.duration_minutes}

@app.get("/api/leaderboard/{department}")
async def leaderboard(department: str):
    data = LEADERBOARD_DATA.get(department, LEADERBOARD_DATA["default"])
    return {"department": department, "leaderboard": data, "updated_at": datetime.utcnow().isoformat()}

@app.post("/api/mentor-request")
async def mentor_request(body: MentorRequestInput):
    mentor = next((m for m in MENTORS if m["id"] == body.mentor_id), None)
    if not mentor: raise HTTPException(404, "Mentor not found")
    req = {**body.dict(), "id": len(MENTOR_REQUESTS)+1, "status": "pending", "created_at": datetime.utcnow().isoformat()}
    MENTOR_REQUESTS.append(req)
    return {"status": "submitted", "request_id": req["id"], "mentor_name": mentor["name"], "message": f"Your request to {mentor['name']} has been sent!"}

@app.get("/api/certifications/{skill}")
async def get_certifications(skill: str):
    certs = CERTIFICATIONS.get(skill, CERTIFICATIONS.get(skill.split()[0], CERTIFICATIONS["default"]))
    return {"skill": skill, "certifications": certs}

@app.post("/api/quiz/{skill}")
async def generate_quiz(skill: str, body: QuizInput):
    questions_pool = INTERVIEW_QUESTIONS.get(skill, INTERVIEW_QUESTIONS["default"])
    selected = questions_pool[:body.num_questions]
    quiz = [{"id": i+1, "question": q, "difficulty": body.difficulty, "skill": skill, "hint": f"Think about core {skill} concepts"} for i, q in enumerate(selected)]
    return {"skill": skill, "difficulty": body.difficulty, "questions": quiz, "total": len(quiz), "time_limit_minutes": len(quiz) * 3}

@app.get("/api/mentors")
async def get_mentors():
    return {"mentors": MENTORS}

@app.get("/api/departments")
async def get_departments():
    return {"departments": DEPARTMENTS}

@app.get("/api/career-roles")
async def get_career_roles():
    return {"roles": list(CAREER_ROLES.keys()), "details": CAREER_ROLES}

@app.get("/api/interview-questions/{role}")
async def interview_questions(role: str):
    role_info = CAREER_ROLES.get(role, {})
    skills = role_info.get("required_skills", [])
    questions = []
    for skill in skills[:4]:
        qs = INTERVIEW_QUESTIONS.get(skill, INTERVIEW_QUESTIONS["default"])
        questions.extend([{"question": q, "skill": skill} for q in qs[:2]])
    return {"role": role, "questions": questions[:15]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
