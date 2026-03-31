import os
import base64
import json
import time
from flask import Flask, request, jsonify, send_from_directory, Blueprint
from flask_cors import CORS
from google import genai
from google.genai import types
from anthropic import Anthropic
from openai import OpenAI

# ─────────────────────────────────────────────────────────────────────────────
# FLASK APP INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__, static_url_path='', static_folder='static')
CORS(app)  # Enable CORS for local development

# ─────────────────────────────────────────────
# GAME ROUTES (TEMPLATES & AUDIO)
# ─────────────────────────────────────────────

# --- SPRAWL ---
@app.route('/Sprawl/index.html')
def play_sprawl():
    return send_from_directory('templates/templates_sprawl', 'index.html')

@app.route('/Sprawl/<path:filename>')
def serve_sprawl_static(filename):
    return send_from_directory('static/static_sprawl', filename)

# --- BLACK ICHOR ---
@app.route('/Black-Ichor/index.html')
def play_ichor():
    return send_from_directory('templates/templates_ichor', 'index.html')

@app.route('/Black-Ichor/<path:filename>')
def serve_ichor_static(filename):
    return send_from_directory('static/static_ichor/', filename)

# --- WARDEN ---
@app.route('/Warden/index.html')
def play_warden():
    return send_from_directory('templates/templates_warden', 'index.html')

@app.route('/Warden/<path:filename>')
def serve_warden_static(filename):
    return send_from_directory('static/static_warden', filename)

# --- GREYWAKE ---
@app.route('/Greywake/index.html')
def play_greywake():
    return send_from_directory('templates/templates_greywake', 'index.html')

@app.route('/Greywake/<path:filename>')
def serve_greywake_static(filename):
    return send_from_directory('static/static_greywake', filename)

# ─────────────────────────────────────────────
# MODEL SELECTION
# ─────────────────────────────────────────────

# Narrator Model
# "claude-sonnet-4-6" | "gemini-3.1-pro-preview" | "gpt-5.4"
NARRATOR_MODEL = os.environ.get("NARRATOR_MODEL", "claude-sonnet-4-6")

# Image Generation Model
# Options: "imagen-4.0-generate-001" | "gpt-image-1.5"
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gpt-image-1.5")

# ─────────────────────────────────────────────
# API CLIENTS
# ─────────────────────────────────────────────

gemini_key = os.environ.get("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None

openai_key = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_key.strip()) if openai_key else None

anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
anthropic_client = Anthropic(api_key=anthropic_key) if anthropic_key else None

# ─────────────────────────────────────────────
# PROVIDER DETECTION
# ─────────────────────────────────────────────

def get_provider(model_name: str) -> str:
    """Determine the provider based on model name."""
    name = model_name.lower()
    if "claude" in name:
        return "claude"
    elif "gemini" in name or "imagen" in name:
        return "gemini"
    elif "gpt" in name:
        return "gpt"
    return None

NARRATOR_PROVIDER = get_provider(NARRATOR_MODEL)
IMAGE_PROVIDER = get_provider(IMAGE_MODEL)

# ─────────────────────────────────────────────
# HARD-CODED FAST MODELS (ARCHIVIST + IMAGE REFINER)
# ─────────────────────────────────────────────

GEMINI_ARCHIVIST_AND_REFINER = 'gemini-flash-lite-latest'
GPT_ARCHIVIST_AND_REFINER = "gpt-5.4-mini"
CLAUDE_ARCHIVIST_AND_REFINER = "claude-haiku-4-5"

# ─────────────────────────────────────────────────────────────────────────────
# AI HANDLERS - NARRATION
# ─────────────────────────────────────────────────────────────────────────────

