# AI LinkedIn & Blog Content Generator (with Translation)

This Python Flask web application automates the generation of LinkedIn posts and corresponding blog articles using AI (via OpenRouter) based on selected topics. It also features a one-click translation of the generated English content into French.

## Features

*   **Topic Selection:** Choose from a predefined list of topics (e.g., Cybersecurity, AI, Networking, Cloud).
*   **Idea Generation:** For a selected topic, the AI generates 5 distinct LinkedIn post ideas, each with a title, summary, and a suggested URL slug.
*   **Content Generation:**
    *   Select one of the 5 ideas.
    *   The AI generates a full LinkedIn post in English based on the chosen idea.
    *   The AI generates a corresponding detailed blog article (~1000 words) in English Markdown format.
    *   The LinkedIn post automatically includes a link to the generated blog article (using the suggested slug and a configurable domain).
*   **Translation:**
    *   One-click button to translate the generated English LinkedIn post, blog article, and blog link tag into French using an AI model.
    *   Displays both English and French versions side-by-side.
*   **User Interface:** Simple web interface built with Flask and HTML/CSS.
*   **Easy Copying:** Buttons to easily copy the generated LinkedIn posts and blog article Markdown.
*   **Markdown Preview:** Basic client-side rendering of the Markdown blog articles for preview.
*   **Configurable:** API keys, AI models, and blog domain are configured via an environment file.
*   **Server-Side Sessions:** Uses Flask-Session to handle potentially large content in sessions, avoiding browser cookie size limits.

## How it Works

