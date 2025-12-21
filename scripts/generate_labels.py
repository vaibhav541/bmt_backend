#!/usr/bin/env python3
"""
Simple script to generate ground truth labels for blur and lighting detection
using GPT-4o Vision API
"""

import os
import json
import csv
import argparse
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm
import time

# Import utility functions
from utils import (
    encode_image_to_base64,
    get_session_frames,
    ensure_directory,
    calculate_cost,
    print_cost_summary
)

# Load environment variables from parent directory
load_dotenv(Path(__file__).parent.parent / '.env')

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-2024-11-20')
FRAMES_DIR = os.getenv('FRAMES_DIR', '../stored-frames/sessions')
GROUND_TRUTH_DIR = os.getenv('GROUND_TRUTH_DIR', '../ground-truth')
IMAGE_RESIZE_WIDTH = int(os.getenv('IMAGE_RESIZE_WIDTH', 512))
IMAGE_DETAIL_LEVEL = os.getenv('IMAGE_DETAIL_LEVEL', 'high')

# Enhanced prompt for GPT-4o with test result and image source detection
PROMPT = """Analyze this medical test strip image comprehensively:

1. BLUR: Is the image blurred or out of focus?
2. LIGHTING: Is the lighting adequate for analysis?
3. TEST RESULT: What is the test result? Look for control (C) and test (T) lines.
   - Positive: Both C and T lines visible
   - Negative: Only C line visible
   - Invalid: No C line or unclear
4. IMAGE SOURCE: Is this a real physical test or an image from a screen?
   - Real: Physical test kit with natural lighting, texture, 3D depth
   - Screen: Digital display with pixel grid, screen glare, backlight, moiré patterns

Respond ONLY with valid JSON:
{
  "blur": {
    "isBlurred": true/false,
    "confidence": 0-100,
    "reason": "brief explanation"
  },
  "lighting": {
    "isGood": true/false,
    "level": "underexposed|normal|overexposed",
    "confidence": 0-100,
    "reason": "brief explanation"
  },
  "testResult": {
    "result": "positive|negative|invalid",
    "confidence": 0-100,
    "reason": "brief explanation of what lines are visible"
  },
  "imageSource": {
    "source": "real|screen",
    "confidence": 0-100,
    "indicators": ["list of detected indicators like 'pixel grid', 'screen glare', 'natural texture', etc."]
  }
}"""