def handle_sonnet(system_prompt, context, player_action):
    if not anthropic_client:
        raise ValueError("ANTHROPIC_API_KEY not configured for Claude")

    # System instruction parts: main game rules + current context
    system_parts = [
        {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": context}
    ]

    # Latest user input
    user_message = {"role": "user", "content": player_action}

    # Call Claude
    response = anthropic_client.messages.create(
        model=NARRATOR_MODEL,
        max_tokens=8192,
        temperature=0.7,
        system=system_parts,
        messages=[user_message]
    )

    return response.content[0].text

def handle_gemini(system_prompt, context, player_action):
    
    # 1. Create the Cache
    cache = gemini_client.caches.create(
        model=NARRATOR_MODEL,
        config=types.CreateCachedContentConfig(
            display_name="neon_bazaar_logic",
            system_instruction=system_prompt,
            ttl="300s",
        )
    )
    
    # 2. Optimized Generation Config
    config = types.GenerateContentConfig(
        cached_content=cache.name,
        thinking_config=types.ThinkingConfig(thinking_level="low"),
        temperature=1.0, 
        max_output_tokens=8000, 
    )
    
    # 3. Generate
    response = gemini_client.models.generate_content(
        model=NARRATOR_MODEL,
        contents=[
            types.Part.from_text(text=f"### CURRENT_STATE ###\n{context}"),
            types.Part.from_text(text=f"### USER_INPUT ###\n{player_action}")
        ],
        config=config
    )
    
    return response.text


def handle_gpt(system_prompt, context, player_action):
    """GPT narration with separate context and player input messages"""
    if not openai_client:
        raise ValueError("OpenAI API key not configured")

    gpt_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"### CURRENT_STATE ###\n{context}"},
        {"role": "user", "content": f"### USER_INPUT ###\n{player_action}"}
    ]

    response = openai_client.chat.completions.create(
        model=NARRATOR_MODEL,
        messages=gpt_messages,
        temperature=1.0,
        max_completion_tokens=8000
    )

    return response.choices[0].message.content


# ─────────────────────────────────────────────────────────────────────────────
# AI HANDLERS - ARCHIVING (SUMMARIZATION)
# ─────────────────────────────────────────────────────────────────────────────

def handle_archive(log_segment, narrator_provider, archivist_prompt):
    """
    Archive/summarize conversation logs using hard models.
    """
    if narrator_provider == "gpt":
        model = GPT_ARCHIVIST_AND_REFINER
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": f"Summarize:\n{log_segment}"}],
            temperature=0.3,
            max_tokens=8000
        )
        return response.choices[0].message.content

    elif narrator_provider == "claude":
        model = CLAUDE_ARCHIVIST_AND_REFINER
        response = anthropic_client.messages.create(
            model=model,
            system="Summarize the following conversation accurately.",
            messages=[{"role": "user", "content": log_segment}],
            max_tokens_to_sample=8000,
            temperature=0.3
        )
        return response.content[0].text

    else:  # Gemini default
        model = GEMINI_ARCHIVIST_AND_REFINER
        response = gemini_client.models.generate_content(
            model=model,
            contents=f"Log Segment to Archive:\n{log_segment}",
            config=types.GenerateContentConfig(
                system_instruction=archivist_prompt,
                temperature=0.3
            )
        )
        return response.text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# AI HANDLERS - IMAGE GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def refine_image_prompt(narrative_text, refinement_instruction, narrator_provider):
    """
    Refine narrative text into detailed image prompt using fast models.
    """
    if narrator_provider == "gpt":
        model = GPT_ARCHIVIST_AND_REFINER
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": f"{refinement_instruction}\n\n{narrative_text}"}],
            temperature=0.7,
            max_completion_tokens=2000
        )
        return response.choices[0].message.content

    elif narrator_provider == "claude":
        model = CLAUDE_ARCHIVIST_AND_REFINER
        response = anthropic_client.messages.create(
            model=model,
            system=refinement_instruction,
            messages=[{"role": "user", "content": narrative_text}],
            temperature=0.7,
            max_tokens=2000
        )
        return response.content[0].text

    else:  # Gemini
        model = GEMINI_ARCHIVIST_AND_REFINER
        response = gemini_client.models.generate_content(
            model=model,
            contents=narrative_text,
            config=types.GenerateContentConfig(
                system_instruction=refinement_instruction,
                temperature=0.7
            )
        )
        return response.text.strip()