1.  **Setup:**
    *   The application uses Python with the Flask web framework.
    *   API calls to AI models are made through [OpenRouter](https://openrouter.ai/), allowing flexibility in choosing different LLMs.
    *   Configuration (API keys, model choices, blog domain) is managed via a `.env` file.

2.  **Workflow:**
    *   **Homepage (`/`):** The user selects a general topic from a dropdown list.
    *   **Generate Ideas (`/generate_ideas`):**
        *   The selected topic is sent to the backend.
        *   An API call is made to an AI model (e.g., DeepSeek via OpenRouter) with a prompt to generate 5 LinkedIn post *ideas* (each with a title, summary, and URL slug) for that topic. The AI is instructed to return this as a JSON list.
        *   The response is parsed, and the 5 ideas are displayed to the user.
    *   **Generate Content (`/generate_content`):**
        *   The user chooses one of the 5 ideas.
        *   The details of the chosen idea and its pre-generated slug are sent to the backend.
        *   A second API call is made to an AI model. This prompt asks the AI to:
            1.  Write a LinkedIn post in English based on the chosen idea, ensuring it includes a link to `https://YOUR_BLOG_DOMAIN/the-generated-slug`.
            2.  Write an approximately 1000-word blog article in English Markdown, elaborating on the chosen idea.
            The AI is instructed to return both in a single JSON object.
        *   The response is parsed. The generated English content (LinkedIn post, blog article, and link details) is stored in a server-side session and displayed to the user.
    *   **Translate Content (`/translate_content`):**
        *   If the user clicks the "Translate to French" button, the English content stored in the session is retrieved.
        *   An API call is made to a specified translation-capable AI model (via OpenRouter). The prompt instructs the AI to:
            1.  Translate the English LinkedIn post to French.
            2.  Translate the English blog article (Markdown) to French, preserving Markdown formatting.
            3.  Translate the English blog link tag/slug to a suitable French slug.
            The AI is instructed to return these three pieces of translated content in a single JSON object.
        *   The response is parsed. The French LinkedIn post is updated to link to the French blog URL (using the translated slug).
        *   The translated content is stored in the session and displayed alongside the English version.

3.  **Technical Details:**
    *   **Flask:** Handles routing, request processing, and template rendering.
    *   **OpenRouter API:** Used for interacting with various Large Language Models for content generation and translation.
    *   **JSON:** AI models are prompted to return structured data in JSON format, which is then parsed by the application. Robust parsing logic is implemented to handle potential inconsistencies in AI output.
    *   **Server-Side Sessions (Flask-Session):** The generated content (which can be large) is stored in server-side sessions (filesystem-based by default) to avoid browser cookie size limitations.
    *   **HTML Templates (Jinja2):** Used to render the web pages.
    *   **Showdown.js:** A client-side JavaScript library used for basic preview rendering of Markdown content.

## Setup and Installation

### Prerequisites

*   Python 3.7+
*   `pip` (Python package installer)
*   An [OpenRouter API Key](https://openrouter.ai/keys)

### Installation Steps

1.  **Clone the Repository (or download the files):**
    ```bash
    git clone <your-repository-url>
    cd ai-linkedin-blog-generator
    ```
    (If you don't have a repo yet, just navigate to the directory where you have `app.py` and other files).

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install Flask python-dotenv requests Flask-Session
    ```

4.  **Create the Environment File (`.env`):**
    In the root directory of the project, create a file named `.env` and add the following, replacing the placeholder values with your actual credentials and preferences:

    ```env
    FLASK_SECRET_KEY="your_very_strong_and_random_secret_key_here_for_flask_sessions"
    OPENROUTER_API_KEY="sk-or-v1-your_openrouter_api_key_here"
    
    # AI Model for initial content generation (English)
    DEEPSEEK_MODEL="deepseek/deepseek-chat" 
    # You can find model IDs on OpenRouter: https://openrouter.ai/models
    # Examples: "mistralai/mistral-7b-instruct", "google/gemma-7b-it", "nousresearch/nous-hermes-2-mixtral-8x7b-dpo"

    # AI Model for translation (English to French)
    TRANSLATION_MODEL="mistralai/mistral-7b-instruct:free" 
    # Choose a model good at instruction following and translation. Free models might have limitations.
    # Examples: "mistralai/mixtral-8x7b-instruct", "anthropic/claude-3-haiku" (if available & you have credits)

    YOUR_BLOG_DOMAIN="myblogname.com" 
    # Replace with your actual blog domain (without https://)
    ```
    *   **`FLASK_SECRET_KEY`**: Make this a long, random, and unique string. It's used for securing sessions.
    *   **`OPENROUTER_API_KEY`**: Your API key from OpenRouter.
    *   **`DEEPSEEK_MODEL`**: The ID of the model you want to use for generating the initial English content.
    *   **`TRANSLATION_MODEL`**: The ID of the model for translation.
    *   **`YOUR_BLOG_DOMAIN`**: Used to construct the links in the LinkedIn posts.

5.  **Create Session Directory:**
    In the root directory of your project (same level as `app.py`), create a folder named `flask_session`:
    ```bash
    mkdir flask_session
    ```
    This folder will be used by Flask-Session to store server-side session files.

## Running the Application

1.  **Activate your virtual environment** (if you created one and it's not already active):
    ```bash
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

2.  **Run the Flask app:**
    ```bash
    python app.py
    ```

3.  **Open your web browser** and navigate to:
    [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

You should see the application's homepage where you can select a topic to begin.

## Project Structure

```
ai-linkedin-blog-generator/
├── app.py # Main Flask application logic
├── templates/
│ ├── index.html # Homepage: Select initial topic
│ ├── ideas.html # Page to show 5 generated LinkedIn post ideas
│ └── content.html # Page to show final English & French content
├── static/
│ └── style.css # Basic CSS styling
├── flask_session/ # Directory for server-side session files (auto-generated by Flask-Session)
├── .env # Environment variables (API keys, config - YOU CREATE THIS)
└── README.md # This file
```

## Troubleshooting & Notes

*   **AI Model Performance:** The quality of generated content and translations heavily depends on the chosen AI models. Experiment with different models available on OpenRouter. Free models may have stricter rate limits or lower quality output.
*   **API Costs:** Be mindful of API usage costs if you are using paid models through OpenRouter.
*   **JSON Parsing Errors:** The application includes robust JSON parsing logic to handle inconsistencies from AI responses. However, if AI models consistently output malformed JSON, you may see error messages. Check the console logs for "Full Raw AI Response..." messages to debug. Refining the prompts in `app.py` is key to improving AI output quality.
*   **Session Directory:** Ensure the `flask_session` directory is writable by the application.
*   **`FLASK_SECRET_KEY`:** Keep this key secret, especially if deploying. It should be a strong, random string.

## Future Enhancements (Ideas)

*   Allow users to input custom topics.
*   More advanced Markdown editor/preview.
*   Option to choose different target languages for translation.
*   Integration with actual blog platforms to publish articles.
*   User authentication if multiple people are to use it.
*   Option to regenerate individual pieces of content (e.g., just the LinkedIn post).
*   Use a more robust server-side session backend for production (e.g., Redis, database).