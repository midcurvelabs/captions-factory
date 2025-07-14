#!/usr/bin/env python3
"""
Vibecode Content Factory Setup Script
Helps configure credentials and test the system
"""

import os
import json
import sys
from pathlib import Path
from vibecode_automation import VibeCodeContentFactory

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'google-api-python-client',
        'google-auth',
        'anthropic',
        'pandas'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print("❌ Missing required packages:")
        for package in missing:
            print(f"   • {package}")
        print("\nInstall with: pip install " + " ".join(missing))
        return False
    
    print("✅ All required packages installed")
    return True

def setup_environment():
    """Setup environment variables"""
    print("\n🔧 Setting up environment variables...")
    
    # Check Claude API key
    claude_key = os.environ.get('CLAUDE_API_KEY')
    if not claude_key:
        claude_key = input("Enter your Claude API key: ").strip()
        if claude_key:
            print(f"export CLAUDE_API_KEY='{claude_key}'")
            print("Add this to your ~/.bashrc or ~/.zshrc")
        else:
            print("❌ Claude API key is required")
            return False
    else:
        print("✅ Claude API key found")
    
    # Check Google Sheet ID
    sheet_id = os.environ.get('GOOGLE_SHEET_ID')
    if not sheet_id:
        sheet_id = input("Enter your Google Sheet ID (from the URL): ").strip()
        if sheet_id:
            print(f"export GOOGLE_SHEET_ID='{sheet_id}'")
            print("Add this to your ~/.bashrc or ~/.zshrc")
        else:
            print("❌ Google Sheet ID is required")
            return False
    else:
        print("✅ Google Sheet ID found")
    
    return True

def setup_google_credentials():
    """Setup Google credentials"""
    print("\n🔐 Setting up Google credentials...")
    
    # Check if credentials file exists
    possible_paths = [
        'service-account.json',
        'credentials.json',
        'google-credentials.json'
    ]
    
    creds_path = None
    for path in possible_paths:
        if os.path.exists(path):
            creds_path = path
            break
    
    if not creds_path:
        print("❌ Google service account credentials not found")
        print("\nTo set up Google credentials:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing")
        print("3. Enable Google Sheets API")
        print("4. Create Service Account → Download JSON")
        print("5. Save as 'service-account.json' in this directory")
        print("6. Share your Google Sheet with the service account email")
        return False
    
    # Validate credentials file
    try:
        with open(creds_path, 'r') as f:
            creds = json.load(f)
        
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in creds]
        
        if missing_fields:
            print(f"❌ Invalid credentials file. Missing: {missing_fields}")
            return False
        
        print(f"✅ Valid Google credentials found: {creds_path}")
        print(f"   Service account: {creds['client_email']}")
        print("   Make sure to share your Google Sheet with this email!")
        
        return creds_path
        
    except Exception as e:
        print(f"❌ Error reading credentials file: {e}")
        return False

def test_connection():
    """Test the connection to Google Sheets and Claude"""
    print("\n🧪 Testing connections...")
    
    try:
        # Get configuration
        claude_key = os.environ.get('CLAUDE_API_KEY')
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        creds_path = setup_google_credentials()
        
        if not all([claude_key, sheet_id, creds_path]):
            print("❌ Missing required configuration")
            return False
        
        # Initialize factory
        factory = VibeCodeContentFactory(
            google_credentials_path=creds_path,
            claude_api_key=claude_key,
            sheet_id=sheet_id
        )
        
        # Test Google Sheets connection
        print("Testing Google Sheets connection...")
        data = factory.read_sheet_data()
        print(f"✅ Successfully read {len(data)} rows from Google Sheet")
        
        # Test Claude connection with sample data
        print("Testing Claude API connection...")
        test_content = factory.generate_viral_content(
            title="Test Title",
            keywords="test, viral, content",
            transcription="This is a test transcription for validating the Claude API connection and content generation capabilities."
        )
        print("✅ Claude API connection successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def create_sample_sheet():
    """Create sample data for testing"""
    print("\n📊 Sample Google Sheet format:")
    print("Column A: title")
    print("Column B: keywords") 
    print("Column C: transcription")
    print("\nExample data:")
    print("Row 1: Title | Keywords | Transcription")
    print("Row 2: How to Build MVPs Fast | MVP, startup, development | In this video I'll show you...")
    print("Row 3: AI Tools for Developers | AI, coding, productivity | Today we're looking at...")

def main():
    """Main setup function"""
    print("🚀 Vibecode Content Factory Setup")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Setup environment
    if not setup_environment():
        return False
    
    # Setup Google credentials
    if not setup_google_credentials():
        return False
    
    # Test connections
    if not test_connection():
        return False
    
    print("\n🎉 Setup complete! You're ready to generate viral content.")
    print("\nTo run the content factory:")
    print("python vibecode_automation.py")
    
    # Show sample sheet format
    create_sample_sheet()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)