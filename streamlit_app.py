#!/usr/bin/env python3
"""
Streamlit Web Frontend for Vibecode Content Factory
Simple web interface for generating viral content
"""

import streamlit as st
import pandas as pd
import os
import json
import tempfile
from pathlib import Path
from vibecode_automation import VibeCodeContentFactory, validate_sheet_data, estimate_token_usage
from csv_processor import CSVContentFactory
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Vibecode Content Factory",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("🚀 Vibecode Content Factory")
    st.markdown("Transform your transcripts into viral TikTok/YouTube content using Claude AI")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Keys
        st.subheader("🔑 API Configuration")
        openrouter_key = st.text_input(
            "OpenRouter API Key", 
            value=os.environ.get('OPENROUTER_API_KEY', ''),
            type="password",
            help="Get your API key from https://openrouter.ai/ (often includes free credits!)"
        )
        
        # Model selection
        model_options = {
            "Claude 3 Sonnet": "anthropic/claude-3-sonnet-20240229",
            "Claude 3 Haiku (Faster)": "anthropic/claude-3-haiku-20240307", 
            "Claude 3 Opus (Best Quality)": "anthropic/claude-3-opus-20240229",
            "GPT-4 Turbo": "openai/gpt-4-turbo",
            "GPT-4o": "openai/gpt-4o"
        }
        
        selected_model = st.selectbox(
            "AI Model",
            options=list(model_options.keys()),
            index=0,
            help="Claude models work best for viral content generation"
        )
        
        model_name = model_options[selected_model]
        
        # Google Sheet Configuration
        st.subheader("📊 Google Sheet Setup")
        
        setup_method = st.radio(
            "Setup Method:",
            ["Upload CSV File", "Google Sheets API"]
        )
        
        if setup_method == "Google Sheets API":
            sheet_id = st.text_input(
                "Google Sheet ID", 
                value=os.environ.get('GOOGLE_SHEET_ID', ''),
                help="Copy from your Google Sheet URL"
            )
            
            worksheet_name = st.text_input(
                "Worksheet Name",
                value="Sheet1",
                help="Name of the tab in your Google Sheet"
            )
            
            # Credentials file upload
            creds_file = st.file_uploader(
                "Upload Google Credentials JSON",
                type=['json'],
                help="Download from Google Cloud Console"
            )
        
        # Processing options
        st.subheader("🔧 Processing Options")
        batch_size = st.slider("Batch Size", min_value=1, max_value=10, value=3)
        confirm_cost = st.checkbox("Confirm high costs", value=True)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if setup_method == "Upload CSV File":
            st.header("📁 Upload Your Data")
            
            # File upload
            uploaded_file = st.file_uploader(
                "Upload CSV file with columns: title, keywords, transcription",
                type=['csv']
            )
            
            if uploaded_file:
                try:
                    # Read CSV
                    df = pd.read_csv(uploaded_file)
                    st.success(f"✅ Loaded {len(df)} rows")
                    
                    # Show actual columns found
                    st.subheader("📋 CSV Analysis")
                    st.write(f"**Columns found:** {list(df.columns)}")
                    
                    # Normalize column names to handle variations
                    df_normalized = df.copy()
                    
                    # Clean data - convert all columns to strings and handle NaN values
                    for col in df_normalized.columns:
                        df_normalized[col] = df_normalized[col].astype(str).fillna('')
                        # Replace 'nan' string with empty string
                        df_normalized[col] = df_normalized[col].replace('nan', '')
                    
                    column_mapping = {}
                    
                    # Map common variations to standard names
                    for i, col in enumerate(df.columns):
                        col_lower = col.lower().strip()
                        
                        # Handle transcript variations
                        if col_lower in ['transcript', 'transcription', 'transcript_text', 'content']:
                            df_normalized['transcription'] = df[col]
                            column_mapping[col] = 'transcription'
                        # Handle title variations
                        elif col_lower in ['title', 'video_title', 'heading']:
                            df_normalized['title'] = df[col]
                            column_mapping[col] = 'title'
                        # Handle keywords variations
                        elif col_lower in ['keywords', 'tags', 'keyword']:
                            df_normalized['keywords'] = df[col]
                            column_mapping[col] = 'keywords'
                        # Handle likely corrupted title column (first column with single letter or short name)
                        elif i == 0 and len(col_lower) <= 2 and 'title' not in df_normalized.columns:
                            df_normalized['title'] = df[col]
                            column_mapping[col] = 'title (detected as first column)'
                    
                    # Show mapping if any
                    if column_mapping:
                        st.success("✅ Column mapping applied:")
                        for orig, mapped in column_mapping.items():
                            st.write(f"   • '{orig}' → '{mapped}'")
                    
                    # Validate required columns in normalized data
                    required_cols = ['title', 'transcription']
                    missing_cols = [col for col in required_cols if col not in df_normalized.columns]
                    
                    if missing_cols:
                        st.error(f"❌ Missing required columns: {missing_cols}")
                        st.info("**Required columns:** title, transcription (or transcript)")
                        st.info("**Optional columns:** keywords")
                        st.warning("**Please rename your columns or use one of these variations:**")
                        st.write("• **Title:** title, video_title, heading")
                        st.write("• **Transcript:** transcript, transcription, transcript_text, content")
                        st.write("• **Keywords:** keywords, tags, keyword")
                    else:
                        # Show preview
                        st.subheader("📋 Data Preview")
                        st.dataframe(df.head())
                        
                        # Process button
                        if st.button("🚀 Generate Viral Content", type="primary"):
                            process_csv_data(df_normalized, openrouter_key, model_name, batch_size)
                
                except Exception as e:
                    st.error(f"❌ Error reading CSV: {e}")
        
        else:  # Google Sheets API
            st.header("📊 Google Sheets Integration")
            
            if not all([openrouter_key, sheet_id, creds_file]):
                st.warning("⚠️ Please configure all required fields in the sidebar")
                
                # Show setup instructions
                with st.expander("📋 Setup Instructions"):
                    st.markdown("""
                    ### Required Setup:
                    1. **OpenRouter API Key**: Get from [OpenRouter.ai](https://openrouter.ai/) (often includes free credits!)
                    2. **Google Sheet ID**: Copy from your sheet URL
                    3. **Credentials JSON**: Download from [Google Cloud Console](https://console.cloud.google.com/)
                    
                    ### Google Sheet Format:
                    - Column A: `title` - Video title
                    - Column B: `keywords` - Target keywords (optional)
                    - Column C: `transcription` - Full transcript
                    """)
            else:
                # Process with Google Sheets
                if st.button("🚀 Process Google Sheet", type="primary"):
                    process_google_sheet(openrouter_key, sheet_id, worksheet_name, creds_file, batch_size, confirm_cost, model_name)
    
    with col2:
        st.header("💡 Tips")
        
        with st.expander("📝 Content Guidelines"):
            st.markdown("""
            **Good Transcriptions:**
            - At least 50 characters long
            - Clear, conversational tone
            - Include specific details/numbers
            - Mention tools or frameworks
            
            **Title Tips:**
            - Keep under 200 characters
            - Include main topic/benefit
            - Use builder-friendly language
            """)
        
        with st.expander("💰 Cost Estimation"):
            st.markdown("""
            **Approximate Costs:**
            - ~$0.05-0.08 per transcript
            - 40 transcripts = ~$2-3 total
            - Processing time: ~30s per transcript
            
            **Time Savings:**
            - Manual: 5 min per caption
            - Automated: 30 sec per caption
            - **Save 3+ hours per 40 captions**
            """)
        
        with st.expander("🎯 Output Format"):
            st.markdown("""
            **Generated Content:**
            - **On-screen title**: 3-second hook
            - **Viral hook**: Scroll-stopping headline
            - **Caption body**: 3-6 sentence explainer
            - **Hashtags**: #vibecoding #vibecodefun #vibecoders
            - **Full content**: Copy/paste ready
            """)

