# Lecta-AI
Extracts your PDF, generates structured notes, builds quizzes at your level, and answers questions  — grounded strictly in your document, nothing else.  Optimized for lecture notes, textbook chapters, and study guides. 
## Features
- **PDF text extraction** — upload any text-based PDF, extracts and chunks content automatically
- **AI-generated study notes** — structured, Markdown-formatted notes with full KaTeX math rendering
- **Adaptive quiz generation** — MCQs, conceptual, or comprehensive formats, across 5 education levels, with a customizable question count (max questions 25)
- **AI grading system** — submit answers, get scored feedback with strengths, weaknesses, and improvement suggestions
- **Context-locked Q&A chatbot** — answers strictly from your uploaded document, refuses out-of-scope questions
- **Gemini + Groq fallback** — automatically switches providers if the primary API is rate-limited or unavailable
- **Dark/light theme**

## Tech Stack
- **Backend:** Python, Flask, PyMuPDF (PDF parsing)
- **AI:** Google Gemini 3.5 Flash (primary), Groq/Llama 3.3 70B (fallback)
- **Frontend:** Vanilla JS, HTML, CSS (animations made via *Canva*)
- **Rendering:** marked.js (Markdown), KaTeX (math)

## Screenshots
<img width="1920" height="1810" alt="image" src="https://github.com/user-attachments/assets/b8ae24cb-5c2e-4a42-868c-673ac2df0adc" />
<img width="1920" height="1810" alt="image" src="https://github.com/user-attachments/assets/0f727ce9-00bc-4577-a01b-d3f789604458" />
<img width="1919" height="874" alt="image" src="https://github.com/user-attachments/assets/42b5ffa5-e6a1-4839-8042-6b74d1388853" />
<img width="1462" height="811" alt="image" src="https://github.com/user-attachments/assets/5ecdb521-0a22-4dee-b607-ee58211cac77" />
<img width="1410" height="861" alt="image" src="https://github.com/user-attachments/assets/868a12ad-c8ba-4c25-a1ae-1e4c338bc1b1" />
<img width="1458" height="814" alt="image" src="https://github.com/user-attachments/assets/9ef2b80a-8487-4a85-8d27-7aaf3f8d4a6b" />
<img width="1154" height="468" alt="image" src="https://github.com/user-attachments/assets/984a6507-0790-4261-9867-940ce028e918" />


## Setup

1. Clone the repo
   git clone https://github.com/Hamzacoder399/lecta-ai.git
cd lecta-ai
2. Create and activate a virtual environment
   python -m venv .venv
.venv\Scripts\activate # Windows
source .venv/bin/activate # macOS/Linux
3. Install dependencies (pip install -r requirements.txt)
4. Create a `.env` file in the project root (use `.env.example` as a reference) and add your API keys:
   GEMINI_API_KEY= YOUR_API_KEY
   GROQ_API_KEY= YOUR_API_KEY
5. Run the app.  (python reader.py)
     Then open `http://127.0.0.1:5000` in your browser

## Known Limitations
- Only text-based PDFs are supported — scanned/image-based documents are not (no OCR)
- Notes generation is capped at 15 chunks per document to manage API usage (depending on document- a 25 to 30 page document can be converted into notes at a time, smaller docs around 5 to 10 pages can be used consecutively but upto a limit).
- Requires active Gemini and/or Groq API keys to function.
- Fallback logic keeps the app running under quota pressure, but response quality may vary slightly between the two providers.

## What I Learned Building This
This project involved solving real, complex yet important engineering problems: designing a resilient two-provider AI fallback system- got hit with multiple errors- the "FALLBACK" AI idea came in creation when I saw that Gemini usually got too busy and it would be a very frustrating error as it doesn't resolve instantly. Then added , handling malformed JSON from LLM responses (including LaTeX backslash-escaping edge cases that broke JSON parsing), building a locked-in answer-key architecture so quiz grading doesn't rely on re-deriving correct answers on the fly, and integrated Markdown + KaTeX rendering pipelines for clean, readable AI output. Learned how to build a proper, functioning frontend. 
Verification and validation of data- how frontend and backend communicate, and how one can cause the other to fall.
Debugging these issues taught me to reason about *why* something failed; reading actual error traces and raw AI output, rather than guessing at fixes.

## License

MIT
