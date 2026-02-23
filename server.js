const express = require('express');
const multer = require('multer');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8080;

// Create directories for storing frames
const STORAGE_DIR = path.join(__dirname, 'stored-frames');
const SESSIONS_DIR = path.join(STORAGE_DIR, 'sessions');

// Ensure directories exist
if (!fs.existsSync(STORAGE_DIR)) {
  fs.mkdirSync(STORAGE_DIR, { recursive: true });
}
if (!fs.existsSync(SESSIONS_DIR)) {
  fs.mkdirSync(SESSIONS_DIR, { recursive: true });
}

// Configure multer for file uploads
const storage = multer.memoryStorage();
const upload = multer({
  storage: storage,
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB limit per file
  },
});

// Middleware
app.use(cors({
  origin: true, // Allow any origin
  credentials: true, // Allow credentials
  exposedHeaders: ['Content-Length', 'Content-Type'],
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true }));

// Serve OCR test pages
app.use('/ocr-test-tfjs', express.static(path.join(__dirname, '..', 'ocr-test-tfjs')));
app.use('/ocr-test-onnx', express.static(path.join(__dirname, '..', 'ocr-conversion', 'webapp')));

// Serve model files with CORS headers
app.use('/models', (req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  next();
}, express.static(path.join(__dirname, 'models')));

// Logging middleware
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
  next();
});

/**
 * POST /api/v2/detection-frames
 * Endpoint to receive and store detection frames
 */
