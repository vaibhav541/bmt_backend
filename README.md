# BMT Frame Storage Backend

A Node.js/Express backend service for storing detection frames from the BMT InView frontend application.

## Features

- ✅ Receives and stores detection frames via multipart/form-data
- ✅ Stores raw images, cropped images, and metadata
- ✅ Organizes frames by session ID
- ✅ RESTful API for managing sessions
- ✅ CORS enabled for frontend integration
- ✅ File size limits and validation
- ✅ Session summary generation

## Installation

```bash
cd backend-frame-storage
npm install
```

## Running the Server

### Development Mode (with auto-reload):
```bash
npm run dev
```

### Production Mode:
```bash
npm start
```

The server will start on port 8080 by default. You can change this by setting the `PORT` environment variable:

```bash
PORT=3000 npm start
```

## API Endpoints

### 1. Upload Detection Frames

**POST** `/api/v2/detection-frames`

Upload frames from a detection session.

**Request Format:** `multipart/form-data`

**Body Parameters:**
- `sessionId` (string): Unique session identifier
- `frameCount` (string): Number of frames being uploaded
- `rawImage_0` to `rawImage_N` (files): Raw captured images
- `croppedImage_0` to `croppedImage_N` (files): Cropped strip images
- `metadata_0` to `metadata_N` (strings): JSON metadata for each frame

**Response:**
```json
{
  "success": true,
  "sessionId": "uuid-string",
  "frameCount": 5,
  "storagePath": "/path/to/stored-frames/sessions/uuid-string",
  "message": "Successfully stored 5 frames"
}
```

### 2. Get Session Information

**GET** `/api/v2/detection-frames/:sessionId`

Retrieve information about a specific session.

**Response:**
```json
{
  "success": true,
  "session": {
    "sessionId": "uuid-string",
    "timestamp": "2024-01-01T00:00:00.000Z",
    "frameCount": 5,
    "frames": [...]
  }
}
```

### 3. List All Sessions

**GET** `/api/v2/detection-frames`

Get a list of all stored sessions.

**Response:**
```json
{
  "success": true,
  "count": 10,
  "sessions": [
    {
      "sessionId": "uuid-string",
      "timestamp": "2024-01-01T00:00:00.000Z",
      "frameCount": 5
    },
    ...
  ]
}
```

### 4. Delete Session

**DELETE** `/api/v2/detection-frames/:sessionId`

Delete a session and all its associated frames.

**Response:**
```json
{
  "success": true,
  "message": "Session uuid-string deleted successfully"
}
```

### 5. Health Check

**GET** `/health`

Check if the server is running.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "storageDir": "/path/to/stored-frames"
}
```

## Storage Structure

Frames are stored in the following directory structure:

```
backend-frame-storage/
└── stored-frames/
    └── sessions/
        └── {sessionId}/
            ├── session_summary.json
            ├── frame_0_raw.jpg
            ├── frame_0_cropped.jpg
            ├── frame_0_metadata.json
            ├── frame_1_raw.jpg
            ├── frame_1_cropped.jpg
            ├── frame_1_metadata.json
            └── ...
```

### Session Summary Format

Each session has a `session_summary.json` file:

```json
{
  "sessionId": "uuid-string",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "frameCount": 5,
  "frames": [
    {
      "frameIndex": 0,
      "metadata": {
        "sessionId": "uuid-string",
        "timestamp": 1234567890,
        "frameIndex": 0,
        "detectionBbox": [x1, y1, x2, y2],
        "detectionConfidence": 0.95,
        "aspectRatio": 1.5,
        "classificationResult": "positive",
        "classificationScores": {
          "positive": 0.8,
          "negative": 0.2
        },
        "filteringResults": {
          "isBlurred": false,
          "isLowContrast": false
        }
      }
    },
    ...
  ]
}
```

## Testing

### Using curl:

```bash
# Health check
curl http://localhost:8080/health

# List all sessions
curl http://localhost:8080/api/v2/detection-frames

# Get specific session
curl http://localhost:8080/api/v2/detection-frames/{sessionId}

# Upload frames (example with test files)
curl -X POST http://localhost:8080/api/v2/detection-frames \
  -F "sessionId=test-session-123" \
  -F "frameCount=1" \
  -F "rawImage_0=@test_raw.jpg" \
  -F "croppedImage_0=@test_cropped.jpg" \
  -F 'metadata_0={"timestamp":1234567890,"frameIndex":0}'

# Delete session
curl -X DELETE http://localhost:8080/api/v2/detection-frames/{sessionId}
```

### Using Postman:

1. Create a new POST request to `http://localhost:8080/api/v2/detection-frames`
2. Select "Body" → "form-data"
3. Add the following fields:
   - `sessionId`: text value
   - `frameCount`: text value
   - `rawImage_0`: file
   - `croppedImage_0`: file
   - `metadata_0`: text (JSON string)

## Configuration

### Environment Variables

- `PORT`: Server port (default: 8080)

### File Upload Limits

- Maximum file size: 10MB per file
- Configured in `server.js` via multer settings

## Integration with Frontend

The frontend (`bmt_inview_fe`) is already configured to use this backend:

1. Ensure `REACT_APP_API_ENDPOINT` in frontend `.env` points to this server:
   ```
   REACT_APP_API_ENDPOINT='http://localhost:8080'
   ```

2. Enable frame saving in frontend:
   ```
   REACT_APP_SAVE_FRAMES_ENABLED='true'
   ```

3. Start both servers:
   ```bash
   # Terminal 1: Backend
   cd backend-frame-storage
   npm start

   # Terminal 2: Frontend
   cd bmt_inview_fe
   npm start
   ```

## Production Deployment

### Recommendations:

1. **Use a process manager** (PM2, systemd):
   ```bash
   npm install -g pm2
   pm2 start server.js --name bmt-frame-storage
   ```

2. **Set up reverse proxy** (nginx):
   ```nginx
   location /api/v2/detection-frames {
       proxy_pass http://localhost:8080;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection 'upgrade';
       proxy_set_header Host $host;
       proxy_cache_bypass $http_upgrade;
       client_max_body_size 50M;
   }
   ```

3. **Use environment variables** for configuration
4. **Set up logging** (Winston, Morgan)
5. **Add authentication** if needed
6. **Configure HTTPS**
7. **Set up database** for metadata (optional)
8. **Configure cloud storage** (S3, GCS) for images (optional)

## Security Considerations

- Add authentication middleware for production
- Validate file types and sizes
- Implement rate limiting
- Add request validation
- Set up HTTPS
- Configure CORS properly for production domains
- Add file scanning for malware (optional)

## Troubleshooting

### Port already in use:
```bash
# Change port
PORT=3000 npm start
```

### Permission errors:
```bash
# Ensure write permissions for storage directory
chmod -R 755 stored-frames/
```

### CORS errors:
- Verify frontend URL matches CORS configuration
- Check that both servers are running

### Large file uploads failing:
- Increase multer file size limit in `server.js`
- Configure nginx/reverse proxy limits

## License

MIT
