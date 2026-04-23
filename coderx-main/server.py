from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

# Load the hidden keys from your .env file
load_dotenv()

app = Flask(__name__)
CORS(app) 

# Using the latest fast model
TARGET_MODEL = 'gemini-2.5-flash'

# --- API KEY ROTATION SETUP ---
API_KEYS = [
    os.getenv("gemini_key_1"),
    os.getenv("gemini_key_2"),
    os.getenv("gemini_key_3"),
    os.getenv("gemini_key_4"),
    os.getenv("gemini_key_5"),
    os.getenv("gemini_key_6")
    
]

# Safety net: Remove any empty keys if you didn't set all 5 in the .env file
API_KEYS = [key for key in API_KEYS if key is not None]

# Global tracker for which key we are currently using
CURRENT_KEY_INDEX = 0

# --- 1. PROMPT FOR THE CHAT BUBBLE ---
CHAT_PROMPT = """
You are a dedicated coding engine.
RULES:
1. Write COMPLETE code.
2. For Java: You MUST use 'public class Main'.
3. For Java: You MUST include 'public static void main(String[] args)'.
4. Output Markdown blocks (```java).
5. No conversational filler.
"""

# --- 2. PROMPT FOR THE ANIMATION TRACE ---
TRACE_PROMPT = """
You are the execution trace engine for 'CodeViz' — a tool that eliminates the black-box effect of compilers by visualizing EVERY state change inside a program.

Your job: Simulate the program's execution step-by-step and return a valid JSON array.

STRICT RULES:
1. UNIVERSAL COVERAGE: Handle ALL program types — loops, recursion, conditionals, function/method calls, object creation, array/list mutations, string operations, exception handling, class instantiation, and more.
2. MEMORY STATE: In 'memory_state', track ALL variables currently in scope — primitives, arrays, objects, return values. Show their values AS THEY CHANGE each step.
3. CALL STACK: For function/method calls, add a 'call_stack' field (array of strings) showing the active call chain, e.g. ["main", "factorial(3)", "factorial(2)"].
4. ACCURACY: Your trace MUST be consistent with the program output and inputs provided. Never invent values. Read the actual inputs given and trace with those exact values.
5. SCOPE CLEANUP: Remove variables from 'memory_state' when they go out of scope (e.g., after a function returns).
6. NO COMPRESSION EVER: You MUST trace every single iteration, every single step, for the entire program. No matter how many iterations — 5, 10, 50 — trace ALL of them completely. NEVER skip, summarize, or compress any part of the execution. Every loop body, every function call, every assignment must appear as its own step.
7. NO INVISIBLE STEPS: Do NOT show the final invisible post-increment of a loop variable after the loop exits.
8. GRANULARITY: Every line that changes state (assignment, comparison, function call, return, print, input read) must be its own step.
9. INPUT HANDLING: If inputs are provided in the EXECUTION CONTEXT, use those exact values when tracing. Each input read (scanner.nextInt, input(), scanf, cin) must show the actual value received in that step's memory_state.
10. OUTPUT JSON ONLY. No explanation, no markdown, no preamble.

Schema (each element):
{
  "step": <number>,
  "action": "highlight" | "call" | "return" | "error",
  "line": <line number in the user's code>,
  "code_text": "<the actual line of code>",
  "explanation": "<student-friendly explanation of what is happening and WHY>",
  "memory_state": { "<var_name>": <current_value>, ... },
  "call_stack": ["main", "..."]
}
"""

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    def generate():
        global CURRENT_KEY_INDEX
        
        for _ in range(len(API_KEYS)):
            try:
                genai.configure(api_key=API_KEYS[CURRENT_KEY_INDEX])
                model = genai.GenerativeModel(TARGET_MODEL)
                
                full_prompt = f"System Instructions:\n{CHAT_PROMPT}\n\nUser Request:\n{user_message}"
                stream = model.generate_content(full_prompt, stream=True)
                
                for chunk in stream:
                    if chunk.text:
                        yield chunk.text
                return 
                
            except Exception as e:
                error_msg = str(e).lower()
                if "429" in error_msg or "exhausted" in error_msg or "quota" in error_msg:
                    print(f"⚠️ Key {CURRENT_KEY_INDEX + 1} exhausted. Switching to next key...")
                    CURRENT_KEY_INDEX = (CURRENT_KEY_INDEX + 1) % len(API_KEYS)
                    continue 
                else:
                    yield f"\n[System Error]: {str(e)}"
                    return
        
        yield "\n[System Error]: All API keys have reached their free tier limits!"

    return Response(generate(), mimetype='text/plain')


@app.route('/generate_trace', methods=['POST'])
def generate_trace():
    global CURRENT_KEY_INDEX
    
    data = request.json
    user_code = data.get('code', '')
    user_inputs = data.get('inputs', '') 
    program_output = data.get('output', '')
    
    prompt_message = f"System Instructions:\n{TRACE_PROMPT}\n\nGenerate trace for the following code:\n{user_code}"
    if user_inputs or program_output:
        prompt_message += "\n\n--- EXECUTION CONTEXT ---"
        if user_inputs: prompt_message += f"\nINPUTS: {user_inputs}"
        if program_output: prompt_message += f"\nRESULT: {program_output}"

    for _ in range(len(API_KEYS)):
        try:
            genai.configure(api_key=API_KEYS[CURRENT_KEY_INDEX])
            
            # FIXED: We now force Gemini to return strict JSON formatting
            model = genai.GenerativeModel(
                model_name=TARGET_MODEL,
                generation_config={"response_mime_type": "application/json"}
            )
            
            response = model.generate_content(prompt_message)
            raw_output = response.text
            
            try:
                # Load the guaranteed JSON string
                return jsonify(json.loads(raw_output)), 200
            except json.JSONDecodeError:
                return jsonify([{"step": 1, "line": 1, "explanation": "Logic trace failed to format.", "memory_state": {}}]), 200

        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "exhausted" in error_msg or "quota" in error_msg:
                print(f"⚠️ Key {CURRENT_KEY_INDEX + 1} exhausted for trace. Switching to next key...")
                CURRENT_KEY_INDEX = (CURRENT_KEY_INDEX + 1) % len(API_KEYS)
                continue 
            else:
                # Print exact error to the terminal so we can see what went wrong
                print(f"❌ Backend Trace Error: {str(e)}") 
                return jsonify({"error": str(e)}), 500

    return jsonify({"error": "All API keys have reached their free tier limits!"}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    print(f"⚡ Light Agent running with {TARGET_MODEL} on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)