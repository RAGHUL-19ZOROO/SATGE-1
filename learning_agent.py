"""
Learning Agent Module for Flask LMS

Generates comprehensive, human-readable learning materials in GeeksforGeeks style.
Uses simple English, real-world analogies, and practical examples to explain concepts
for easy understanding by students of all levels.

Functions:
    - generate_learning_content(topic_slug): Main function to create GeeksforGeeks-style learning content
    - call_openrouter(prompt): Makes API calls to OpenRouter
    - fetch_wiki_summary(topic): Optional Wikipedia fallback content
"""

import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Use openrouter/auto to automatically select the best available model
# Alternatives that failed: minimax/minimax-m2.5 (502), mistral/mistral-7b-instruct (invalid), meta-llama/llama-2-70b
OPENROUTER_MODEL = "openrouter/auto"
DATA_FOLDER = Path(__file__).parent / "data"
MAX_CONTENT_LENGTH = 3000
MIN_CONTENT_LENGTH = 200
MAX_TOKENS = 1500


def fetch_wiki_summary(topic: str) -> str:
    """
    Fetch a summary from Wikipedia as fallback content.
    
    Args:
        topic (str): The topic to search for on Wikipedia
        
    Returns:
        str: Wikipedia summary, empty string if not found or error occurs
    """
    try:
        import wikipedia
        summary = wikipedia.summary(topic, auto_suggest=True)
        logger.info(f"Fetched Wikipedia summary for: {topic}")
        return summary
    except wikipedia.exceptions.DisambiguationError as e:
        logger.warning(f"Disambiguation error for topic '{topic}': {e}")
        return ""
    except wikipedia.exceptions.PageError:
        logger.warning(f"Wikipedia page not found for topic: {topic}")
        return ""
    except Exception as e:
        logger.error(f"Error fetching Wikipedia summary: {str(e)}")
        return ""


