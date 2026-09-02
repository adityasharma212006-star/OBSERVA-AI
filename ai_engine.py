import os, json, re, sqlite3, time
from collections import defaultdict
from pathlib import Path
import pandas as pd
from PIL import Image
import pytesseract

DB="data/observa.db"
Path("data").mkdir(exist_ok=True)

def normalize(x):
    return re.sub(r"[^a-z0-9 ]","",str(x).lower()).strip()

def init_db():
    con=sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS rounds (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, difficulty TEXT,
        score REAL, accuracy REAL, correct INTEGER, total INTEGER, response_time REAL,
        category_scores TEXT, insight TEXT)""")
    con.commit(); con.close()

init_db()

def analyze_image(image_path, use_gemini=False):
    # Optional real multimodal AI path.
    if use_gemini and os.getenv("GEMINI_API_KEY"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model=genai.GenerativeModel("gemini-2.5-flash")
            img=Image.open(image_path)
            prompt="""Analyse this image for an observation-memory test.
Return ONLY valid JSON with:
objects: [{name, color, count}],
text: [visible text],
relationships: [short facts like 'cat is left of table'].
Be conservative and do not invent details."""
            response=model.generate_content([prompt,img])
            return json.loads(response.text.strip().replace("```json","").replace("```",""))
        except Exception:
            pass
    # Fully offline baseline: OCR + metadata. Reliable questions are built from OCR.
    img=Image.open(image_path).convert("RGB")
    w,h=img.size
    text=pytesseract.image_to_string(img).strip()
    return {"objects":[], "text":[x.strip() for x in text.splitlines() if x.strip()],
            "relationships":[], "image_size":{"width":w,"height":h}}

def generate_questions(analysis, difficulty):
    qs=[]
    # Text questions
    for t in analysis.get("text",[])[:4]:
        qs.append({"category":"Text Recognition","question":f"What exact text did you notice: '{t}'?","answer":t,"difficulty":difficulty})
    # Vision-model questions
    for obj in analysis.get("objects",[]):
        name=obj.get("name","object"); count=obj.get("count")
        color=obj.get("color")
        if count not in [None,"unknown"]:
            qs.append({"category":"Counting","question":f"How many {name}s were visible?","answer":str(count),"difficulty":difficulty})
        if color and color!="unknown":
            qs.append({"category":"Color Recognition","question":f"What color was the {name}?","answer":str(color),"difficulty":difficulty})
        qs.append({"category":"Object Recognition","question":f"Was a {name} visible in the image?","answer":"yes","difficulty":difficulty})
    for rel in analysis.get("relationships",[])[:3]:
        qs.append({"category":"Spatial Awareness","question":f"Recall this visual relationship: {rel} (true/false)","answer":"true","difficulty":difficulty})
    # Fallback so the module always demonstrates the complete flow
    if len(qs)<3:
        w=analysis.get("image_size",{}).get("width")
        h=analysis.get("image_size",{}).get("height")
        if w and h:
            qs += [
                {"category":"Visual Detail","question":"Was the image wider than it was tall? (yes/no)","answer":"yes" if w>h else "no","difficulty":difficulty},
                {"category":"Visual Detail","question":"Was the image taller than it was wide? (yes/no)","answer":"yes" if h>w else "no","difficulty":difficulty},
            ]
    return qs[: {"Easy":3,"Medium":5,"Hard":7}[difficulty]]

def evaluate_answers(questions, answers, response_time):
    details=[]; categories=defaultdict(lambda:[0,0])
    for i,q in enumerate(questions):
        expected=normalize(q["answer"]); actual=normalize(answers.get(str(i),""))
        correct=actual==expected or (expected in actual and len(expected)>2)
        categories[q["category"]][1]+=1
        categories[q["category"]][0]+=int(correct)
        details.append({"question":q["question"],"expected":q["answer"],"actual":answers.get(str(i),""),"correct":correct})
    total=len(questions); correct=sum(d["correct"] for d in details)
    category_scores={k:round(v[0]/v[1]*100,1) for k,v in categories.items()}
    accuracy=round(correct/total*100,1) if total else 0
    weak=min(category_scores,key=category_scores.get) if category_scores else "overall observation"
    insight=f"Your strongest available skill data is being tracked. Focus on {weak}: it had the lowest accuracy in this round."
    return {"score":accuracy,"accuracy":accuracy,"correct":correct,"total":total,
            "response_time":round(response_time,1),"category_scores":category_scores,
            "details":details,"insight":insight}

def adapt_difficulty(result,current):
    order=["Easy","Medium","Hard"]; i=order.index(current)
    if result["accuracy"]>=80 and i<2: return order[i+1]
    if result["accuracy"]<50 and i>0: return order[i-1]
    return current

def save_round(r):
    con=sqlite3.connect(DB)
    con.execute("""INSERT INTO rounds(created_at,difficulty,score,accuracy,correct,total,response_time,category_scores,insight)
    VALUES(datetime('now'),?,?,?,?,?,?,?,?)""",
    (r["difficulty"],r["score"],r["accuracy"],r["correct"],r["total"],r["response_time"],json.dumps(r["category_scores"]),r["insight"]))
    con.commit(); con.close()

def get_history():
    con=sqlite3.connect(DB); df=pd.read_sql_query("SELECT * FROM rounds",con); con.close(); return df
