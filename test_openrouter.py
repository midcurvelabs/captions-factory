#!/usr/bin/env python3
"""
Quick test of OpenRouter integration
"""

import os
from csv_processor import CSVContentFactory

def test_openrouter():
    """Test OpenRouter API connection"""
    
    # Check for API key
    openrouter_key = os.environ.get('OPENROUTER_API_KEY')
    if not openrouter_key:
        print("❌ Set OPENROUTER_API_KEY environment variable first")
        print("Get your key from: https://openrouter.ai/")
        return False
    
    try:
        print("🧪 Testing OpenRouter connection...")
        
        # Initialize processor
        processor = CSVContentFactory(openrouter_key, "anthropic/claude-3-haiku-20240307")  # Use faster model for testing
        
        # Test with sample data
        test_content = processor.generate_viral_content(
            title="Test: Building MVPs with AI",
            keywords="AI, MVP, development, startup",
            transcription="In this video, I'll show you how to build minimum viable products using AI tools like Claude and Cursor. Most developers waste months building features nobody wants, but with the right AI-powered approach, you can validate ideas in days and ship working prototypes in a week. The key is using AI for rapid prototyping and getting user feedback early."
        )
        
        print("✅ OpenRouter API connection successful!")
        print(f"🎬 Generated title: {test_content.get('on_screen_title', '')}")
        print(f"🔥 Generated hook: {test_content.get('viral_hook', '')}")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenRouter test failed: {e}")
        return False

if __name__ == "__main__":
    test_openrouter()