def process_csv_data(df, openrouter_key, model_name, batch_size):
    """Process CSV data and generate viral content"""
    
    if not openrouter_key:
        st.error("❌ OpenRouter API key required")
        return
    
    try:
        with st.spinner("🔄 Processing your content..."):
            # Ensure all data is properly cleaned
            df_clean = df.copy()
            
            # Convert all columns to strings and handle NaN/empty values
            for col in df_clean.columns:
                df_clean[col] = df_clean[col].astype(str).replace('nan', '').fillna('')
            
            # Add keywords column if missing
            if 'keywords' not in df_clean.columns:
                df_clean['keywords'] = ''
            
            # Convert DataFrame to list of dicts
            data = df_clean.to_dict('records')
            
            # Validate data
            valid_data = validate_sheet_data(data)
            
            if not valid_data:
                st.error("❌ No valid data to process")
                return
            
            # Cost estimation
            cost_estimate = estimate_token_usage(valid_data)
            
            st.info(f"""
            📊 **Processing Estimate:**
            - Rows to process: {cost_estimate['total_rows']}
            - Estimated cost: ${cost_estimate['estimated_cost_usd']:.2f}
            - Estimated time: {cost_estimate['estimated_time_minutes']:.1f} minutes
            """)
            
            # Initialize CSV processor
            processor = CSVContentFactory(openrouter_key, model_name)
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()
            
            processed_data = []
            
            # Process each row with real Claude API
            for i, row in enumerate(valid_data):
                status_text.text(f"Processing {i+1}/{len(valid_data)}: {row.get('title', '')[:50]}...")
                
                try:
                    # Generate real viral content
                    viral_content = processor.generate_viral_content(
                        row.get('title', ''),
                        row.get('keywords', ''),
                        row.get('transcription', '')
                    )
                    
                    # Merge with original data
                    result = {**row, **viral_content}
                    processed_data.append(result)
                    
                    # Update progress
                    progress_bar.progress((i + 1) / len(valid_data))
                    
                    # Show preview
                    status_text.text(f"✅ Generated: {viral_content.get('viral_hook', '')[:60]}...")
                    
                except Exception as e:
                    st.error(f"❌ Error processing row {i+1}: {e}")
                    # Add error content
                    error_content = processor._create_error_content(str(e))
                    result = {**row, **error_content}
                    processed_data.append(result)
                    progress_bar.progress((i + 1) / len(valid_data))
            
            # Show results
            status_text.text("✅ Processing complete!")
            
            with results_container:
                success_count = sum(1 for row in processed_data if not row.get('viral_hook', '').startswith('ERROR'))
                st.success(f"🎉 Generated content for {success_count}/{len(processed_data)} items!")
                
                # Convert to DataFrame for display
                results_df = pd.DataFrame(processed_data)
                
                # Show preview with tabs
                tab1, tab2, tab3 = st.tabs(["📋 Full Results", "🎯 Preview", "📊 Summary"])
                
                with tab1:
                    st.dataframe(results_df, use_container_width=True)
                
                with tab2:
                    # Show a few examples nicely formatted
                    for i, row in enumerate(processed_data[:3]):
                        if not row.get('viral_hook', '').startswith('ERROR'):
                            st.markdown(f"### Example {i+1}: {row.get('title', '')}")
                            st.markdown(f"**🎬 On-Screen Title:** {row.get('on_screen_title', '')}")
                            st.markdown(f"**🔥 Viral Hook:** {row.get('viral_hook', '')}")
                            st.markdown(f"**📝 Caption:** {row.get('caption_body', '')}")
                            st.markdown(f"**#️⃣ Hashtags:** {row.get('hashtags', '')}")
                            st.markdown("---")
                
                with tab3:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Processed", len(processed_data))
                    with col2:
                        st.metric("Successful", success_count)
                    with col3:
                        st.metric("Success Rate", f"{(success_count/len(processed_data)*100):.1f}%")
                
                # Download button
                csv = results_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Results as CSV",
                    data=csv,
                    file_name="vibecode_viral_content.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    
    except Exception as e:
        st.error(f"❌ Processing failed: {e}")

