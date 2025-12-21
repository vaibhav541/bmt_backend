# Ground Truth Generation with GPT-4o

Simple Python scripts to generate ground truth labels for blur and lighting detection using GPT-4o Vision API.

## 📁 Files

- **`generate_labels.py`** - Generate ground truth labels from stored frames
- **`compare_results.py`** - Compare your algorithm with ground truth
- **`utils.py`** - Helper functions

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend-frame-storage
pip install -r requirements.txt
```

### 2. Configure API Key

The `.env` file is already configured with your OpenAI API key.

### 3. Generate Ground Truth Labels

**Test with 20 frames:**
```bash
cd scripts
python generate_labels.py --limit 20
```

**Process specific session:**
```bash
python generate_labels.py --session aad8bfa4-1846-4270-a5d6-b8b6d9635b4e --limit 50
```

**Process all frames in all sessions:**
```bash
python generate_labels.py
```

### 4. Compare with Your Algorithm

```bash
python compare_results.py
```

**Show misclassified frames:**
```bash
python compare_results.py --show-misclassified
```

**Save detailed results:**
```bash
python compare_results.py --output validation_report.json
```

## 📊 Output

### Ground Truth File (`ground-truth/session-id.json`)

```json
{
  "sessionId": "aad8bfa4-1846-4270-a5d6-b8b6d9635b4e",
  "totalFrames": 50,
  "frames": [
    {
      "filename": "pending_1765730262965_raw.jpg",
      "groundTruth": {
        "blur": {
          "isBlurred": false,
          "confidence": 95,
          "reason": "Image is sharp with clear edges"
        },
        "lighting": {
          "isGood": true,
          "level": "normal",
          "confidence": 90,
          "reason": "Well-lit with good contrast"
        }
      }
    }
  ],
  "statistics": {
    "totalProcessed": 50,
    "totalFailed": 0,
    "totalCost": 0.50
  }
}
```

### Validation Report

```
============================================================
Algorithm Validation Report
============================================================

Processing session: aad8bfa4-1846-4270-a5d6-b8b6d9635b4e
  ✅ Compared 50 frames
  Misclassified: 5 frames

============================================================
Blur Detection
============================================================
Accuracy:  94.0%
Precision: 92.5%
Recall:    96.0%
F1 Score:  94.2%

Confusion Matrix:
                Predicted False  Predicted True
Actual False                 40               2
Actual True                   1               7

============================================================
Lighting Detection
============================================================
Accuracy:  88.0%
Precision: 85.0%
Recall:    90.0%
F1 Score:  87.4%

============================================================
OVERALL SUMMARY
============================================================
Total sessions: 1
Total frames: 50
Average blur detection accuracy: 94.0%
Average lighting detection accuracy: 88.0%
============================================================
```

## 💰 Cost Estimates

- **20 frames**: ~$0.20
- **50 frames**: ~$0.50
- **100 frames**: ~$1.00
- **500 frames**: ~$5.00
- **1000 frames**: ~$10.00

## 🔧 Configuration

Edit `.env` to customize:

```bash
# Model selection
OPENAI_MODEL=gpt-4o

# Image quality (affects cost)
IMAGE_RESIZE_WIDTH=512
IMAGE_DETAIL_LEVEL=high  # or "low" for cheaper

# Processing limits
PROCESS_LIMIT=0  # 0 = all frames
MAX_COST_PER_SESSION=10.00  # Safety limit
```

## 📝 Notes

- **Ground truth files** are saved to `ground-truth/` directory
- **Progress** is shown with a progress bar
- **Cost tracking** is automatic
- **Rate limiting** is handled automatically (0.1s delay between requests)
- **Resumable** - Can restart if interrupted

## 🎯 Next Steps

1. Run on a small batch (20 frames) to test
2. Review the ground truth labels
3. Compare with your algorithm
4. Identify areas for improvement
5. Tune your algorithm parameters
6. Re-run validation

## 🐛 Troubleshooting

**Error: OPENAI_API_KEY not found**
- Check that `.env` file exists in `backend-frame-storage/` directory
- Verify the API key is correct

**Error: No frames found**
- Check that `stored-frames/sessions/` directory contains session folders
- Verify frames are named with `*_raw.jpg` pattern

**Rate limit errors**
- Increase delay in `generate_labels.py` (line 177)
- Reduce `MAX_CONCURRENT_REQUESTS` in `.env`

## 📚 Example Workflow

```bash
# 1. Test with 20 frames
python generate_labels.py --limit 20

# 2. Check the output
ls -la ../ground-truth/

# 3. Compare with algorithm
python compare_results.py --show-misclassified

# 4. If results look good, process more frames
python generate_labels.py --limit 100

# 5. Generate full validation report
python compare_results.py --output full_validation.json
```

## ✅ Success Criteria

- **Blur Detection**: Target 90%+ accuracy
- **Lighting Detection**: Target 85%+ accuracy
- **F1 Score**: Target 0.85+ for both

Use the misclassified frames to identify patterns and tune your algorithm!
