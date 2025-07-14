"""
Vibecode Content Factory - Claude Automation
Transforms Google Sheets transcripts into viral TikTok/YouTube content
"""

import os
import time
import json
from typing import List, Dict, Optional
import pandas as pd
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from openai import OpenAI
import logging
from functools import wraps
import random

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_with_backoff(max_retries: int = 3, backoff_factor: float = 1.5):
    """Decorator for retrying API calls with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt + random.uniform(0, 1)
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.2f}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"All {max_retries} attempts failed. Last error: {e}")
            raise last_exception
        return wrapper
    return decorator

def safe_str_convert(value):
    """Safely convert any value to string"""
    if value is None:
        return ''
    if isinstance(value, float):
        import math
        if math.isnan(value):
            return ''
        return str(value)
    return str(value)

def validate_sheet_data(data: List[Dict]) -> List[Dict]:
    """Validate and clean sheet data"""
    valid_data = []
    
    for i, row in enumerate(data):
        try:
            # Clean all values in the row first
            cleaned_row = {}
            for key, value in row.items():
                cleaned_row[key] = safe_str_convert(value)
            
            # Normalize column names - accept both 'transcript' and 'transcription'
            if 'transcript' in cleaned_row and 'transcription' not in cleaned_row:
                cleaned_row['transcription'] = cleaned_row['transcript']
            
            # Check required fields
            required_fields = ['title', 'transcription']
            missing_fields = []
            for field in required_fields:
                value = cleaned_row.get(field, '').strip()
                if not value:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning(f"Row {i+1} missing required fields: {missing_fields}")
                continue
            
            # Validate transcription length
            transcription = cleaned_row.get('transcription', '').strip()
            if len(transcription) < 50:
                logger.warning(f"Row {i+1} transcription too short ({len(transcription)} chars)")
                continue
            
            if len(transcription) > 8000:
                logger.warning(f"Row {i+1} transcription too long ({len(transcription)} chars), truncating")
                cleaned_row['transcription'] = transcription[:8000] + "..."
            
            # Validate title
            title = cleaned_row.get('title', '').strip()
            if len(title) > 200:
                logger.warning(f"Row {i+1} title too long, truncating")
                cleaned_row['title'] = title[:200] + "..."
            
            # Ensure keywords field exists
            if 'keywords' not in cleaned_row:
                cleaned_row['keywords'] = ''
            
            valid_data.append(cleaned_row)
            
        except Exception as e:
            logger.error(f"Error processing row {i+1}: {e}")
            continue
    
    logger.info(f"Validated {len(valid_data)} out of {len(data)} rows")
    return valid_data

def estimate_token_usage(data: List[Dict]) -> Dict:
    """Estimate token usage and cost for processing"""
    total_chars = 0
    total_rows = len(data)
    
    for row in data:
        # Estimate input tokens (system prompt + user content)
        title = safe_str_convert(row.get('title', ''))
        keywords = safe_str_convert(row.get('keywords', ''))
        transcription = safe_str_convert(row.get('transcription', ''))
        
        # Rough char count (system prompt is ~2000 chars)
        total_chars += len(title) + len(keywords) + len(transcription) + 2000
    
    # Rough token estimation (4 chars per token)
    estimated_input_tokens = total_chars // 4
    estimated_output_tokens = total_rows * 200  # ~200 tokens per output
    
    # Claude Sonnet pricing (approximate)
    input_cost = estimated_input_tokens * 3 / 1_000_000  # $3 per 1M input tokens
    output_cost = estimated_output_tokens * 15 / 1_000_000  # $15 per 1M output tokens
    total_cost = input_cost + output_cost
    
    return {
        'total_rows': total_rows,
        'estimated_input_tokens': estimated_input_tokens,
        'estimated_output_tokens': estimated_output_tokens,
        'estimated_cost_usd': total_cost,
        'estimated_time_minutes': total_rows * 0.5  # ~30 seconds per row
    }

class VibeCodeContentFactory:
    def __init__(self, 
                 google_credentials_path: str,
                 openrouter_api_key: str,
                 sheet_id: str,
                 worksheet_name: str = "Sheet1",
                 model: str = "anthropic/claude-3-sonnet-20240229"):
        """
        Initialize the Vibecode Content Factory
        
        Args:
            google_credentials_path: Path to Google service account JSON
            openrouter_api_key: OpenRouter API key
            sheet_id: Google Sheet ID from URL
            worksheet_name: Name of the worksheet tab
            model: OpenRouter model name (e.g., "anthropic/claude-3-sonnet-20240229")
        """
        self.sheet_id = sheet_id
        self.worksheet_name = worksheet_name
        self.model = model
        
        # Initialize Google Sheets client
        self.sheets_service = self._init_google_sheets(google_credentials_path)
        
        # Initialize OpenRouter client
        self.claude_client = OpenAI(
            api_key=openrouter_api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        # System prompt for Claude
        self.system_prompt = """You are the VIRAL CONTENT MASTERMIND for TikTok and YouTube Shorts under the Vibecode brand.

