import os
import json
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
from flask_session import Session # Import Flask-Session

load_dotenv()

app = Flask(__name__)

# --- START Flask-Session Configuration ---
# SECRET_KEY is essential for signing the session cookie and for Flask-Session
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", os.urandom(32)) 

# Choose your session type. Filesystem is easy for local development.
app.config["SESSION_TYPE"] = "filesystem"

# Configure the directory for filesystem sessions.
SESSION_FILE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'flask_session')
if not os.path.exists(SESSION_FILE_PATH):
    try:
        os.makedirs(SESSION_FILE_PATH)
        print(f"Created session directory: {SESSION_FILE_PATH}")
    except OSError as e:
        print(f"Error creating session directory {SESSION_FILE_PATH}: {e}")
        # Depending on your needs, you might want to exit or handle this error differently
app.config["SESSION_FILE_DIR"] = SESSION_FILE_PATH

app.config["SESSION_PERMANENT"] = False # Make sessions non-permanent (browser-length) by default
app.config["SESSION_USE_SIGNER"] = True  # Encrypts the session ID cookie. Recommended.
# app.config["SESSION_COOKIE_SAMESITE"] = "Lax" 
# app.config["SESSION_COOKIE_SECURE"] = True # In production with HTTPS, set this to True

# Initialize the Flask-Session extension
# This MUST come AFTER you've set the app.config values for Flask-Session
server_session = Session(app)
# --- END Flask-Session Configuration ---


# Global variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek/deepseek-chat") 
TRANSLATION_MODEL = os.getenv("TRANSLATION_MODEL", "mistralai/mistral-7b-instruct:free")
YOUR_BLOG_DOMAIN = os.getenv("YOUR_BLOG_DOMAIN", "myblogname.com")

# --- AI Call Function ---
def call_openrouter_api(prompt_messages, model_to_use=DEEPSEEK_MODEL):
    if not OPENROUTER_API_KEY:
        print("OpenRouter API key not found.")
        return None
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": model_to_use,
                "messages": prompt_messages
            })
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Request Error with model {model_to_use}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.content.decode(errors='ignore') if e.response.content else 'No content'}")
        else:
            print("No response from API.")
        return None
    except json.JSONDecodeError as e_json: # Renamed to avoid conflict
        print(f"JSON Decode Error with model {model_to_use}: {e_json}")
        # Check if 'response' was defined in this scope (it would be if requests.post succeeded but raise_for_status failed on non-JSON error)
        # However, more likely it's defined if raise_for_status passed but response.json() failed.
        if 'response' in locals() and hasattr(response, 'text'): # Use .text for string content
            print(f"Response text that failed to parse as JSON: {response.text}")
        return None

# --- Topics Data ---
TOPICS_DATA = {
  "topics": [
    {"category": "cybersecurity", "title": "Password Security Basics", "keywords": ["passwords", "security", "authentication", "best practices"]},
    {"category": "cybersecurity", "title": "Understanding Phishing Attacks", "keywords": ["phishing", "email security", "social engineering", "prevention"]},
    {"category": "networking", "title": "VPN Explained Simply", "keywords": ["VPN", "remote work", "privacy", "security"]},
    {"category": "networking", "title": "Network Security Fundamentals", "keywords": ["firewall", "network protection", "monitoring", "basics"]},
    {"category": "AI", "title": "AI in Business: Practical Applications", "keywords": ["artificial intelligence", "business automation", "productivity", "implementation"]},
    {"category": "AI", "title": "Machine Learning for Non-Technical Teams", "keywords": ["machine learning", "data analysis", "business intelligence", "simple explanation"]},
    {"category": "cloud", "title": "Cloud Storage Security Best Practices", "keywords": ["cloud security", "data protection", "backup", "compliance"]},
    {"category": "cloud", "title": "Moving to the Cloud: What HR Needs to Know", "keywords": ["cloud migration", "HR considerations", "employee training", "change management"]}
  ]
}

# --- Routes ---
@app.route('/', methods=['GET'])
def index():
    # These pops are fine, as Flask-Session handles the actual data storage
    session.pop('last_generated_content', None)
    session.pop('translated_content', None)
    return render_template('index.html', topics=TOPICS_DATA['topics'])