app.post('/api/v2/detection-frames', upload.any(), async (req, res) => {
  try {
    const { sessionId, frameCount } = req.body;

    if (!sessionId) {
      return res.status(400).json({
        success: false,
        error: 'Session ID is required',
      });
    }

    if (!frameCount || parseInt(frameCount) === 0) {
      return res.status(400).json({
        success: false,
        error: 'Frame count is required and must be greater than 0',
      });
    }

    console.log(`Processing ${frameCount} frames for session: ${sessionId}`);

    // Create session directory
    const sessionDir = path.join(SESSIONS_DIR, sessionId);
    if (!fs.existsSync(sessionDir)) {
      fs.mkdirSync(sessionDir, { recursive: true });
    }

    const frames = [];
    const count = parseInt(frameCount);

    // Process each frame
    for (let i = 0; i < count; i++) {
      const rawImage = req.files.find(f => f.fieldname === `rawImage_${i}`);
      const croppedImage = req.files.find(f => f.fieldname === `croppedImage_${i}`);
      const metadataStr = req.body[`metadata_${i}`];

      if (!rawImage || !metadataStr) {
        console.warn(`Missing data for frame ${i}`);
        continue;
      }

      // Parse metadata
      const metadata = JSON.parse(metadataStr);

      // Use the original filename from the frontend (which includes status prefix)
      // Fallback to old format if originalname is not available
      const rawImageFilename = rawImage.originalname || `frame_${i}_raw.jpg`;
      const metadataFilename = rawImageFilename.replace('_raw.jpg', '_metadata.json');

      // Save raw image with descriptive filename
      const rawImagePath = path.join(sessionDir, rawImageFilename);
      fs.writeFileSync(rawImagePath, rawImage.buffer);

      // Save cropped image with descriptive filename (if exists)
      let croppedImagePath = null;
      if (croppedImage) {
        const croppedImageFilename = croppedImage.originalname || `frame_${i}_cropped.jpg`;
        croppedImagePath = path.join(sessionDir, croppedImageFilename);
        fs.writeFileSync(croppedImagePath, croppedImage.buffer);
      }

      // Save metadata with descriptive filename
      const metadataPath = path.join(sessionDir, metadataFilename);
      fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2));

      frames.push({
        frameIndex: i,
        rawImagePath: rawImagePath,
        croppedImagePath: croppedImagePath, // Can be null for failed frames
        metadataPath: metadataPath,
        metadata: metadata,
        filename: rawImageFilename, // Store the descriptive filename
      });

      console.log(`Saved frame ${i} (${rawImageFilename})${croppedImage ? ' with cropped image' : ' (no cropped image)'} for session ${sessionId}`);
    }

    // Compute session-level (stack-level) final classification once
    const stackFrames = frames
      .map((f) => f.metadata)
      .filter((m) => m && m.includedInStack === true);

    const positiveVotes = stackFrames.filter(
      (m) => m.individualClassificationResult === "positive"
    ).length;
    const negativeVotes = stackFrames.filter(
      (m) => m.individualClassificationResult === "negative"
    ).length;

    const totalVotes = positiveVotes + negativeVotes;

    const finalClassificationResult =
      totalVotes > 0 && positiveVotes >= negativeVotes ? "positive" : totalVotes > 0 ? "negative" : null;

    const finalVoteFractions =
      totalVotes > 0
        ? {
            positive: positiveVotes / totalVotes,
            negative: negativeVotes / totalVotes,
          }
        : null;

    const finalVoteScore = totalVotes > 0 ? Math.max(positiveVotes, negativeVotes) / totalVotes : null;

    // Save session summary
    const sessionSummary = {
      sessionId,
      timestamp: new Date().toISOString(),
      frameCount: frames.length,
      stackFrameCount: stackFrames.length,
      stackFrameIndices: stackFrames
        .map((m) => m.frameIndex)
        .filter((i) => typeof i === "number"),
      stackFrameTimestamps: stackFrames
        .map((m) => m.imageTimestamp)
        .filter((t) => typeof t === "number"),
      finalClassificationResult,
      finalVoteFractions,
      finalVoteScore,
      frames: frames.map((f) => ({
        frameIndex: f.frameIndex,
        metadata: f.metadata,
      })),
    };

    const summaryPath = path.join(sessionDir, 'session_summary.json');
    fs.writeFileSync(summaryPath, JSON.stringify(sessionSummary, null, 2));

    console.log(`Session ${sessionId} completed with ${frames.length} frames`);

    res.json({
      success: true,
      sessionId,
      frameCount: frames.length,
      storagePath: sessionDir,
      message: `Successfully stored ${frames.length} frames`,
    });

  } catch (error) {
    console.error('Error processing frames:', error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

/**
 * GET /api/v2/detection-frames/:sessionId
 * Retrieve session information
 */
app.get('/api/v2/detection-frames/:sessionId', (req, res) => {
  try {
    const { sessionId } = req.params;
    const sessionDir = path.join(SESSIONS_DIR, sessionId);

    if (!fs.existsSync(sessionDir)) {
      return res.status(404).json({
        success: false,
        error: 'Session not found',
      });
    }

    const summaryPath = path.join(sessionDir, 'session_summary.json');
    if (!fs.existsSync(summaryPath)) {
      return res.status(404).json({
        success: false,
        error: 'Session summary not found',
      });
    }

    const summary = JSON.parse(fs.readFileSync(summaryPath, 'utf8'));

    res.json({
      success: true,
      session: summary,
    });

  } catch (error) {
    console.error('Error retrieving session:', error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

/**
 * GET /api/v2/detection-frames
 * List all sessions
 */
app.get('/api/v2/detection-frames', (req, res) => {
  try {
    const sessions = fs.readdirSync(SESSIONS_DIR)
      .filter(file => {
        const sessionPath = path.join(SESSIONS_DIR, file);
        return fs.statSync(sessionPath).isDirectory();
      })
      .map(sessionId => {
        const summaryPath = path.join(SESSIONS_DIR, sessionId, 'session_summary.json');
        if (fs.existsSync(summaryPath)) {
          const summary = JSON.parse(fs.readFileSync(summaryPath, 'utf8'));
          return {
            sessionId: summary.sessionId,
            timestamp: summary.timestamp,
            frameCount: summary.frameCount,
          };
        }
        return null;
      })
      .filter(session => session !== null)
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    res.json({
      success: true,
      count: sessions.length,
      sessions,
    });

  } catch (error) {
    console.error('Error listing sessions:', error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

/**
 * DELETE /api/v2/detection-frames/:sessionId
 * Delete a session and its frames
 */
app.delete('/api/v2/detection-frames/:sessionId', (req, res) => {
  try {
    const { sessionId } = req.params;
    const sessionDir = path.join(SESSIONS_DIR, sessionId);

    if (!fs.existsSync(sessionDir)) {
      return res.status(404).json({
        success: false,
        error: 'Session not found',
      });
    }

    // Delete directory and all contents
    fs.rmSync(sessionDir, { recursive: true, force: true });

    console.log(`Deleted session: ${sessionId}`);

    res.json({
      success: true,
      message: `Session ${sessionId} deleted successfully`,
    });

  } catch (error) {
    console.error('Error deleting session:', error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    storageDir: STORAGE_DIR,
  });
});

/**
 * POST /api/v2/remote-log
 * Remote logging endpoint for mobile debugging
 * Receives logs from the frontend and prints them to the server console
 */
app.post('/api/v2/remote-log', (req, res) => {
  try {
    const { level, message, data, timestamp, userAgent } = req.body;
    
    const logPrefix = `[REMOTE ${(level || 'LOG').toUpperCase()}] [${timestamp || new Date().toISOString()}]`;
    
    // Color-code based on level
    if (level === 'error') {
      console.error('\x1b[31m%s\x1b[0m', logPrefix, message);
      if (data) {
        console.error('\x1b[31m%s\x1b[0m', '  Data:', JSON.stringify(data, null, 2));
      }
    } else if (level === 'warn') {
      console.warn('\x1b[33m%s\x1b[0m', logPrefix, message);
      if (data) {
        console.warn('\x1b[33m%s\x1b[0m', '  Data:', JSON.stringify(data, null, 2));
      }
    } else {
      console.log('\x1b[36m%s\x1b[0m', logPrefix, message);
      if (data) {
        console.log('\x1b[36m%s\x1b[0m', '  Data:', JSON.stringify(data, null, 2));
      }
    }
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error in remote-log:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ---- OCR Debug Endpoint ----
// Accepts crop images + OCR pipeline results from the frontend for offline analysis.
const DEBUG_OCR_DIR = path.join(STORAGE_DIR, 'debug-ocr');
if (!fs.existsSync(DEBUG_OCR_DIR)) {
  fs.mkdirSync(DEBUG_OCR_DIR, { recursive: true });
}

app.post('/api/v2/debug/ocr', (req, res) => {
  try {
    // Handle status-type messages (lightweight logging from mobile)
    if (req.body.type === 'status' || req.body.type === 'ocrService') {
      const logLine = JSON.stringify({ ...req.body, receivedAt: new Date().toISOString() });
      const logPath = path.join(DEBUG_OCR_DIR, 'status.log');
      fs.appendFileSync(logPath, logLine + '\n');
      console.log(`[OCR Status] ${req.body.step}`, req.body);
      return res.json({ success: true });
    }

    const { sessionId, cropIndex, imageBase64, ocrResult, debugInfo } = req.body;

    if (!sessionId || cropIndex === undefined || !imageBase64) {
      return res.status(400).json({ success: false, error: 'Missing required fields: sessionId, cropIndex, imageBase64' });
    }

    // Create session directory
    const sessionDir = path.join(DEBUG_OCR_DIR, sessionId);
    if (!fs.existsSync(sessionDir)) {
      fs.mkdirSync(sessionDir, { recursive: true });
    }

    // Save the crop image (strip data URL prefix)
    const base64Data = imageBase64.replace(/^data:image\/\w+;base64,/, '');
    const imageBuffer = Buffer.from(base64Data, 'base64');
    const imagePath = path.join(sessionDir, `crop_${cropIndex}.jpg`);
    fs.writeFileSync(imagePath, imageBuffer);

    // Save OCR result + debug info as JSON
    const metadata = {
      cropIndex,
      timestamp: new Date().toISOString(),
      ocrResult: ocrResult || null,
      debugInfo: debugInfo || null,
    };
    const jsonPath = path.join(sessionDir, `crop_${cropIndex}_result.json`);
    fs.writeFileSync(jsonPath, JSON.stringify(metadata, null, 2));

    console.log(`[OCR Debug] Saved crop ${cropIndex} for session ${sessionId} (${imageBuffer.length} bytes)`);
    res.json({ success: true, sessionId, cropIndex, imagePath });
  } catch (error) {
    console.error('Error in debug/ocr:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({
    success: false,
    error: 'Internal server error',
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`\n🚀 BMT Frame Storage Backend Server`);
  console.log(`📡 Server running on port ${PORT}`);
  console.log(`💾 Storage directory: ${STORAGE_DIR}`);
  console.log(`🔗 API endpoint: http://localhost:${PORT}/api/v2/detection-frames`);
  console.log(`❤️  Health check: http://localhost:${PORT}/health\n`);
});