def process_google_sheet(openrouter_key, sheet_id, worksheet_name, creds_file, batch_size, confirm_cost, model_name):
    """Process Google Sheet data"""
    
    try:
        with st.spinner("🔄 Connecting to Google Sheets..."):
            # Save credentials to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                creds_data = json.loads(creds_file.read().decode())
                json.dump(creds_data, f)
                temp_creds_path = f.name
            
            # Initialize factory
            factory = VibeCodeContentFactory(
                google_credentials_path=temp_creds_path,
                openrouter_api_key=openrouter_key,
                sheet_id=sheet_id,
                worksheet_name=worksheet_name,
                model=model_name
            )
            
            # Read data
            data = factory.read_sheet_data()
            st.success(f"✅ Connected! Found {len(data)} rows in sheet")
            
            # Filter unprocessed
            unprocessed = [row for row in data if not row.get('viral_hook')]
            
            if not unprocessed:
                st.info("🎉 All rows already processed!")
                return
            
            st.info(f"Found {len(unprocessed)} rows to process")
            
            # Process with progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Run processing
            factory.run(batch_size=batch_size, confirm_cost=False)  # Skip confirmation in web UI
            
            st.success("🎉 Processing complete! Check your Google Sheet for results.")
            
            # Clean up temp file
            os.unlink(temp_creds_path)
    
    except Exception as e:
        st.error(f"❌ Google Sheets processing failed: {e}")

def show_sample_data():
    """Show sample data format"""
    sample_data = {
        'title': [
            'How to Build MVPs Fast with AI',
            'The Secret to 10x Developer Productivity', 
            'Why 90% of Startups Fail (And How to Avoid It)'
        ],
        'keywords': [
            'MVP, startup, AI, development',
            'productivity, developer, tools, automation',
            'startup, failure, success, entrepreneurship'
        ],
        'transcription': [
            'In this video I show you how to build MVPs 10x faster using AI tools. Most developers waste months on features nobody wants...',
            'Today I\'m sharing the productivity secrets that helped me ship 5 apps in 6 months. The key is automation and the right tools...',
            'After analyzing 1000+ failed startups, I found the #1 reason they fail. It\'s not what you think, and it\'s completely avoidable...'
        ]
    }
    
    return pd.DataFrame(sample_data)

if __name__ == "__main__":
    main()