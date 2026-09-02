# OBSERVA AI

A complete mini-project prototype for AI-powered visual observation assessment.

## Run
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Optional real AI
Set `GEMINI_API_KEY` and enable **Use Gemini Vision** in the interface. Without an API key, the project still runs using OCR and image metadata, allowing the complete challenge → evaluation → analytics → adaptation flow to be demonstrated.

## Important
The current fallback is intentionally conservative. For richer automatic object/color/spatial questions, use Gemini Vision or replace the `analyze_image()` function with a local vision model/YOLO pipeline.
