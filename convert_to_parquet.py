#!/usr/bin/env python3
"""
Convert existing JSON data files to Parquet format
Part of migration to Parquet (Issue #13)
Timestamp: 2026-02-03 18:50 GMT+1
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def convert_json_to_parquet(json_file, parquet_file=None):
    """Convert a JSON file to Parquet format"""
    json_path = Path(json_file)
    
    if not json_path.exists():
        print(f"❌ File not found: {json_file}")
        return False
    
    # Determine output filename
    if parquet_file is None:
        parquet_file = json_path.with_suffix('.parquet')
    
    print(f"Converting {json_file}...")
    
    try:
        # Load JSON
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Convert to DataFrame
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # Handle nested structures
            df = pd.json_normalize(data)
        else:
            print(f"❌ Unknown data structure in {json_file}")
            return False
        
        # Convert timestamp strings to datetime
        for col in df.columns:
            if 'timestamp' in col.lower() or 'date' in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col])
                except:
                    pass
        
        # Save to Parquet
        df.to_parquet(parquet_file, index=False, compression='snappy')
        
        # Calculate compression ratio
        json_size = json_path.stat().st_size
        parquet_size = Path(parquet_file).stat().st_size
        ratio = (1 - parquet_size / json_size) * 100
        
        print(f"  ✓ Saved to {parquet_file}")
        print(f"  📊 Rows: {len(df):,}")
        print(f"  📉 Compression: {json_size/1024:.1f} KB → {parquet_size/1024:.1f} KB ({ratio:.1f}% reduction)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    print('=' * 70)
    print('🔄 MIGRATING JSON DATA TO PARQUET')
    print('=' * 70)
    
    data_dir = Path('data')
    
    # Files to convert
    files_to_convert = [
        'predictions.json',
        'resolved_markets.json',
        'additional_resolved_markets.json',
        'large_resolved_markets.json'
    ]
    
    converted = 0
    failed = 0
    
    for filename in files_to_convert:
        json_file = data_dir / filename
        if json_file.exists():
            print()
            if convert_json_to_parquet(json_file):
                converted += 1
            else:
                failed += 1
        else:
            print(f"\n⏭ Skipping {filename} (not found)")
    
    print(f"\n{'='*70}")
    print('✅ Migration complete!')
    print(f'   Converted: {converted}')
    print(f'   Failed: {failed}')
    print(f"{'='*70}")
    
    # List all parquet files
    print('\n📁 Parquet files in data/:')
    for f in sorted(data_dir.glob('*.parquet')):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f'   {f.name:<40} {size_mb:>8.2f} MB')


if __name__ == '__main__':
    main()