@app.route('/generate_ideas', methods=['POST'])
def generate_ideas():
    selected_topic_title = request.form.get('topic_title')
    
    if not selected_topic_title:
        flash("Please select a topic.", "warning")
        return redirect(url_for('index'))

    selected_topic_detail = next((t for t in TOPICS_DATA['topics'] if t['title'] == selected_topic_title), None)
    if not selected_topic_detail:
        flash("Topic not found.", "error")
        return redirect(url_for('index'))

    session['current_topic_detail'] = selected_topic_detail
    
    prompt_messages = [
        {"role": "system", "content": "You are an AI assistant that generates creative content ideas."},
        {"role": "user", "content": f"""
        Generate 5 distinct LinkedIn post ideas based on the topic: "{selected_topic_detail['title']}".
        For each idea, provide:
        1. A catchy `title` for the potential LinkedIn post.
        2. A brief `summary` (1-2 sentences) of what the post would cover.
        3. A suggested URL `slug` (3-5 words, lowercase, hyphenated) for a blog post related to this idea.
        
        Format your response as a valid JSON list of objects. Each object must have 'title', 'summary', and 'slug' keys.
        Ensure all strings within the JSON are properly escaped, especially for newlines (use \\n), tabs (use \\t), and quotes (use \\"). Avoid any raw control characters within string values.
        
        Example:
        [
          {{"title": "Unlocking Password Power", "summary": "Discover why strong passwords are your first line of defense against online threats. We'll cover simple steps.", "slug": "unlocking-password-power"}},
          {{"title": "Password Myths Debunked", "summary": "Are long passwords always better? We bust common password security myths for you.", "slug": "password-myths-debunked"}}
        ]
        
        Your entire response should be ONLY the JSON list, with no other text, explanations, or markdown formatting (like ```json) surrounding it.
        """}
    ]

    api_response = call_openrouter_api(prompt_messages, model_to_use=DEEPSEEK_MODEL)
    
    linkedin_ideas = [] 
    error_message_for_flash = None
    raw_content_str = "" 

    if api_response and api_response.get('choices'):
        try:
            raw_content_str = api_response['choices'][0]['message']['content'].strip()
            json_payload_str = raw_content_str
            if json_payload_str.startswith("```json") and json_payload_str.endswith("```"):
                json_payload_str = json_payload_str[len("```json"):-len("```")].strip()
            elif json_payload_str.startswith("```") and json_payload_str.endswith("```"):
                json_payload_str = json_payload_str[len("```"):-len("```")].strip()
            
            if not (json_payload_str.startswith('[') and json_payload_str.endswith(']')):
                list_start_index = json_payload_str.find('[')
                list_end_index = json_payload_str.rfind(']')
                if list_start_index != -1 and list_end_index != -1 and list_end_index > list_start_index:
                    json_payload_str = json_payload_str[list_start_index : list_end_index + 1]
                else:
                    raise ValueError("Response does not appear to contain a valid JSON list structure for ideas.")

            try:
                parsed_data = json.loads(json_payload_str)
            except json.JSONDecodeError as je: # Renamed to avoid conflict
                print(f"Strict JSON parsing failed for ideas: {je}. Raw snippet being tried with strict=False: '{json_payload_str[:200]}...'")
                try:
                    parsed_data = json.loads(json_payload_str, strict=False)
                    flash("Warning: AI response for ideas contained non-standard characters. Parsed using a more lenient mode.", "warning")
                except json.JSONDecodeError as je_fallback:
                    print(f"Lenient JSON parsing (strict=False) also failed for ideas: {je_fallback}")
                    raise je_fallback

            if not isinstance(parsed_data, list):
                raise ValueError("Parsed data for ideas is not a list as expected.")
            
            valid_ideas_count = 0
            for item in parsed_data:
                if isinstance(item, dict) and 'title' in item and 'summary' in item and 'slug' in item:
                    linkedin_ideas.append(item)
                    valid_ideas_count +=1
                else:
                    print(f"Warning: Skipping an invalid item in ideas list: {item}")
            
            if not linkedin_ideas:
                 raise ValueError("No valid ideas found in the parsed AI response, or the list was empty.")
            
            print(f"Successfully parsed {valid_ideas_count} ideas.")
            session['generated_linkedin_ideas'] = linkedin_ideas

        except (json.JSONDecodeError, ValueError, KeyError) as e_parser: # Renamed to avoid conflict
            snippet = raw_content_str[:200] if raw_content_str else "N/A"
            error_message_for_flash = f"Error processing AI response for ideas: {type(e_parser).__name__} - {str(e_parser)}. Snippet: '{snippet}...'"
            print(f"Full Raw AI Response (for Ideas) causing processing error:\n{raw_content_str if raw_content_str else 'N/A'}")
            session.pop('generated_linkedin_ideas', None) 
            linkedin_ideas = [] 
    
    else: 
        error_message_for_flash = "Failed to receive a valid response from the AI for generating ideas."
        if api_response and 'error' in api_response: 
            api_err = api_response['error']
            error_message_for_flash += f" API Error ({api_err.get('type', 'Unknown')}): {api_err.get('message', 'No details')}"
        elif not api_response:
            error_message_for_flash += " No response was received from the API."
        
        session.pop('generated_linkedin_ideas', None) 
        linkedin_ideas = []

    if error_message_for_flash:
        flash(error_message_for_flash, "error")
        
    return render_template('ideas.html',
                           topic_title=selected_topic_detail.get('title', "N/A"),
                           ideas=linkedin_ideas)


