from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
from groq import Groq
from google import genai
import fitz
from werkzeug.utils import secure_filename
import uuid
import re
import json
import os

# CONSTANTS
MAX_PROMPTS = 8
MAX_CHUNKS = 15

# Fetching API key
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

app = Flask(__name__)
MODEL_NAME = "gemini-3.5-flash" 

# --- GEMINI CLIENT ---
gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key= GEMINI_API_KEY)
        print("[INFO] Gemini client initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to create Gemini client: {e}")
else:
    print("[ERROR] GEMINI_API_KEY missing in .env file.")

# --- GROQ CLIENT ---
groq_client = None
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
FALLBACK_MODEL = "llama-3.3-70b-versatile"
if GEMINI_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("[INFO] Groq client initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to create Groq client: {e}")
else:
    print("[ERROR] GROQ_API_KEY missing in .env file. No fallback available.")


UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# --- FALLBACK AI FUNCTION CALL ---
def call_ai(prompt, force_Groq = False):
    if not force_Groq:
        try:
            response = gemini_client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )
            return response.text, False
        except Exception as e:
            error = str(e)
            print("DEBUG - error string was:", repr(error))
            print("DEBUG - groq_client is:", groq_client)
            if not any(code in error for code in ["503", "429", "quota", "unavailable"]):
                raise e
            print("[FALLBACK] Gemini unavailable, switching to Groq")
    response = groq_client.chat.completions.create(
        model=FALLBACK_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content, True
    

# ---CHUNKING TEXT FROM PDF---
def chunk_text(text, chunk_size=5000):
    chunks = []
    start = 0

    while start < len(text):
        if len(chunks) == MAX_CHUNKS:
            break   # stop creating more chunks when limit met

        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end

    return chunks


@app.route("/")
def home():
    return render_template("struct.html")

# ---EXTRACTION---
@app.route("/extraction", methods=['POST'])
def extraction():
    """1- Check availibility of file/pdf.
    2- Check if file has name.
    3- Check file format if correct or not.
    4- Save file.
    5- Open document and extract text.
    6- Return extracted text.
    7- Get chunks of text by applying chunk_text funciton.
    8- Call API
    9- Give prompt to AI and give chunks of text through for loop
    """
    try:
        if not request.files:
            return jsonify({'verification':False, 'error': 'File not available.' }), 400
        
        file = request.files["pdf"]
        if file.filename == "":
            return jsonify({'verification':False, 'error': 'File has no name.' }), 400
        
        if not file.filename.lower().endswith(".pdf"):
            return jsonify({'verification':False, 'error': 'File is not in PDF format.' }), 400
        
        # Saving file
        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        file.save(file_path)

        # Extracting text via PyMuPDF
        doc = fitz.open(file_path)
        extracted_text = "".join(page.get_text() for page in doc)
        doc.close()

        os.remove(file_path)

        # Checking for unextractable text
        if not extracted_text.strip():
            return jsonify({
                "success": False,
                "error": "No extractable text found. This PDF may be scanned."
            }), 400
        
        chunks = chunk_text(extracted_text)

        return jsonify({
            "success": True,
            "chunks": chunks,
             "meta": {
                "total_chars": len(extracted_text),
                "chunk_count": len(chunks)
            }
         }), 200

    except Exception as e:
        return jsonify({'verification':False, 'error':f"Internal server error {str(e)}"}), 500

# --NOTES MAKING---    
@app.route("/notes", methods = ['POST'])
def notes():
    try:
        # checking if request recieved
        if not request.is_json:
            return jsonify({
                "success": False,
                "error": "JSON required!"
            })
        data = request.get_json()
        chunks = data.get("chunks")

        # checking if chunks recieved
        if not chunks or not isinstance(chunks, list):
            return jsonify({
                "success": False,
                "error": "Chunk not recieved."
            }), 400
        # checking for GEMINI client intialization
        if not gemini_client:
            return jsonify({
                "success": False,
                "error": "GEMINI CLIENT NOT INITIALIZED."
            }), 400
        chunks = chunks[:MAX_CHUNKS]
        notes_out = []

        user_groq = False
        for chunk in chunks:
            prompt = (
                "Create clear, structured study notes from the text below. "
                "Only use the provided content. If something is missing, do not guess."
                "Do NOT include any introductory phrase like 'Here are the notes' — start directly with the content."
                "Any mathematical formulas, equations or symbols must be written in LaTeX notation wrapped in $ delimiters for inline math (e.g. $E = mc^2$) or $$ for display equations.\n\n"
                f"Text:\n{chunk}"
            )

            response, user_groq = call_ai(prompt, force_Groq=user_groq)
            notes_out.append(response)

        final_notes = "\n\n".join(notes_out)

        # Success response with all processed chunks
        return jsonify({
            "success": True,
            "chunk_count": len(chunks),
            "notes": final_notes
         }), 200

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
            return jsonify({
            'success': False,
            'error': "AI is busy right now. Please wait 30 seconds and try again."
        }), 429
        return jsonify({'verification':False, 'error':f"Internal server error {str(e)}"}), 500

# ---Q/A---
@app.route("/qa", methods=['POST'])
def qa():
    try:
        if not request.is_json:  # request is Flask’s representation of the incoming HTTP request (like an envelope)
            return jsonify({'verification':False, 'error': 'JSON not available.' }), 400 
        
        data = request.get_json() # fetching data from request HTTP
        if data == None:    
            return jsonify({'verification':False, 'error': 'Request failed.' }), 400
        print("Incoming data:", data)

        # validating data (keys)
        required_keys = ["user_prompt", "prompt_count", "notes"]
        for keys in required_keys:
            if keys not in data:
                return jsonify({'error': f"{keys} is required."}), 400
            
        
        #saving data
        userPrompt = data["user_prompt"]
        prompt_count = int(data.get("prompt_count", 0))
        prompt_count = min(int(prompt_count), MAX_PROMPTS)

        # mistake: prompt_count = prompt_count[:MAX_PROMPTS]
        # prompt_count is an int; cannot be sliced as a string/list

        notes = data["notes"]
        

        # Checking if prompt limit reached
        if prompt_count >= 8:
            return jsonify({
                "success": False,
                "error": "Max prompt limit reached"
            }), 400
        
        # API calling
        if not gemini_client:
            return jsonify({ 
            'success': False,
            'error': "Gemini API Key or client initialization failed."
        }), 500
        
        # Giving prompt to Gemini/Groq AI
        prompt = (
        "Answer the question of the user based off the notes. Answer in a student-friendly manner. The answer MUST STAY ONLY ACCORDING TO THE QUESTION GIVEN AND NOTHING ELSE. If the user asks questions outside the context provided, refuse. If the answer is not present in the notes, respond with: \"This question is outside the provided material.\" \n\n"
        f"Notes: {notes[:50000]}" "\n" f"Question: {userPrompt[:700]}" # Question should be moderate in length
    )
        answer_qa, _ = call_ai(prompt)
        
        # Success response
        return jsonify({
            "success": True,
            "answer": answer_qa,
            "prompt_count": prompt_count + 1
        }), 200
    except Exception as e:
         error_msg = str(e)
         if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
             return jsonify({
                 'success': False,
                 'error': "AI is busy right now. Please wait 30 seconds and try again."
             }), 429
         return jsonify({'verification':False, 'error':f"Internal server error {str(e)}"}), 500
# ---QUIZ---
@app.route("/quiz", methods=['POST'])
def quiz():
    try:
        if not request.is_json: 
            return jsonify({'verification':False, 'error': 'JSON not available.' }), 400 
        
        # fetching data from HTTP request
        data = request.get_json() 
        if data == None:    
            return jsonify({'verification':False, 'error': 'Request failed.' }), 400
        print("Incoming data:", data)
        
        # data needed, notes, level of education, and number of questions (to be given from frontend, checked/validated in backend) and then make API call to Gemini AI/Groq AI

        # validating data (keys)
        required_keys = ["notes", "level_of_edu", "ques_type", "number_of_questions"]
        for key in required_keys:
            if key not in data:
                return jsonify({'error': f"{key} is required."}), 400
        
        notes_gen = data["notes"]
        level_of_edu = data["level_of_edu"] 
        question_format = data["ques_type"]
        number_of_questions = data["number_of_questions"]

        # Validation of data
        if not isinstance(notes_gen, str) or notes_gen.strip() == "":
            return jsonify({
                "verification": False,
                "error": "Notes must'nt be a non-empty string."
            }), 400

        allowed_levels_edu = ["pre-junior", "junior", "high-school", "college", "university"]
        if level_of_edu not in allowed_levels_edu:
            return jsonify({
                "verification": False,
                "error": "Invalid education level."
            }), 400
        
        allowed_types = ["mcqs", "conceptual", "comprehensive"]
        if question_format not in allowed_types:
            return jsonify({
                "verification": False,
                "error": "Invalid question format."
            }), 400
        
        # Mapping Question Format
        QUES_FORMAT_MAP = {
            "mcqs": f"Generate {number_of_questions} multiple-choice questions. Each question must have 4 options labeled A, B, C, and D.",
            "conceptual": f"Generate {number_of_questions} deep conceptual questions. Questions must test reasoning and analytical thinking. Questions must NOT ask answers more than 3 to 4 lines. Do NOT provide answers.",
            "comprehensive": f"Generate {number_of_questions} comprehensive/long questions. Questions must test knowledge, understanding, and analytical reasoning. "
        }
        type_instruction = QUES_FORMAT_MAP[question_format]

        # API calling
        if not gemini_client:
            return jsonify({ 
            'success': False,
            'error': "Gemini API Key or client initialization failed."
        }), 500

        if question_format == "mcqs":
            json_shape = '''[{"question": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."}, "correct_answer": "A"}, ...]'''
        else:
            json_shape = '''[{"question": "...", "model_answer": "..."}, ...]'''

        # Giving prompt to Gemini/Groq AI
        prompt = (f"""You are a professional academic quiz generator. 
                  Your task is to generate a quiz strictly based on the provided notes
Rules:
1. Use ONLY notes as context.
2. Do NOT introduce outside knowledge.
3. If information required for a question is not available in the notes, then do not fabricate/make it up.
4. Questions must test:
   - Critical thinking
   - Understanding
   - Concept Clarity
   - Knowledge    
Education level: {level_of_edu}
Difficulty Guidelines based of Education level:
- pre_junior: Simple recall and basic understanding.
- junior: Mix of recall and basic reasoning.
- high_school: Concept explanation and applied reasoning.
- college: Analytical, comparative, and deeper conceptual evaluation.
- university: Critical analysis, correspondence between different topics, and real-life based critical questions.

Question Format: {type_instruction}

Return ONLY a valid JSON array. No markdown, no code fences, no explanations, no text before or after the array.
Each element must strictly follow this shape:
{json_shape}
Do not include a "correct_answer" or "model_answer" field with an empty value — always provide the real answer.
The real answer provided should be carefully reviewed and then provided- not overlooked.
Notes:
{notes_gen} """)
        
        raw, _ = call_ai(prompt)
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        raw = raw.replace("\\", "\\\\")
        print("RAW BEFORE PARSE:", raw)
        try:
            answer_quiz = json.loads(raw)
        except json.JSONDecodeError as e:
            return jsonify({
                "success": False,
                "error": "AI returned malfunctioned quiz data- try again."
            }), 502


        # Success response
        return jsonify({
            "success": True,
            "quiz": answer_quiz,
            "education_level": level_of_edu,
            "question_type": question_format,
            "question_count": number_of_questions
        }), 200

    except Exception as e:
          error_msg = str(e)
          if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
            return jsonify({
            'success': False,
            'error': "AI is busy right now. Please wait 30 seconds and try again."
        }), 429
          return jsonify({'verification':False, 'error':f"Internal server error {str(e)}"}), 500
    
#--- GRADING SYSTEM ---
@app.route("/grade", methods=['POST'])
def grade():
    try:
        if not request.is_json: 
            return jsonify({'verification':False, 'error': 'JSON not available.' }), 400 
        
        # fetching data from HTTP request
        data = request.get_json() 
        if data == None:    
            return jsonify({'verification':False, 'error': 'Request failed.' }), 400
        print("Incoming data:", data)
        
        # data needed, generated notes, question format, and answers to be given from frontend, checked/validated in backend) and then make API call to Gemini AI/Groq AI

        # validating data (keys)
        required_keys = ["notes", "question_type", "answers"]
        for key in required_keys:
            if key not in data:
                return jsonify({'error': f"{key} is required."}), 400
        
        notes_gen = data["notes"]
        user_answer = data["answers"] 
        question_format = data["question_type"]

        print("Answers recieved:",data.get("answers"))
        # Validation of data
        if not isinstance(notes_gen, str) or notes_gen.strip() == "":
            return jsonify({
                "verification": False,
                "error": "Notes must'nt be a non-empty string."
            }), 400
        
        allowed_types = ["mcqs", "conceptual", "comprehensive"]
        if question_format not in allowed_types:
            return jsonify({
                "verification": False,
                "error": "Invalid question format."
            }), 400

        # API calling
        if not gemini_client:
            return jsonify({ 
            'success': False,
            'error': "Gemini API Key or client initialization failed."
        }), 500

        # Cleaning the provided answers in JSON format
        user_answer_json = json.dumps(user_answer, indent=2)

        # Giving prompt to Gemini AI/Groq AI
        prompt = (f"""You are a professional academic quiz checker. 
                  Your task is to check a quiz strictly based on the provided notes
Rules:
1. Each object contains the question, the correct_answer (ground truth), and the user_answer. Compare user_answer directly against correct_answer. For MCQs, only exact letter match counts as correct.
2. Do NOT introduce outside knowledge.
3. Start your response with: Score: X/10 (or X%), then follow with the rest.
4. Answers must be:
   - According to notes, related or in other words analogous to notes.
   - If answers are not mcqs but rather written in words question by question- then check for misunderstandings- weak concepts and knowledge gaps.

Feedback Format:
- List out weaknesses depending on answers gotten completely wrong or partially correct.
- List out strengths depending on answers gotten completely right.
- In bullet points ONLY, list out ways to improve score if score is less than 95 percent.
- Strengths, weaknesses and advice to improve score must be precise and concise.
- If score is 95 percent or above- congratulate the user- but advise spaced repitition to maintain score.

Answers submitted by user:
{user_answer_json}

Notes:
{notes_gen} """)
        checked_and_feedback, _ = call_ai(prompt)


        # Success response
        return jsonify({
            "success": True,
            "grading": checked_and_feedback,
            "question_type": question_format,
            "answers_from_user": user_answer
        }), 200

    except Exception as e:
          error_msg = str(e)
          if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
            return jsonify({
            'success': False,
            'error': "AI is busy right now. Please wait 30 seconds and try again."
        }), 429
          return jsonify({'verification':False, 'error':f"Internal server error {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