Your mission: Transform boring transcripts into SCROLL-STOPPING, dopamine-hitting content that makes builders STOP scrolling and start watching.

🎯 PSYCHOLOGICAL TRIGGERS TO USE:
* FOMO: "While you're doing X, vibecoders are doing Y"
* SOCIAL PROOF: "22M downloads", "$50K MRR", "10,000 builders can't be wrong"
* CURIOSITY GAPS: "The secret that changed everything" (then explain it)
* CONTRAST: "Everyone does X, but vibecoders do Y"
* URGENCY: "This changes everything", "Before it's too late"
* VALIDATION: "You're not crazy for thinking this"
* EXCLUSIVITY: "Only 1% of builders know this"

📦 YOUR OUTPUT MUST INCLUDE:

1. ON-SCREEN TITLE (3-second hook)
   * SHOCKING stat, claim, or contradiction from the video
   * Numbers work: "95% fail", "$22M mistake", "0 to 1M users"
   * Questions work: "Why are 90% of developers doing this wrong?"
   * Keep it visual and bold (max 8 words)
   * Examples: "This 1 line of code = $50K/month", "He quit his job for THIS?"

2. VIRAL HOOK (caption headline)
   * STOP-THE-SCROLL first line
   * Max 8 words, frontload the most interesting part
   * Use power words: "secret", "exposed", "hidden", "truth", "finally"
   * Include "vibecoder" or specific tool when natural
   * NEVER use emdashes — only regular dashes (-)
   * Examples: "The vibecoder secret that broke the internet", "This AI tool prints money"

3. CAPTION BODY (the story)
   * 3-5 sentences that build curiosity and explain the value
   * Start with a relatable problem or surprising fact
   * Include specific numbers, tools, or timeframes
   * Each sentence MUST be followed by two line breaks
   * Use builder language: "shipped", "deployed", "scaled", "launched"
   * End with transformation or possibility

4. HASHTAGS
ALWAYS end with: #vibecoding #vibecodefun #vibecoders

💡 VIBECODE BRAND VOICE:
* Speak like a successful indie hacker sharing insider knowledge
* Confident but not arrogant, excited but not salesy
* Use "vibecoding" as the philosophy/approach, not just a hashtag
* Reference specific tools, frameworks, and real metrics
* Assume audience knows basic development concepts

🔥 ADVANCED VIRAL TACTICS:
* PATTERN INTERRUPT: "Everyone thinks X, but actually..."
* SPECIFICITY: "In 47 minutes" vs "quickly"
* STORY ARCS: Problem → Discovery → Transformation → Possibility
* EMOTIONAL HOOKS: Frustration → Relief → Excitement → FOMO
* SOCIAL DYNAMICS: "While others debate, vibecoders ship"

✅ REQUIRED JSON OUTPUT:
{
    "on_screen_title": "He made $22M from a 'broken' app",
    "viral_hook": "This 'broken' app generated $22M. Here's why.",
    "caption_body": "Everyone told him the app was too buggy to ship.\\n\\nBut he launched anyway - and users loved the 'imperfect' experience.\\n\\nSometimes vibecoding means shipping before you're ready.\\n\\nPerfection is the enemy of profit.",
    "hashtags": "#vibecoding #vibecodefun #vibecoders"
}

