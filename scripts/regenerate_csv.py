#!/usr/bin/env python3
"""
Regenerate ground_truth_labels.csv from all existing JSON files
"""

import json
import csv
from pathlib import Path

def main():
    # Paths
    script_dir = Path(__file__).parent.resolve()
    ground_truth_dir = script_dir.parent / 'ground-truth'
    csv_output_path = ground_truth_dir / 'ground_truth_labels.csv'
    
    print(f"\n{'='*60}")
    print(f"Regenerating CSV from JSON files")
    print(f"{'='*60}\n")
    
    # Find all JSON files
    json_files = list(ground_truth_dir.glob('*.json'))
    print(f"Found {len(json_files)} JSON files")
    
    csv_rows = []
    
    # Process each JSON file
    for json_file in sorted(json_files):
        print(f"Processing: {json_file.name}")
        
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        session_id = data['sessionId']
        
        for frame in data['frames']:
            if 'groundTruth' in frame:
                gt = frame['groundTruth']
                # Extract test result and image source with safe defaults
                test_result = gt.get('testResult', {})
                image_source = gt.get('imageSource', {})
                
                csv_rows.append({
                    'session_id': session_id,
                    'filename': frame['filename'],
                    'is_blurred': gt['blur']['isBlurred'],
                    'blur_confidence': gt['blur']['confidence'],
                    'blur_reason': gt['blur']['reason'],
                    'is_good_lighting': gt['lighting']['isGood'],
                    'lighting_level': gt['lighting']['level'],
                    'lighting_confidence': gt['lighting']['confidence'],
                    'lighting_reason': gt['lighting']['reason'],
                    'test_result': test_result.get('result', 'unknown'),
                    'test_result_confidence': test_result.get('confidence', 0),
                    'test_result_reason': test_result.get('reason', ''),
                    'image_source': image_source.get('source', 'unknown'),
                    'image_source_confidence': image_source.get('confidence', 0),
                    'image_source_indicators': ', '.join(image_source.get('indicators', [])),
                })
    
    # Write CSV
    if csv_rows:
        with open(csv_output_path, 'w', newline='') as csvfile:
            fieldnames = [
                'session_id', 'filename',
                'is_blurred', 'blur_confidence', 'blur_reason',
                'is_good_lighting', 'lighting_level', 'lighting_confidence', 'lighting_reason',
                'test_result', 'test_result_confidence', 'test_result_reason',
                'image_source', 'image_source_confidence', 'image_source_indicators'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        
        print(f"\n✅ CSV regenerated: {csv_output_path}")
        print(f"📊 Total rows: {len(csv_rows)}")
        print(f"{'='*60}\n")
    else:
        print("\n❌ No data found to write to CSV")


if __name__ == "__main__":
    main()
