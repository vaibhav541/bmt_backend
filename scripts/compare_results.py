#!/usr/bin/env python3
"""
Compare algorithm results with GPT-4o ground truth labels
"""

import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

# Load environment variables from parent directory
load_dotenv(Path(__file__).parent.parent / '.env')

GROUND_TRUTH_DIR = os.getenv('GROUND_TRUTH_DIR', '../ground-truth')
FRAMES_DIR = os.getenv('FRAMES_DIR', '../stored-frames/sessions')


def load_ground_truth(session_id: str, gt_dir: Path) -> dict:
    """Load ground truth labels for a session"""
    gt_file = gt_dir / f"{session_id}.json"
    
    if not gt_file.exists():
        print(f"Warning: Ground truth file not found: {gt_file}")
        return None
    
    with open(gt_file, 'r') as f:
        return json.load(f)


def load_algorithm_results(session_id: str, frames_dir: Path) -> dict:
    """Load algorithm results from frame metadata files"""
    session_dir = frames_dir / session_id
    
    if not session_dir.exists():
        print(f"Warning: Session directory not found: {session_dir}")
        return {}
    
    results = {}
    
    # Load metadata for each frame
    for metadata_file in session_dir.glob("*_metadata.json"):
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Extract frame filename (raw image)
            frame_name = metadata_file.name.replace('_metadata.json', '_raw.jpg')
            
            # Extract blur and lighting info from metadata
            quality = metadata.get('quality', {})
            
            results[frame_name] = {
                "blur": {
                    "isBlurred": quality.get('isBlurred', False),
                    "laplacianVariance": quality.get('laplacianVariance', 0)
                },
                "lighting": {
                    "brightness": quality.get('brightness', 0),
                    "contrast": quality.get('contrast', 0)
                }
            }
        except Exception as e:
            print(f"Error loading {metadata_file}: {e}")
    
    return results


def calculate_metrics(y_true: list, y_pred: list, label: str) -> dict:
    """Calculate classification metrics"""
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    # Use labels parameter to ensure confusion matrix has correct shape
    cm = confusion_matrix(y_true, y_pred, labels=[False, True])
    
    return {
        "label": label,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "confusion_matrix": cm.tolist()
    }


def compare_session(session_id: str, gt_dir: Path, frames_dir: Path) -> dict:
    """Compare algorithm results with ground truth for a session"""
    
    # Load data
    ground_truth = load_ground_truth(session_id, gt_dir)
    algorithm_results = load_algorithm_results(session_id, frames_dir)
    
    if not ground_truth or not algorithm_results:
        return None
    
    # Prepare comparison data
    blur_true = []
    blur_pred = []
    lighting_true = []
    lighting_pred = []
    misclassified_frames = []
    
    for frame_data in ground_truth['frames']:
        filename = frame_data['filename']
        
        if 'groundTruth' not in frame_data:
            continue
        
        gt = frame_data['groundTruth']
        
        if filename not in algorithm_results:
            continue
        
        algo = algorithm_results[filename]
        
        # Blur comparison
        gt_blur = gt['blur']['isBlurred']
        algo_blur = algo['blur']['isBlurred']
        blur_true.append(gt_blur)
        blur_pred.append(algo_blur)
        
        # Lighting comparison (good lighting = True, bad = False)
        gt_lighting = gt['lighting']['isGood']
        # For algorithm, we need to determine if lighting is good based on brightness/contrast
        # Simple heuristic: brightness between 40-200 is good
        algo_brightness = algo['lighting']['brightness']
        algo_lighting = 40 <= algo_brightness <= 200
        lighting_true.append(gt_lighting)
        lighting_pred.append(algo_lighting)
        
        # Track misclassifications
        if gt_blur != algo_blur or gt_lighting != algo_lighting:
            misclassified_frames.append({
                "filename": filename,
                "blur_mismatch": gt_blur != algo_blur,
                "lighting_mismatch": gt_lighting != algo_lighting,
                "ground_truth": gt,
                "algorithm": algo
            })
    
    # Calculate metrics
    blur_metrics = calculate_metrics(blur_true, blur_pred, "Blur Detection")
    lighting_metrics = calculate_metrics(lighting_true, lighting_pred, "Lighting Detection")
    
    return {
        "sessionId": session_id,
        "totalFrames": len(blur_true),
        "blur_metrics": blur_metrics,
        "lighting_metrics": lighting_metrics,
        "misclassified_frames": misclassified_frames
    }


