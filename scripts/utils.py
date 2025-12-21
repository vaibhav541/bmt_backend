"""
Utility functions for ground truth generation and validation
"""

import base64
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image
import io


def resize_image(image_path: str, max_width: int = 512) -> Image.Image:
    """
    Resize image to reduce API costs while maintaining aspect ratio
    
    Args:
        image_path: Path to the image file
        max_width: Maximum width in pixels
        
    Returns:
        Resized PIL Image object
    """
    img = Image.open(image_path)
    
    # Convert to RGB if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Calculate new dimensions
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    
    return img


def encode_image_to_base64(image_path: str, max_width: int = 512) -> str:
    """
    Encode image to base64 string for API transmission
    
    Args:
        image_path: Path to the image file
        max_width: Maximum width for resizing
        
    Returns:
        Base64 encoded string
    """
    img = resize_image(image_path, max_width)
    
    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=95)
    img_bytes = buffer.getvalue()
    
    # Encode to base64
    return base64.b64encode(img_bytes).decode('utf-8')


def parse_llm_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse LLM JSON response with error handling
    
    Args:
        response_text: Raw response text from LLM
        
    Returns:
        Parsed JSON dict or None if parsing fails
    """
    try:
        # Try to parse as JSON
        data = json.loads(response_text)
        
        # Validate required fields
        if 'blur' not in data or 'lighting' not in data:
            print(f"Warning: Missing required fields in response")
            return None
        
        return data
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Response text: {response_text[:200]}...")
        return None


def calculate_cost(
    num_images: int,
    avg_input_tokens: int = 300,
    avg_output_tokens: int = 200,
    image_cost_per_image: float = 0.00765
) -> Dict[str, float]:
    """
    Calculate estimated cost for processing images with GPT-4o
    
    Args:
        num_images: Number of images to process
        avg_input_tokens: Average input tokens per request
        avg_output_tokens: Average output tokens per response
        image_cost_per_image: Cost per image (512x512 with GPT-4o)
        
    Returns:
        Dict with cost breakdown
    """
    # GPT-4o pricing (as of Dec 2024)
    INPUT_TOKEN_COST = 0.0025 / 1000   # $2.50 per 1M tokens
    OUTPUT_TOKEN_COST = 0.010 / 1000   # $10 per 1M tokens
    
    image_cost = num_images * image_cost_per_image
    token_cost = (
        (num_images * avg_input_tokens * INPUT_TOKEN_COST) +
        (num_images * avg_output_tokens * OUTPUT_TOKEN_COST)
    )
    total = image_cost + token_cost
    
    return {
        "image_cost": round(image_cost, 2),
        "token_cost": round(token_cost, 2),
        "total_cost": round(total, 2),
        "cost_per_image": round(total / num_images, 4) if num_images > 0 else 0
    }


def save_checkpoint(data: Dict[str, Any], checkpoint_file: str) -> None:
    """
    Save processing checkpoint for resumability
    
    Args:
        data: Checkpoint data to save
        checkpoint_file: Path to checkpoint file
    """
    checkpoint_path = Path(checkpoint_file)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(checkpoint_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Checkpoint saved: {checkpoint_file}")


def load_checkpoint(checkpoint_file: str) -> Optional[Dict[str, Any]]:
    """
    Load processing checkpoint
    
    Args:
        checkpoint_file: Path to checkpoint file
        
    Returns:
        Checkpoint data or None if file doesn't exist
    """
    checkpoint_path = Path(checkpoint_file)
    
    if not checkpoint_path.exists():
        return None
    
    try:
        with open(checkpoint_path, 'r') as f:
            data = json.load(f)
        print(f"Checkpoint loaded: {checkpoint_file}")
        return data
    except Exception as e:
        print(f"Error loading checkpoint: {e}")
        return None


def ensure_directory(directory: str) -> Path:
    """
    Ensure directory exists, create if it doesn't
    
    Args:
        directory: Directory path
        
    Returns:
        Path object
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_session_frames(session_dir: str) -> list:
    """
    Get all frame images from a session directory
    
    Args:
        session_dir: Path to session directory
        
    Returns:
        List of frame image paths
    """
    session_path = Path(session_dir)
    
    if not session_path.exists():
        return []
    
    # Get all image files (jpg, jpeg, png)
    frames = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
        for file in session_path.glob(ext):
            # Skip metadata files
            if not file.name.endswith('.json'):
                frames.append(str(file))
    
    # Sort by filename
    frames.sort()
    
    return frames


def load_session_metadata(session_dir: str) -> Optional[Dict[str, Any]]:
    """
    Load session summary metadata
    
    Args:
        session_dir: Path to session directory
        
    Returns:
        Session metadata dict or None
    """
    metadata_file = Path(session_dir) / "session_summary.json"
    
    if not metadata_file.exists():
        return None
    
    try:
        with open(metadata_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading session metadata: {e}")
        return None


def format_time(seconds: float) -> str:
    """
    Format seconds into human-readable time string
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def print_cost_summary(cost_data: Dict[str, float]) -> None:
    """
    Print formatted cost summary
    
    Args:
        cost_data: Cost data from calculate_cost()
    """
    print("\n" + "="*50)
    print("COST SUMMARY")
    print("="*50)
    print(f"Image Processing Cost: ${cost_data['image_cost']:.2f}")
    print(f"Token Processing Cost: ${cost_data['token_cost']:.2f}")
    print(f"Total Cost:            ${cost_data['total_cost']:.2f}")
    print(f"Cost per Image:        ${cost_data['cost_per_image']:.4f}")
    print("="*50 + "\n")