CRITICAL: Return ONLY valid JSON. No markdown, no explanations, just pure JSON."""

    def _init_google_sheets(self, credentials_path: str):
        """Initialize Google Sheets API client"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            service = build('sheets', 'v4', credentials=credentials)
            return service.spreadsheets()
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}")
            raise

    def read_sheet_data(self) -> List[Dict]:
        """Read data from Google Sheet"""
        try:
            range_name = f"{self.worksheet_name}!A:Z"
            result = self.sheets_service.values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                logger.warning("No data found in sheet")
                return []
            
            # Convert to list of dictionaries
            headers = values[0]
            data = []
            for row in values[1:]:
                # Pad row if shorter than headers
                row_data = row + [''] * (len(headers) - len(row))
                data.append(dict(zip(headers, row_data)))
            
            logger.info(f"Read {len(data)} rows from sheet")
            return data
            
        except Exception as e:
            logger.error(f"Failed to read sheet data: {e}")
            raise

    @retry_with_backoff(max_retries=3, backoff_factor=2.0)
    def generate_viral_content(self, title: str, keywords: str, transcription: str) -> Dict:
        """Generate viral content using Claude"""
        # Safe string conversion
        title = safe_str_convert(title)
        keywords = safe_str_convert(keywords)
        transcription = safe_str_convert(transcription)
        
        # Input validation
        if not title.strip():
            raise ValueError("Title cannot be empty")
        if not transcription.strip():
            raise ValueError("Transcription cannot be empty")
        if len(transcription) < 50:
            raise ValueError("Transcription too short (minimum 50 characters)")
        
        try:
            # Create user prompt
            user_prompt = f"""
TITLE: {title.strip()}
KEYWORDS: {keywords.strip()}
TRANSCRIPTION: {transcription.strip()}

Generate viral TikTok/YouTube Shorts content based on this transcript. Return only valid JSON.
"""
            
            # Call OpenRouter API
            response = self.claude_client.chat.completions.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Parse JSON response
            content = response.choices[0].message.content.strip()
            
            # Try to extract JSON if wrapped in other text
            if content.startswith('```json'):
                content = content.split('```json')[1].split('```')[0].strip()
            elif content.startswith('```'):
                content = content.split('```')[1].split('```')[0].strip()
            
            result = json.loads(content)
            
            # Add full formatted content
            result['full_content'] = self._format_full_content(result)
            
            logger.info("Successfully generated viral content")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.error(f"Raw response: {content}")
            return self._create_error_content("JSON parsing failed")
        except Exception as e:
            logger.error(f"Failed to generate content: {e}")
            return self._create_error_content(str(e))

    def _format_full_content(self, content: Dict) -> str:
        """Format the complete content for copy/paste"""
        return f"""ON-SCREEN TITLE:
{content.get('on_screen_title', '')}

HOOK:
{content.get('viral_hook', '')}

CAPTION:
{content.get('caption_body', '')}

{content.get('hashtags', '')}"""

    def _create_error_content(self, error: str) -> Dict:
        """Create error content structure"""
        return {
            'on_screen_title': f'ERROR: {error}',
            'viral_hook': 'Generation failed',
            'caption_body': 'Please try again or check the transcript',
            'hashtags': '#vibecoding #vibecodefun #vibecoders',
            'full_content': f'ERROR: {error}'
        }

    def process_batch(self, data: List[Dict], batch_size: int = 5) -> List[Dict]:
        """Process data in batches to respect API limits"""
        processed_data = []
        total_batches = (len(data) + batch_size - 1) // batch_size
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            logger.info(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} rows)")
            
            for j, row in enumerate(batch):
                title = row.get('title', '')
                keywords = row.get('keywords', '')
                transcription = row.get('transcription', '')
                
                if not transcription.strip():
                    logger.warning(f"Empty transcription for row: {title}")
                    continue
                
                # Progress indicator
                current_item = i + j + 1
                logger.info(f"   [{current_item}/{len(data)}] Processing: {title[:50]}...")
                
                try:
                    # Generate content
                    viral_content = self.generate_viral_content(title, keywords, transcription)
                    
                    # Merge with original row data
                    updated_row = {**row, **viral_content}
                    processed_data.append(updated_row)
                    
                    # Show preview of generated content
                    logger.info(f"   ✅ Generated: {viral_content.get('viral_hook', '')[:60]}...")
                    
                except Exception as e:
                    logger.error(f"   ❌ Failed to process '{title}': {e}")
                    # Add error content to maintain structure
                    error_content = self._create_error_content(f"Processing failed: {e}")
                    updated_row = {**row, **error_content}
                    processed_data.append(updated_row)
                
                # Rate limiting - Claude has generous limits but be safe
                time.sleep(1)
            
            # Progress summary
            success_count = sum(1 for row in processed_data[-len(batch):] if not row.get('viral_hook', '').startswith('ERROR'))
            logger.info(f"   Batch {batch_num} complete: {success_count}/{len(batch)} successful")
            
            # Longer pause between batches
            if i + batch_size < len(data):
                logger.info("   Pausing between batches...")
                time.sleep(5)
        
        return processed_data

    def write_to_sheet(self, data: List[Dict]):
        """Write processed data back to Google Sheet"""
        try:
            if not data:
                logger.warning("No data to write")
                return
            
            # Get all unique headers
            all_headers = set()
            for row in data:
                all_headers.update(row.keys())
            headers = list(all_headers)
            
            # Create values array
            values = [headers]
            for row in data:
                row_values = [row.get(header, '') for header in headers]
                values.append(row_values)
            
            # Clear existing data and write new data
            range_name = f"{self.worksheet_name}!A:Z"
            
            # Clear sheet
            self.sheets_service.values().clear(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()
            
            # Write new data
            self.sheets_service.values().update(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body={'values': values}
            ).execute()
            
            logger.info(f"Successfully wrote {len(data)} rows to sheet")
            
        except Exception as e:
            logger.error(f"Failed to write to sheet: {e}")
            raise

    def run(self, batch_size: int = 5, confirm_cost: bool = True):
        """Main execution function"""
        logger.info("🚀 Starting Vibecode Content Factory...")
        
        try:
            # Read data from sheet
            data = self.read_sheet_data()
            if not data:
                logger.warning("No data to process")
                return
            
            # Filter rows that need processing (no viral content yet)
            unprocessed = [row for row in data if not row.get('viral_hook')]
            
            if not unprocessed:
                logger.info("All rows already processed!")
                return
            
            logger.info(f"Found {len(unprocessed)} rows to process")
            
            # Validate data
            validated_data = validate_sheet_data(unprocessed)
            if not validated_data:
                logger.error("No valid data to process after validation")
                return
            
            # Estimate cost and time
            cost_estimate = estimate_token_usage(validated_data)
            logger.info(f"📊 Processing Estimate:")
            logger.info(f"   • Rows: {cost_estimate['total_rows']}")
            logger.info(f"   • Estimated cost: ${cost_estimate['estimated_cost_usd']:.2f}")
            logger.info(f"   • Estimated time: {cost_estimate['estimated_time_minutes']:.1f} minutes")
            
            # Confirm with user if cost is high
            if confirm_cost and cost_estimate['estimated_cost_usd'] > 5.0:
                logger.warning(f"⚠️  High cost estimate: ${cost_estimate['estimated_cost_usd']:.2f}")
                logger.warning("Set confirm_cost=False to skip this check")
                response = input("Continue? (y/N): ").strip().lower()
                if response != 'y':
                    logger.info("Processing cancelled by user")
                    return
            
            # Process in batches
            processed_data = self.process_batch(validated_data, batch_size)
            
            # Merge with existing processed data
            processed_titles = {row.get('title', '') for row in processed_data}
            existing_processed = [row for row in data if row.get('title', '') not in processed_titles]
            
            all_data = existing_processed + processed_data
            
            # Write back to sheet
            self.write_to_sheet(all_data)
            
            logger.info("✅ Content factory completed successfully!")
            logger.info(f"Processed {len(processed_data)} new viral content pieces")
            
        except Exception as e:
            logger.error(f"Content factory failed: {e}")
            raise


def main():
    """Main execution function"""
    
    # Check for required environment variables
    required_env_vars = ['OPENROUTER_API_KEY', 'GOOGLE_SHEET_ID']
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error("❌ Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"   • {var}")
        logger.error("\nSet OPENROUTER_API_KEY and GOOGLE_SHEET_ID environment variables")
        logger.error("Get OpenRouter API key from: https://openrouter.ai/")
        return False
    
    # Auto-detect credentials file
    possible_creds = [
        'service-account.json',
        'credentials.json', 
        'google-credentials.json'
    ]
    
    creds_path = None
    for path in possible_creds:
        if os.path.exists(path):
            creds_path = path
            break
    
    if not creds_path:
        logger.error("❌ Google credentials file not found")
        logger.error("Expected one of: " + ", ".join(possible_creds))
        logger.error("Run 'python setup_vibecode.py' to set up credentials")
        return False
    
    # Configuration
    config = {
        'google_credentials_path': creds_path,
        'openrouter_api_key': os.environ.get('OPENROUTER_API_KEY'),
        'sheet_id': os.environ.get('GOOGLE_SHEET_ID'),
        'worksheet_name': os.environ.get('WORKSHEET_NAME', 'Sheet1'),
        'model': os.environ.get('OPENROUTER_MODEL', 'anthropic/claude-3-sonnet-20240229')
    }
    
    try:
        # Initialize and run
        factory = VibeCodeContentFactory(**config)
        factory.run(batch_size=3, confirm_cost=True)  # Process 3 at a time to be safe
        return True
        
    except Exception as e:
        logger.error(f"❌ Content factory failed: {e}")
        return False


if __name__ == "__main__":
    main()
