import os
import cv2
import numpy as np
from PIL import Image

# Try importing pytesseract safely (won't crash if Tesseract is missing)
try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

# Try importing Google Gemini (optional)
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


def get_dominant_color_name(img_bgr):
    """Identifies the prominent color in plain English."""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    mean_s = np.mean(s)
    mean_v = np.mean(v)
    
    if mean_v < 40:
        return "black"
    if mean_s < 30 and mean_v > 200:
        return "white"
    if mean_s < 35:
        return "gray"
        
    mean_h = np.mean(h)
    if mean_h < 10 or mean_h > 170:
        return "red"
    elif mean_h < 25:
        return "orange"
    elif mean_h < 35:
        return "yellow"
    elif mean_h < 85:
        return "green"
    elif mean_h < 130:
        return "blue"
    elif mean_h < 160:
        return "purple"
    return "colored"


def extract_features(image_path):
    """Extracts rich visual features using OpenCV and PIL."""
    features = {
        "width": 0, "height": 0, "aspect_ratio": "landscape",
        "brightness": "moderate", "dominant_color": "neutral",
        "brightest_quadrant": "center", "object_count": 0,
        "text": "", "has_text": False
    }

    # 1. Dimensions
    try:
        with Image.open(image_path) as pil_img:
            w, h = pil_img.size
            features["width"] = w
            features["height"] = h
            features["aspect_ratio"] = "landscape" if w > h else ("portrait" if h > w else "square")
    except Exception:
        pass

    # 2. OpenCV Vision Extraction
    img = cv2.imread(image_path)
    if img is not None:
        # Dominant color
        features["dominant_color"] = get_dominant_color_name(img)

        # Brightness
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_b = np.mean(gray)
        if mean_b < 80:
            features["brightness"] = "dark"
        elif mean_b > 175:
            features["brightness"] = "bright"
        else:
            features["brightness"] = "moderate"

        # Quadrant Activity & Lighting
        gh, gw = gray.shape
        quads = {
            "top-left": np.mean(gray[:gh//2, :gw//2]),
            "top-right": np.mean(gray[:gh//2, gw//2:]),
            "bottom-left": np.mean(gray[gh//2:, :gw//2]),
            "bottom-right": np.mean(gray[gh//2:, gw//2:])
        }
        features["brightest_quadrant"] = max(quads, key=quads.get)

        # Approximate Object / Salient Region Count
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        large_contours = [c for c in contours if cv2.contourArea(c) > 400]
        features["object_count"] = min(len(large_contours), 12)

    # 3. Safe OCR Text Extraction (wrapped in try/except)
    if HAS_TESSERACT:
        try:
            extracted = pytesseract.image_to_string(Image.open(image_path)).strip()
            clean_text = " ".join(extracted.split())
            if len(clean_text) > 3:
                features["text"] = clean_text
                features["has_text"] = True
        except Exception:
            features["text"] = ""
            features["has_text"] = False

    return features


def generate_local_questions(features, difficulty="Medium"):
    """Generates varied questions according to difficulty level."""
    questions = []
    diff = difficulty.capitalize()

    dom_color = features["dominant_color"]
    brightness = features["brightness"]
    obj_count = features["object_count"]
    has_text = features["has_text"]
    aspect = features["aspect_ratio"]
    quad = features["brightest_quadrant"]

    # ================= EASY LEVEL =================
    if diff == "Easy":
        questions.append({
            "question": f"Was the overall lighting of the scene primarily bright? (yes/no)",
            "category": "Lighting & Mood",
            "answer": "yes" if brightness == "bright" else "no"
        })
        questions.append({
            "question": f"Was {dom_color} one of the noticeable dominant colors in the image? (yes/no)",
            "category": "Color Recognition",
            "answer": "yes"
        })
        questions.append({
            "question": f"Did the image contain any readable words, signs, or text? (yes/no)",
            "category": "Visual Details",
            "answer": "yes" if has_text else "no"
        })

    # ================= MEDIUM LEVEL =================
    elif diff == "Medium":
        questions.append({
            "question": f"Was the image formatted in {aspect} orientation? (yes/no)",
            "category": "Composition",
            "answer": "yes"
        })
        threshold_count = max(2, obj_count - 1)
        questions.append({
            "question": f"Did the scene contain at least {threshold_count} distinct objects or visual elements? (yes/no)",
            "category": "Visual Counting",
            "answer": "yes" if obj_count >= threshold_count else "no"
        })
        questions.append({
            "question": f"Was the {quad} quadrant noticeably brighter or more lit than the rest? (yes/no)",
            "category": "Spatial Lighting",
            "answer": "yes"
        })

    # ================= HARD LEVEL =================
    else:  # Hard
        if has_text:
            sample_word = features["text"].split()[0]
            questions.append({
                "question": f"Did the text in the image contain the word or sequence '{sample_word}'? (yes/no)",
                "category": "Exact Recall",
                "answer": "yes"
            })
        else:
            questions.append({
                "question": "Were there any clear logos, barcodes, or text captions visible? (yes/no)",
                "category": "Fine Inspection",
                "answer": "no"
            })

        questions.append({
            "question": f"In which specific quadrant was the brightest area located: {quad} or center? ({quad}/center)",
            "category": "Spatial Detail",
            "answer": quad
        })
        questions.append({
            "question": f"Was the scene lighting classified as '{brightness}' rather than completely balanced? (yes/no)",
            "category": "Cognitive Tone",
            "answer": "yes" if brightness in ["dark", "bright"] else "no"
        })
        questions.append({
            "question": f"Were more than {obj_count + 2} primary contours detected in the composition? (yes/no)",
            "category": "Structural Density",
            "answer": "no"
        })

    return questions


def analyze_image(image_path, use_gemini=False, difficulty="Medium"):
    """Main analyzer called by app.py."""
    features = extract_features(image_path)
    
    # If Gemini Vision is requested and available
    if use_gemini and HAS_GEMINI and os.getenv("GEMINI_API_KEY"):
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel("gemini-1.5-flash")
            pil_img = Image.open(image_path)
            prompt = f"""
            Analyze this image for a cognitive memory observation challenge.
            Difficulty: {difficulty}.
            Generate 3 short, specific questions testing what the viewer noticed.
            Format output strictly as:
            Q1: [question] | Category: [category] | Answer: [short answer]
            Q2: [question] | Category: [category] | Answer: [short answer]
            Q3: [question] | Category: [category] | Answer: [short answer]
            """
            resp = model.generate_content([prompt, pil_img])
            gemini_questions = []
            for line in resp.text.split("\n"):
                if "|" in line and "Q" in line:
                    parts = line.split("|")
                    q_text = parts[0].split(":", 1)[-1].strip()
                    cat = parts[1].split(":", 1)[-1].strip()
                    ans = parts[2].split(":", 1)[-1].strip()
                    gemini_questions.append({"question": q_text, "category": cat, "answer": ans})
            if gemini_questions:
                return {"questions": gemini_questions, "features": features}
        except Exception as e:
            print(f"Gemini fallback to local CV: {e}")

    # Default: Robust computer vision heuristics
    questions = generate_local_questions(features, difficulty=difficulty)
    return {"questions": questions, "features": features}