def generate_image(visual_prompt, aspect_ratio="16:9"):
    if "imagen" in IMAGE_MODEL.lower():  # Gemini Imagen
        if not gemini_client:
            raise ValueError("GEMINI_API_KEY not configured for image generation")
        
        response = gemini_client.models.generate_images(
            model=IMAGE_MODEL,
            prompt=visual_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                output_mime_type="image/png",
                safety_filter_level="block_low_and_above",
            )
        )
        
        if response.generated_images:
            image_obj = response.generated_images[0]
            img_b64 = base64.b64encode(image_obj.image.image_bytes).decode('utf-8')
            return img_b64
        else:
            raise ValueError("Image generation blocked by safety filters")

    elif "gpt-image" in IMAGE_MODEL.lower():  # GPT Image 1.5
        if not openai_client:
            raise ValueError("OPENAI_API_KEY not configured for GPT Image generation")
        
        response = openai_client.images.generate(
            model=IMAGE_MODEL,
            prompt=visual_prompt,
            n=1,
            size="1024x1024"  # Adjust aspect_ratio mapping if needed
        )
        
        img_b64 = response.data[0].b64_json
        if img_b64:
            return img_b64
        else:
            raise ValueError("GPT Image generation returned no image")
    
    else:
        raise ValueError(f"Unsupported IMAGE_MODEL: {IMAGE_MODEL}")


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return send_from_directory('templates', 'index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        system_prompt = data.get('system_prompt', '')
        context = data.get('context', '')
        player_action = data.get('player_action', '')

        if not system_prompt:
            return jsonify({"error": "system_prompt is required"}), 400

        # Route to the correct narrator
        if NARRATOR_PROVIDER == "claude":
            # Claude Sonnet 4.6
            content = handle_sonnet(system_prompt, context, player_action)

        elif NARRATOR_PROVIDER == "gemini":
            # Gemini 3.1 Pro Preview
            content = handle_gemini(system_prompt, context, player_action)

        elif NARRATOR_PROVIDER == "gpt":
            # GPT 5.4
            content = handle_gpt(system_prompt, context, player_action)

        else:
            return jsonify({"error": f"Unsupported narrator model: {NARRATOR_MODEL}"}), 500

        return jsonify({"text": content})

    except Exception as e:
        print(f"❌ Chat Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/archive', methods=['POST'])
def archive_route():
    try:
        data = request.json
        
        log_segment = data.get('context', '')
        archivist_prompt = data.get('system_instruction', '')
        
        summary = handle_archive(log_segment, archivist_prompt)
        
        return jsonify({"text": summary})
    
    except Exception as e:
        print(f"❌ Archive Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/painter', methods=['POST'])
def painter():
    try:
        data = request.json
        narrative_text = data.get('prompt', '')
        refinement_instruction = data.get('refinement_instruction', '')
        aspect_ratio = data.get('aspect_ratio', '16:9')
        narrator_provider = data.get('narrator_provider', NARRATOR_PROVIDER)

        # Default refinement instruction if not provided
        if not refinement_instruction:
            refinement_instruction = """
You are an expert at converting narrative text into detailed image generation prompts.

Analyze the narrative and create a vivid, cinematic image prompt that captures:
- The key visual elements and composition
- The atmosphere and lighting
- Character positioning and actions
- Environmental details
- The emotional tone

Output ONLY the image prompt as a single detailed paragraph. Be specific about:
- Camera angle and framing
- Lighting conditions
- Color palette
- Textures and materials
- Style (photorealistic, illustrated, etc.)
"""

        # Step 1: Refine narrative into image prompt using fast model
        print(f"🎨 Refining narrative for {narrator_provider}...")
        visual_prompt = refine_image_prompt(
            narrative_text,
            refinement_instruction,
            narrator_provider=narrator_provider
        )
        print(f"✨ Refined prompt: {visual_prompt}")

        # Step 2: Generate image using Gemini Imagen or GPT Image
        print(f"🖼️ Generating image using {IMAGE_MODEL}...")
        img_b64 = generate_image(visual_prompt, aspect_ratio)

        return jsonify({
            "success": True,
            "image_base64": img_b64,
            "refined_prompt": visual_prompt
        })

    except Exception as e:
        print(f"❌ Painter Error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """Return current configuration"""
    return jsonify({
        "narrator_model": NARRATOR_MODEL,
        "narrator_provider": NARRATOR_PROVIDER,
        "image_model": IMAGE_MODEL,
        "image_provider": IMAGE_PROVIDER,
        "archivist_model": ARCHIVIST_MODEL
    })


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🎮 UNIFIED GAME BACKEND")
    print("="*80)
    print(f"📖 Narrator: {NARRATOR_MODEL} ({NARRATOR_PROVIDER})")
    print(f"🎨 Image Model: {IMAGE_MODEL} ({IMAGE_PROVIDER})")
    print("="*80 + "\n")
    
    # Verify at least one API key is configured
    if not (gemini_client or openai_client or anthropic_client):
        print("⚠️  WARNING: No API keys configured!")
        print("Set environment variables: GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY")
    
    app.run(debug=True, port=5000)