def print_metrics(metrics: dict):
    """Print metrics in a readable format"""
    print(f"\n{'='*60}")
    print(f"{metrics['label']}")
    print(f"{'='*60}")
    print(f"Accuracy:  {metrics['accuracy']*100:.1f}%")
    print(f"Precision: {metrics['precision']*100:.1f}%")
    print(f"Recall:    {metrics['recall']*100:.1f}%")
    print(f"F1 Score:  {metrics['f1_score']*100:.1f}%")
    
    cm = metrics['confusion_matrix']
    print(f"\nConfusion Matrix:")
    print(f"                Predicted False  Predicted True")
    print(f"Actual False    {cm[0][0]:15d}  {cm[0][1]:14d}")
    print(f"Actual True     {cm[1][0]:15d}  {cm[1][1]:14d}")


def main():
    parser = argparse.ArgumentParser(description='Compare algorithm results with ground truth')
    parser.add_argument('--session', type=str, help='Specific session ID to compare')
    parser.add_argument('--show-misclassified', action='store_true', help='Show misclassified frames')
    parser.add_argument('--output', type=str, help='Output file for detailed results')
    
    args = parser.parse_args()
    
    # Get sessions to compare (resolve to absolute path)
    script_dir = Path(__file__).parent.resolve()
    backend_dir = script_dir.parent
    gt_path = (backend_dir / 'ground-truth').resolve()
    frames_path = (backend_dir / 'stored-frames' / 'sessions').resolve()
    
    if not gt_path.exists():
        print(f"Error: Ground truth directory not found: {gt_path}")
        print("Please run generate_labels.py first to create ground truth labels.")
        return
    
    if args.session:
        sessions = [args.session]
    else:
        sessions = [f.stem for f in gt_path.glob("*.json")]
    
    print(f"\n{'='*60}")
    print(f"Algorithm Validation Report")
    print(f"{'='*60}")
    print(f"Sessions to compare: {len(sessions)}\n")
    
    all_results = []
    
    # Compare each session
    for session_id in sessions:
        print(f"\nProcessing session: {session_id}")
        
        results = compare_session(session_id, gt_path, frames_path)
        
        if not results:
            print(f"  ⚠️  Skipped (missing data)")
            continue
        
        all_results.append(results)
        
        print(f"  ✅ Compared {results['totalFrames']} frames")
        print(f"  Misclassified: {len(results['misclassified_frames'])} frames")
        
        # Print metrics
        print_metrics(results['blur_metrics'])
        print_metrics(results['lighting_metrics'])
        
        # Show misclassified frames if requested
        if args.show_misclassified and results['misclassified_frames']:
            print(f"\n{'='*60}")
            print(f"Misclassified Frames ({len(results['misclassified_frames'])})")
            print(f"{'='*60}")
            for frame in results['misclassified_frames'][:10]:  # Show first 10
                print(f"\n{frame['filename']}:")
                if frame['blur_mismatch']:
                    print(f"  Blur: GT={frame['ground_truth']['blur']['isBlurred']}, "
                          f"Algo={frame['algorithm']['blur']['isBlurred']}")
                if frame['lighting_mismatch']:
                    print(f"  Lighting: GT={frame['ground_truth']['lighting']['isGood']}, "
                          f"Algo brightness={frame['algorithm']['lighting']['brightness']:.1f}")
    
    # Overall summary
    if all_results:
        total_frames = sum(r['totalFrames'] for r in all_results)
        avg_blur_acc = sum(r['blur_metrics']['accuracy'] for r in all_results) / len(all_results)
        avg_lighting_acc = sum(r['lighting_metrics']['accuracy'] for r in all_results) / len(all_results)
        
        print(f"\n{'='*60}")
        print(f"OVERALL SUMMARY")
        print(f"{'='*60}")
        print(f"Total sessions: {len(all_results)}")
        print(f"Total frames: {total_frames}")
        print(f"Average blur detection accuracy: {avg_blur_acc*100:.1f}%")
        print(f"Average lighting detection accuracy: {avg_lighting_acc*100:.1f}%")
        print(f"{'='*60}\n")
    
    # Save detailed results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"✅ Detailed results saved to: {args.output}\n")


if __name__ == "__main__":
    main()