@app.route('/generate_content', methods=['POST'])
def generate_content():
    selected_idea_index_str = request.form.get('selected_idea_index')
    generated_ideas = session.get('generated_linkedin_ideas')
    current_topic_detail = session.get('current_topic_detail')

    if selected_idea_index_str is None or not generated_ideas or not current_topic_detail:
        flash("Session expired or invalid request. Please start over by selecting a topic.", "warning")
        return redirect(url_for('index'))

    try:
        selected_idea_index = int(selected_idea_index_str)
        if not (0 <= selected_idea_index < len(generated_ideas)):
            raise IndexError("Selected idea index is out of bounds for the generated ideas list.")
        selected_idea = generated_ideas[selected_idea_index]
        session['current_selected_idea'] = selected_idea
    except (IndexError, ValueError) as e_index: # Renamed to avoid conflict
        flash(f"Invalid idea selected: {e_index}. Please try generating ideas again.", "error")
        return redirect(url_for('index')) 

    blog_link_tag_en = selected_idea.get('slug', 'my-default-blog-post')
    full_blog_url_en = f"https://{YOUR_BLOG_DOMAIN}/{blog_link_tag_en}"

    prompt_messages_generation = [
       {"role": "system", "content": "VERY IMPORTANT: Your entire response MUST be a single, valid JSON object and NOTHING ELSE. Do not include any commentary, notes, explanations, or any text whatsoever before or after the JSON object. Adhere strictly to JSON syntax. The JSON object must contain exactly two keys: 'linkedin_post' and 'blog_article'."},
       {"role": "user", "content": f"""
       Generate content based on the topic: "{selected_idea['title']}" (summary: "{selected_idea['summary']}").
       The blog post should link to: {full_blog_url_en} with slug: {blog_link_tag_en}.
    
       Output a single JSON object with two keys:
       1. `linkedin_post`: A concise LinkedIn post for the topic, including the link {full_blog_url_en}.
       2. `blog_article`: A detailed Markdown blog article (approx. 1000 words) for the topic. This must be the full article, not a note.
    
       JSON Example:
       {{
         "linkedin_post": "Example LinkedIn post... Read more: {full_blog_url_en}",
         "blog_article": "# Example Title\\n\\nFull Markdown article content..."
       }}
    
       Reminder: ONLY the JSON object. No extra text, no ```json wrappers, just the raw JSON starting with {{ and ending with }}.
       Ensure all string values inside the JSON are correctly escaped (newlines as \\n, quotes as \\", etc.).
       """}
    ]
    
    api_response_generation = call_openrouter_api(prompt_messages_generation, model_to_use=DEEPSEEK_MODEL)
    
    generated_content_en = {
        "linkedin_post_en": "Error: Could not generate English LinkedIn post.",
        "blog_article_en": "Error: Could not generate English blog article.",
        "blog_link_tag_en": blog_link_tag_en,
        "full_blog_url_en": full_blog_url_en,
        "idea_title": selected_idea.get('title', "N/A"),
        "topic_title": current_topic_detail.get('title', "N/A")
    }
    error_message_for_flash = None
    raw_content_str_cg = "" 

    if api_response_generation and api_response_generation.get('choices'):
        try:
            raw_content_str_cg = api_response_generation['choices'][0]['message']['content'].strip()
            json_payload_str_cg = raw_content_str_cg
            if json_payload_str_cg.startswith("```json") and json_payload_str_cg.endswith("```"):
                json_payload_str_cg = json_payload_str_cg[len("```json"):-len("```")].strip()
            elif json_payload_str_cg.startswith("```") and json_payload_str_cg.endswith("```"):
                json_payload_str_cg = json_payload_str_cg[len("```"):-len("```")].strip()

            if not (json_payload_str_cg.startswith('{') and json_payload_str_cg.endswith('}')):
                obj_start_index = json_payload_str_cg.find('{')
                obj_end_index = json_payload_str_cg.rfind('}')
                if obj_start_index != -1 and obj_end_index != -1 and obj_end_index > obj_start_index:
                    json_payload_str_cg = json_payload_str_cg[obj_start_index : obj_end_index + 1]
                else:
                    raise ValueError("Response does not appear to contain a valid JSON object structure for content generation.")

            parsed_content_cg = None
            try:
                parsed_content_cg = json.loads(json_payload_str_cg) 
            except json.JSONDecodeError as je_cg:
                print(f"Strict JSON parsing failed for content generation: {je_cg}. Raw snippet trying with strict=False: '{json_payload_str_cg[:200]}...'")
                try:
                    parsed_content_cg = json.loads(json_payload_str_cg, strict=False)
                    flash("Warning: AI response for content generation contained non-standard characters. Parsed leniently.", "warning")
                except json.JSONDecodeError as je_fallback_cg:
                    print(f"Lenient JSON parsing (strict=False) also failed for content generation: {je_fallback_cg}")
                    raise je_fallback_cg

            if not isinstance(parsed_content_cg, dict):
                raise ValueError("Parsed content for generation is not a dictionary as expected.")

            generated_content_en["linkedin_post_en"] = parsed_content_cg.get("linkedin_post", generated_content_en["linkedin_post_en"])
            generated_content_en["blog_article_en"] = parsed_content_cg.get("blog_article", generated_content_en["blog_article_en"])
            
            if len(generated_content_en["blog_article_en"]) < 200 and \
               ("note:" in generated_content_en["blog_article_en"].lower() or \
                "summary." in generated_content_en["blog_article_en"].lower() or \
                "truncated" in generated_content_en["blog_article_en"].lower()):
                print(f"Warning: Retrieved blog_article (key 'blog_article') from AI seems to be a short note/summary, not the full content. Content snippet: '{generated_content_en['blog_article_en'][:150]}...'")

            if "Error:" not in generated_content_en["linkedin_post_en"] and full_blog_url_en not in generated_content_en["linkedin_post_en"]:
                 generated_content_en["linkedin_post_en"] += f"\n\nRead more: {full_blog_url_en}"

        except (json.JSONDecodeError, ValueError, KeyError) as e_cg_parser: # Renamed
            snippet_cg = raw_content_str_cg[:200] if raw_content_str_cg else "N/A"
            error_message_for_flash = f"Error processing AI response for content generation: {type(e_cg_parser).__name__} - {str(e_cg_parser)}. Snippet: '{snippet_cg}...'"
            print(f"Full Raw AI Response (Content Generation) causing processing error:\n{raw_content_str_cg if raw_content_str_cg else 'N/A'}")
   
    else: 
        error_message_for_flash = "Failed to receive a valid response from the AI for generating content."
        if api_response_generation and 'error' in api_response_generation: 
            api_err_cg = api_response_generation['error'] # Renamed
            error_message_for_flash += f" API Error ({api_err_cg.get('type', 'Unknown')}): {api_err_cg.get('message', 'No details')}"
        elif not api_response_generation:
            error_message_for_flash += " No response was received from the API for content generation."

    if error_message_for_flash:
        flash(error_message_for_flash, "error")

    # DEBUGGING PRINT: Check what's being stored in session
    print("--- DEBUG: generated_content_en before setting session in /generate_content ---")
    try:
        # ensure_ascii=False helps if your content has non-ASCII characters that you want to see directly
        print(json.dumps(generated_content_en, indent=2, ensure_ascii=False)) 
    except TypeError as te: # Catch error if generated_content_en is not serializable (should not happen here)
        print(f"Could not serialize generated_content_en for debug printing: {te}")
        print(f"Raw generated_content_en: {generated_content_en}")
    print("--- END DEBUG /generate_content (before session set) ---")

    session['last_generated_content'] = generated_content_en
    session.pop('translated_content', None) 

    return render_template('content.html', **generated_content_en, translated_content=None)


