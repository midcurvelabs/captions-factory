#!/usr/bin/env python3
"""
CSV-only processor for Vibecode Content Factory
Processes CSV files without requiring Google Sheets setup
"""

import pandas as pd
import json
from typing import List, Dict
from openai import OpenAI
from vibecode_automation import validate_sheet_data, estimate_token_usage
import logging

logger = logging.getLogger(__name__)

class CSVContentFactory:
    def __init__(self, openrouter_api_key: str, model: str = "anthropic/claude-3-sonnet-20240229"):
        """Initialize with OpenRouter API key"""
        self.claude_client = OpenAI(
            api_key=openrouter_api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = model
        
        # Use the same enhanced system prompt
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

    def generate_viral_content(self, title: str, keywords: str, transcription: str) -> Dict:
        """Generate viral content using Claude"""
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
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
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

    def process_csv(self, csv_file_path: str, output_path: str = None) -> pd.DataFrame:
        """Process CSV file and return results"""
        
        # Read CSV
        df = pd.read_csv(csv_file_path)
        
        # Clean data - convert all columns to strings and handle NaN values
        for col in df.columns:
            df[col] = df[col].astype(str).fillna('')
            # Replace 'nan' string with empty string
            df[col] = df[col].replace('nan', '')
        
        # Normalize column names - accept both 'transcript' and 'transcription'
        if 'transcript' in df.columns and 'transcription' not in df.columns:
            df['transcription'] = df['transcript']
        
        # Validate required columns
        required_cols = ['title', 'transcription']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            # Try alternative column names
            if 'transcript' in df.columns:
                print("✅ Found 'transcript' column, using as 'transcription'")
            else:
                raise ValueError(f"Missing required columns: {missing_cols}. Found: {list(df.columns)}")
        
        # Add keywords column if missing
        if 'keywords' not in df.columns:
            df['keywords'] = ''
        
        # Convert to list of dicts for processing
        data = df.to_dict('records')
        
        # Validate data
        valid_data = validate_sheet_data(data)
        
        if not valid_data:
            raise ValueError("No valid data to process")
        
        # Show cost estimate
        cost_estimate = estimate_token_usage(valid_data)
        print(f"📊 Processing Estimate:")
        print(f"   • Rows: {cost_estimate['total_rows']}")
        print(f"   • Estimated cost: ${cost_estimate['estimated_cost_usd']:.2f}")
        print(f"   • Estimated time: {cost_estimate['estimated_time_minutes']:.1f} minutes")
        
        # Process each row
        processed_data = []
        
        for i, row in enumerate(valid_data):
            print(f"[{i+1}/{len(valid_data)}] Processing: {row.get('title', '')[:50]}...")
            
            try:
                viral_content = self.generate_viral_content(
                    row.get('title', ''),
                    row.get('keywords', ''),
                    row.get('transcription', '')
                )
                
                # Merge with original data
                result = {**row, **viral_content}
                processed_data.append(result)
                
                print(f"   ✅ Generated: {viral_content.get('viral_hook', '')[:60]}...")
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                error_content = self._create_error_content(str(e))
                result = {**row, **error_content}
                processed_data.append(result)
        
        # Convert back to DataFrame
        results_df = pd.DataFrame(processed_data)
        
        # Save if output path specified
        if output_path:
            results_df.to_csv(output_path, index=False)
            print(f"✅ Results saved to: {output_path}")
        
        return results_df

def main():
    """Command line interface for CSV processing"""
    import sys
    import os
    
    if len(sys.argv) < 2:
        print("Usage: python csv_processor.py input.csv [output.csv]")
        print("\nRequired columns in CSV: title, transcription")
        print("Optional columns: keywords")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.csv', '_viral.csv')
    
    # Check for OpenRouter API key
    openrouter_key = os.environ.get('OPENROUTER_API_KEY')
    if not openrouter_key:
        print("❌ OPENROUTER_API_KEY environment variable required")
        print("Get your API key from: https://openrouter.ai/")
        print("Set it with: export OPENROUTER_API_KEY='your-key'")
        return
    
    try:
        # Initialize processor
        processor = CSVContentFactory(openrouter_key)
        
        # Process file
        results = processor.process_csv(input_file, output_file)
        
        print(f"\n🎉 Processing complete!")
        print(f"Processed {len(results)} rows")
        print(f"Results saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Processing failed: {e}")

if __name__ == "__main__":
    main()