#!/usr/bin/env python3
"""
Convert new_samples HEIC images to sessions format (JPG) for ground truth generation
"""

import os
import uuid
from pathlib import Path
from PIL import Image
import pillow_heif

# Register HEIF opener
pillow_heif.register_heif_opener()

def convert_heic_to_jpg(heic_path: Path, output_path: Path):
    """Convert HEIC image to JPG"""
    try:
        # Open HEIC image
        img = Image.open(heic_path)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save as JPG
        img.save(output_path, 'JPEG', quality=95)
        return True
    except Exception as e:
        print(f"Error converting {heic_path}: {e}")
        return False


def main():
    # Paths
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent.parent
    new_samples_dir = project_root / 'new_samples'
    sessions_dir = project_root / 'backend-frame-storage' / 'stored-frames' / 'sessions'
    
    # Create new session directory
    session_id = f"new-samples-{uuid.uuid4()}"
    session_path = sessions_dir / session_id
    session_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"Converting new_samples to sessions format")
    print(f"{'='*60}")
    print(f"Source: {new_samples_dir}")
    print(f"Destination: {session_path}")
    print(f"Session ID: {session_id}")
    print(f"{'='*60}\n")
    
    # Get all HEIC files
    heic_files = list(new_samples_dir.glob('*.HEIC')) + list(new_samples_dir.glob('*.heic'))
    
    if not heic_files:
        print("❌ No HEIC files found in new_samples directory")
        return
    
    print(f"Found {len(heic_files)} HEIC files\n")
    
    # Convert each file
    converted = 0
    failed = 0
    
    for heic_file in heic_files:
        # Create output filename
        jpg_filename = f"{heic_file.stem}.jpg"
        output_path = session_path / jpg_filename
        
        print(f"Converting: {heic_file.name} → {jpg_filename}...", end=' ')
        
        if convert_heic_to_jpg(heic_file, output_path):
            print("✅")
            converted += 1
        else:
            print("❌")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"CONVERSION COMPLETE")
    print(f"{'='*60}")
    print(f"Converted: {converted} files")
    print(f"Failed: {failed} files")
    print(f"Session directory: {session_path}")
    print(f"{'='*60}\n")
    
    if converted > 0:
        print(f"✅ Ready to generate ground truth!")
        print(f"\nRun: python generate_labels.py --session {session_id}")


if __name__ == "__main__":
    main()