def analyze_image(image_path: str, client: OpenAI) -> dict:
    """
    Send image to GPT-4o and get blur/lighting assessment
    
    Args:
        image_path: Path to image file
        client: OpenAI client instance
        
    Returns:
        Dict with blur and lighting assessment
    """
    try:
        # Encode image to base64
        base64_image = encode_image_to_base64(image_path, IMAGE_RESIZE_WIDTH)
        
        # Call GPT-4o Vision API
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": IMAGE_DETAIL_LEVEL
                            }
                        }
                    ]
                }
            ],
            max_completion_tokens=500,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        result = json.loads(response.choices[0].message.content)
        
        return {
            "success": True,
            "result": result,
            "tokens": {
                "input": response.usage.prompt_tokens,
                "output": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }
        
    except Exception as e:
        print(f"\nError processing {image_path}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def process_session(session_dir: str, client: OpenAI, limit: int = 0) -> dict:
    """
    Process all frames in a session directory
    
    Args:
        session_dir: Path to session directory
        client: OpenAI client instance
        limit: Maximum number of frames to process (0 = all)
        
    Returns:
        Dict with session results
    """
    session_id = Path(session_dir).name
    frames = get_session_frames(session_dir)
    
    if limit > 0:
        frames = frames[:limit]
    
    print(f"\nProcessing session: {session_id}")
    print(f"Found {len(frames)} frames")
    
    results = {
        "sessionId": session_id,
        "totalFrames": len(frames),
        "frames": [],
        "statistics": {
            "totalProcessed": 0,
            "totalFailed": 0,
            "totalTokens": 0,
            "totalCost": 0.0
        }
    }
    
    # Process each frame with progress bar
    for frame_path in tqdm(frames, desc="Analyzing frames"):
        frame_name = Path(frame_path).name
        
        # Analyze image
        analysis = analyze_image(frame_path, client)
        
        if analysis["success"]:
            results["frames"].append({
                "filename": frame_name,
                "groundTruth": analysis["result"],
                "tokens": analysis["tokens"]
            })
            results["statistics"]["totalProcessed"] += 1
            results["statistics"]["totalTokens"] += analysis["tokens"]["total"]
        else:
            results["frames"].append({
                "filename": frame_name,
                "error": analysis["error"]
            })
            results["statistics"]["totalFailed"] += 1
        
        # Small delay to avoid rate limits
        time.sleep(0.1)
    
    # Calculate cost
    cost_data = calculate_cost(
        num_images=results["statistics"]["totalProcessed"],
        avg_input_tokens=300,
        avg_output_tokens=200
    )
    results["statistics"]["totalCost"] = cost_data["total_cost"]
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Generate ground truth labels using GPT-4o')
    parser.add_argument('--session', type=str, help='Specific session ID to process')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of frames (0 = all)')
    parser.add_argument('--output', type=str, help='Output file path')
    parser.add_argument('--new-only', action='store_true', 
                       help='Process only new sessions (skip sessions that already have ground truth JSON files)')
    
    args = parser.parse_args()
    
    # Validate API key
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not found in .env file")
        return
    
    # Initialize OpenAI client
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Ensure output directory exists (resolve to absolute path)
    script_dir = Path(__file__).parent.resolve()
    backend_dir = script_dir.parent
    ground_truth_path = (backend_dir / 'ground-truth').resolve()
    ensure_directory(str(ground_truth_path))
    
    # Get sessions to process (resolve to absolute path)
    frames_path = (backend_dir / 'stored-frames' / 'sessions').resolve()
    if not frames_path.exists():
        print(f"Error: Frames directory not found: {frames_path}")
        return
    
    if args.session:
        sessions = [frames_path / args.session]
    else:
        sessions = [d for d in frames_path.iterdir() if d.is_dir()]
    
    # Filter sessions based on --new-only flag
    if args.new_only and not args.session:
        original_count = len(sessions)
        sessions = [
            s for s in sessions 
            if not (ground_truth_path / f"{s.name}.json").exists()
        ]
        skipped = original_count - len(sessions)
        if skipped > 0:
            print(f"\n⏭️  Skipping {skipped} session(s) with existing ground truth")
    
    if not sessions:
        print("\n⚠️  No sessions to process!")
        if args.new_only:
            print("   All sessions already have ground truth. Remove --new-only to reprocess.")
        return
    
    print(f"\n{'='*60}")
    print(f"GPT-4o Ground Truth Generation")
    print(f"{'='*60}")
    print(f"Model: {OPENAI_MODEL}")
    print(f"Mode: {'New sessions only' if args.new_only else 'All sessions'}")
    print(f"Sessions to process: {len(sessions)}")
    print(f"Frame limit: {args.limit if args.limit > 0 else 'All'}")
    print(f"{'='*60}\n")
    
    all_results = []
    total_cost = 0.0
    
    # Process each session
    for session_dir in sessions:
        if not session_dir.is_dir():
            continue
            
        results = process_session(str(session_dir), client, args.limit)
        all_results.append(results)
        total_cost += results["statistics"]["totalCost"]
        
        # Save results for this session
        if args.output:
            output_file = args.output
        else:
            output_file = str(ground_truth_path / f"{results['sessionId']}.json")
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ Saved: {output_file}")
        print(f"   Processed: {results['statistics']['totalProcessed']} frames")
        print(f"   Failed: {results['statistics']['totalFailed']} frames")
        print(f"   Cost: ${results['statistics']['totalCost']:.2f}")
    
    # Generate CSV from all results
    csv_output_path = ground_truth_path / 'ground_truth_labels.csv'
    csv_rows = []
    
    for result in all_results:
        session_id = result['sessionId']
        for frame in result['frames']:
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
        
        print(f"\n📊 CSV saved to: {csv_output_path}")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total sessions processed: {len(all_results)}")
    print(f"Total frames processed: {sum(r['statistics']['totalProcessed'] for r in all_results)}")
    print(f"Total cost: ${total_cost:.2f}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