@app.route('/translate_content', methods=['POST'])
def translate_content():
    # DEBUGGING PRINT: Check if route is hit and what session contains
    print("--- DEBUG: Entered /translate_content route ---")
    english_content_from_session = session.get('last_generated_content')
    print("--- DEBUG: english_content_from_session in /translate_content ---")
    if english_content_from_session:
        try:
            print(json.dumps(english_content_from_session, indent=2, ensure_ascii=False))
        except TypeError as te_trans: # Renamed
            print(f"Could not serialize english_content_from_session for debug printing in translate: {te_trans}")
            print(f"Raw english_content_from_session in translate: {english_content_from_session}")
    else:
        print("english_content_from_session is None or empty.")
    print("--- END DEBUG /translate_content (after session get) ---")

    if not english_content_from_session: 
        flash("No content to translate. Please generate content first (session data missing).", "warning")
        print("Redirecting to index from /translate_content because english_content_from_session is None or empty.")
        return redirect(url_for('index'))

    linkedin_post_en = english_content_from_session.get('linkedin_post_en')
    blog_article_en = english_content_from_session.get('blog_article_en')
    blog_link_tag_en = english_content_from_session.get('blog_link_tag_en')

    # Check if the retrieved English content is valid (not error placeholders)
    if not all([linkedin_post_en, blog_article_en, blog_link_tag_en]) or \
       "Error: Could not generate" in linkedin_post_en or \
       "Error: Could not generate" in blog_article_en:
        flash("Required English content fields are missing or contain errors. Please regenerate the English content.", "error")
        print("Redirecting to index from /translate_content because essential keys are missing or contain errors in english_content_from_session.")
        return redirect(url_for('index')) 
            
    prompt_messages_translation = [
        {"role": "system", "content": "You are an expert translator. Translate the provided texts from English to French. Maintain the original markdown formatting for the blog article. For the 'blog_link_tag', translate it into a suitable French slug (lowercase, hyphenated, 3-5 words). Output your response as a single JSON object with keys: 'linkedin_post_fr', 'blog_article_fr', and 'blog_link_tag_fr'."},
        {"role": "user", "content": f"""
        Please translate the following English content to French.

        LinkedIn Post (English):
        ---
        {linkedin_post_en}
        ---

        Blog Article (English - Markdown):
        ---
        {blog_article_en}
        ---

        Blog Link Tag (English Slug):
        ---
        {blog_link_tag_en}
        ---

        Return a JSON object with 'linkedin_post_fr', 'blog_article_fr', and 'blog_link_tag_fr'.
        Example JSON structure:
        {{
          "linkedin_post_fr": "Ceci est la version française...",
          "blog_article_fr": "# Titre de l'article en français\\n\\nContenu en markdown...",
          "blog_link_tag_fr": "mon-article-en-francais"
        }}
        """}
    ]

    api_response_translation = call_openrouter_api(prompt_messages_translation, model_to_use=TRANSLATION_MODEL)
    
    translated_data = {
        "linkedin_post_fr": "Error: Could not translate LinkedIn post.",
        "blog_article_fr": "Error: Could not translate blog article.",
        "blog_link_tag_fr": "erreur-slug",
        "full_blog_url_fr": f"https://{YOUR_BLOG_DOMAIN}/erreur-slug" 
    }
    error_message_for_flash = None
    raw_content_str_fr = "" 

    if api_response_translation and api_response_translation.get('choices'):
        try:
            raw_content_str_fr = api_response_translation['choices'][0]['message']['content'].strip()
            json_payload_str_fr = raw_content_str_fr
            if json_payload_str_fr.startswith("```json") and json_payload_str_fr.endswith("```"):
                json_payload_str_fr = json_payload_str_fr[len("```json"):-len("```")].strip()
            elif json_payload_str_fr.startswith("```") and json_payload_str_fr.endswith("```"):
                json_payload_str_fr = json_payload_str_fr[len("```"):-len("```")].strip()
            else: # Fallback if no markdown wrappers
                json_start_fr = json_payload_str_fr.find('{')
                json_end_fr = json_payload_str_fr.rfind('}') + 1
                if json_start_fr != -1 and json_end_fr != 0 and json_end_fr > json_start_fr:
                    json_payload_str_fr = json_payload_str_fr[json_start_fr:json_end_fr]
                else:
                    raise ValueError("Could not find valid JSON structure in AI response for translation.")

            parsed_translation = None
            try:
                parsed_translation = json.loads(json_payload_str_fr)
            except json.JSONDecodeError as je_fr:
                print(f"Strict JSON parsing failed for translation: {je_fr}. Raw snippet trying with strict=False: '{json_payload_str_fr[:200]}...'")
                try:
                    parsed_translation = json.loads(json_payload_str_fr, strict=False)
                    flash("Warning: AI response for translation contained non-standard characters. Parsed leniently.", "warning")
                except json.JSONDecodeError as je_fallback_fr:
                    print(f"Lenient JSON parsing (strict=False) also failed for translation: {je_fallback_fr}")
                    raise je_fallback_fr

            if not isinstance(parsed_translation, dict):
                raise ValueError("Parsed translation data is not a dictionary as expected.")

            translated_data["linkedin_post_fr"] = parsed_translation.get("linkedin_post_fr", translated_data["linkedin_post_fr"])
            translated_data["blog_article_fr"] = parsed_translation.get("blog_article_fr", translated_data["blog_article_fr"])
            translated_data["blog_link_tag_fr"] = parsed_translation.get("blog_link_tag_fr", translated_data["blog_link_tag_fr"])
            
            translated_data["full_blog_url_fr"] = f"https://{YOUR_BLOG_DOMAIN}/{translated_data['blog_link_tag_fr']}"
            
            if "Error:" not in translated_data["linkedin_post_fr"] and \
               translated_data["full_blog_url_fr"] not in translated_data["linkedin_post_fr"]:
                original_en_url = english_content_from_session.get('full_blog_url_en', '') 
                if original_en_url and original_en_url in translated_data["linkedin_post_fr"]:
                     translated_data["linkedin_post_fr"] = translated_data["linkedin_post_fr"].replace(original_en_url, translated_data["full_blog_url_fr"])
                elif translated_data["full_blog_url_fr"] not in translated_data["linkedin_post_fr"]: 
                     translated_data["linkedin_post_fr"] += f"\n\nLire la suite : {translated_data['full_blog_url_fr']}"

        except (json.JSONDecodeError, ValueError, KeyError) as e_fr_parser: # Renamed
            snippet_fr = raw_content_str_fr[:200] if raw_content_str_fr else "N/A"
            error_message_for_flash = f"Error processing AI response for translation: {type(e_fr_parser).__name__} - {str(e_fr_parser)}. Snippet: '{snippet_fr}...'"
            print(f"Full Raw AI Response (Translation) causing processing error:\n{raw_content_str_fr if raw_content_str_fr else 'N/A'}")
    else:
        error_message_for_flash = "Failed to get a valid response from AI for translation."
        if api_response_translation and 'error' in api_response_translation:
            api_err_tr = api_response_translation['error']
            error_message_for_flash += f" API Error ({api_err_tr.get('type', 'Unknown')}): {api_err_tr.get('message', 'No details')}"
        elif not api_response_translation:
            error_message_for_flash += " No response was received from the API for translation."

    if error_message_for_flash:
        flash(error_message_for_flash, "error")

    session['translated_content'] = translated_data
    
    # Ensure english_content_from_session is passed to the template
    final_render_data = {**english_content_from_session, "translated_content": translated_data}
    return render_template('content.html', **final_render_data)


if __name__ == '__main__':
    if not OPENROUTER_API_KEY :
        print("Warning: OPENROUTER_API_KEY is not set in .env.")
    # Check if Flask-Session config is okay
    if app.config.get("SESSION_TYPE") == "filesystem" and not os.path.isdir(app.config.get("SESSION_FILE_DIR", "")):
        print(f"Warning: SESSION_FILE_DIR '{app.config.get('SESSION_FILE_DIR')}' does not exist or is not a directory. Filesystem sessions may fail.")
    elif not app.config.get("SECRET_KEY"):
        print("Warning: SECRET_KEY is not set. Flask sessions will not be secure.")

    app.run(debug=True, port=5000)