def call_openrouter(prompt: str) -> dict:
    """
    Call OpenRouter API with the given prompt and return structured response.
    
    Args:
        prompt (str): The prompt to send to the API
        
    Returns:
        dict: Parsed JSON response with explanation and key_points,
              or empty dict if API call fails
    """
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY not found in environment variables")
        return {}
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Learning Paradise LMS"
    }
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=30)
        
        # Log the response status for debugging
        logger.info(f"API Response Status: {response.status_code}")
        
        if not response.ok:
            error_data = response.text if response.text else "No error details"
            logger.error(f"API Error {response.status_code}: {error_data}")
            return {}
        
        result = response.json()
        
        # Check if the API returned an error response (even with 200 status)
        if "error" in result and isinstance(result["error"], dict):
            error_msg = result["error"].get("message", "Unknown error")
            error_code = result["error"].get("code", "unknown")
            logger.error(f"API returned error {error_code}: {error_msg}")
            return {}
        
        logger.debug(f"API Response JSON: {json.dumps(result)[:500]}...")  # Log first 500 chars
        
        # Extract the message content from API response
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            logger.debug(f"API Message Content: {content[:200]}...")
            
            # Try to parse JSON from response
            try:
                parsed_content = json.loads(content)
                logger.info("Successfully received and parsed response from OpenRouter API")
                return parsed_content
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse API response content as JSON: {str(e)}")
                logger.error(f"Content received: {content[:500]}")
                return {}
        else:
            logger.error(f"Unexpected API response format. Keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
            logger.error(f"Full response: {json.dumps(result)[:500]}")
            return {}
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse API response as JSON: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error in call_openrouter: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {}


def load_topic_content(topic_slug: str) -> str:
    """
    Load content from uploaded files (txt/pdf) for a topic.
    
    Args:
        topic_slug (str): The topic identifier
        
    Returns:
        str: The content from uploaded files, or empty string if not found
    """
    try:
        from utils.file_handler import get_notes
        content = get_notes(topic_slug)
        if content:
            logger.info(f"Loaded content from uploaded files for {topic_slug}")
            return content
        else:
            logger.warning(f"No uploaded content found for topic: {topic_slug}")
            return ""
            
    except Exception as e:
        logger.error(f"Error loading content for {topic_slug}: {str(e)}")
        return ""


def clean_and_limit_content(content: str) -> str:
    """
    Clean content by removing excess whitespace and limit to MAX_CONTENT_LENGTH.
    
    Args:
        content (str): Raw content text
        
    Returns:
        str: Cleaned and limited content
    """
    # Remove excess whitespace and newlines
    cleaned = " ".join(content.split())
    
    # Limit to MAX_CONTENT_LENGTH characters
    if len(cleaned) > MAX_CONTENT_LENGTH:
        cleaned = cleaned[:MAX_CONTENT_LENGTH] + "..."
    
    return cleaned


def generate_learning_content(topic_slug: str) -> dict:
    """
    Main function to generate GeeksforGeeks-style learning content for a topic.
    
    Approach:
    1. Load content from uploaded {topic_slug} files (txt/pdf)
    2. If insufficient, fetch from Wikipedia as fallback
    3. Clean and limit content to 3000 characters
    4. Send to OpenRouter API with GeeksforGeeks-style prompt
    5. Return learning content with analogies, simple explanations, and practical examples
    
    Output Style:
    - Simple, beginner-friendly language (no jargon)
    - Real-world analogies and comparisons
    - Practical examples students can relate to
    - Step-by-step explanations
    - Focus on 'why' not just 'what'
    
    Args:
        topic_slug (str): The topic identifier (e.g., "operating-system")
        
    Returns:
        dict: {
            "topic": topic_slug,
            "explanation": "Simple, clear explanation without analogy",
            "analogy": "Real-world analogy or comparison (optional)",
            "key_points": ["memorable points", ...],
            "examples": ["practical case", "step-by-step"],
            "flowchart": "Text-based flowchart for visual understanding",
            "exam_notes": "Condensed memorizable points",
            "notes": "Comprehensive study guide",
            "ai_knowledge": "Tips, tricks, and insider knowledge",
            "wiki_summary": "Real-world application, not definition",
            "success": bool,
            "error": str (if any)
        }
    """
    
    # Step 1: Load content from JSON file
    content = load_topic_content(topic_slug)
    
    # Step 2: Fetch Wikipedia if content is insufficient
    if not content or len(content) < MIN_CONTENT_LENGTH:
        logger.info(f"Content insufficient, fetching Wikipedia summary for: {topic_slug}")
        wiki_content = fetch_wiki_summary(topic_slug.replace("-", " "))
        if wiki_content:
            content = wiki_content
        else:
            logger.warning(f"No content found for topic: {topic_slug}")
            return {
                "topic": topic_slug,
                "explanation": "",
                "analogy": "",
                "key_points": [],
                "examples": [],
                "flowchart": "",
                "exam_notes": "",
                "notes": "",
                "ai_knowledge": "",
                "wiki_summary": "",
                "success": False,
                "error": "No content found in file or Wikipedia"
            }
    
    # Step 3: Clean and limit content
    content = clean_and_limit_content(content)
    
    # Step 4: Create structured prompt for OpenRouter - GeeksforGeeks style
    prompt = f"""You are an expert technical writer like GeeksforGeeks, explaining concepts in simple, beginner-friendly language.

Topic: {topic_slug.replace("-", " ").title()}

Reference Content:
{content}

Task: Create engaging, human-readable learning materials using the GeeksforGeeks approach. Use real-world analogies, practical examples, and simple language. Return ONLY JSON:

{{
"explanation": "Clear, direct explanation in 3-4 short sentences. Explain WHAT the concept is, WHY it matters, and HOW it works. Use simple, everyday language without jargon. No analogy in this field - just straightforward explanation.",
"analogy": "A helpful real-world analogy or comparison to something familiar (optional - only if it helps understanding). Examples: 'Like a...', 'Similar to...', 'Think of it as...' Compare to everyday situations (cooking, sports, shopping, driving, etc.). Keep it short and simple.",
"key_points": [
"Point 1 - important concept or fact",
"Point 2 - explain the 'why' not just 'what'",
"Point 3 - practical use case or real-world application",
"Point 4 - common mistake or misconception to avoid",
"Point 5 - quick tip or pattern to remember"
],
"examples": [
"Practical example 1: Real-world use case or scenario",
"Practical example 2: How this is used in a real project or situation",
"Example 3: Step-by-step walkthrough showing how it works"
],
"flowchart": "Create a simple text-based flowchart with simple steps and decisions. Use arrows (→, ↓, ←) and brackets [Step]. Make it beginner-friendly.",
"exam_notes": "Condensed bullet points of what to memorize. Include formulas, definitions, and important terms. Format: Term - What it means / Does.",
"notes": "Comprehensive but easy-to-follow study notes. Start with basics, build up complexity. Include step-by-step explanations with examples.",
"ai_knowledge": "Insider tips, common mistakes students make, advanced tricks, or connections to other topics that help understanding.",
"wiki_summary": "Skip Wikipedia style. Instead, give 2-3 sentences explaining what this is used for in the real world, not dictionary definition."
}}

CRITICAL INSTRUCTIONS:
1. Use simple English - avoid jargon, or explain jargon immediately
2. Explanation field: Direct, clear explanation WITHOUT analogy
3. Analogy field: Separate optional field with real-world comparisons (not required for all topics)
4. Focus on 'why' and 'how', not just definitions
5. Include practical, real-world examples students can relate to
6. Assume beginner level - explain like you're teaching a 10th grader
7. Be conversational, not formal like textbooks or Wikipedia
8. Make content memorable with mnemonics or patterns where possible"""
    
    # Step 5: Call OpenRouter API
    api_response = call_openrouter(prompt)
    
    if not api_response:
        return {
            "topic": topic_slug,
            "explanation": "",
            "analogy": "",
            "key_points": [],
            "examples": [],
            "flowchart": "",
            "exam_notes": "",
            "notes": "",
            "ai_knowledge": "",
            "wiki_summary": "",
            "success": False,
            "error": "Failed to generate content via API"
        }
    
    # Step 6: Return structured response
    return {
        "topic": topic_slug,
        "explanation": api_response.get("explanation", ""),
        "analogy": api_response.get("analogy", ""),
        "key_points": api_response.get("key_points", []),
        "examples": api_response.get("examples", []),
        "flowchart": api_response.get("flowchart", ""),
        "exam_notes": api_response.get("exam_notes", ""),
        "notes": api_response.get("notes", ""),
        "ai_knowledge": api_response.get("ai_knowledge", ""),
        "wiki_summary": api_response.get("wiki_summary", ""),
        "success": True,
        "error": None
    }


# Example usage
if __name__ == "__main__":
    # Test the module
    result = generate_learning_content("machine-learning")
    print(json.dumps(result, indent=2))
