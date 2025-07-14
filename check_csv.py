#!/usr/bin/env python3
"""
Quick CSV column checker
"""
import pandas as pd
import sys

def check_csv_columns(file_path):
    """Check what columns are in the CSV"""
    try:
        df = pd.read_csv(file_path)
        
        print(f"📊 CSV Analysis:")
        print(f"   • Total rows: {len(df)}")
        print(f"   • Total columns: {len(df.columns)}")
        print(f"   • Column names:")
        
        for i, col in enumerate(df.columns):
            print(f"     {i+1}. '{col}' (type: {df[col].dtype})")
        
        print(f"\n🔍 Looking for required columns:")
        print(f"   • 'title': {'✅ Found' if 'title' in df.columns else '❌ Missing'}")
        print(f"   • 'transcription': {'✅ Found' if 'transcription' in df.columns else '❌ Missing'}")
        print(f"   • 'transcript': {'✅ Found' if 'transcript' in df.columns else '❌ Missing'}")
        print(f"   • 'keywords': {'✅ Found' if 'keywords' in df.columns else '❌ Missing'}")
        
        # Show sample data
        print(f"\n📋 Sample data (first 2 rows):")
        for col in df.columns:
            print(f"   {col}:")
            for i in range(min(2, len(df))):
                value = str(df.iloc[i][col])[:50]
                print(f"     Row {i+1}: {value}...")
        
        return df.columns.tolist()
        
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_csv_columns(sys.argv[1])
    else:
        print("Usage: python check_csv.py your_file.csv")