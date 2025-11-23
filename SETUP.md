# Quick Setup Guide

## Getting Started in 5 Minutes

### Step 1: Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies (this may take 5-10 minutes)
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start the backend server
python -m uvicorn app.main:app --reload
```

Backend will run on: `http://localhost:8000`

### Step 1 (Alternative): Backend Setup with Docker

If you're on Windows or having trouble with Python dependencies, use Docker instead:

```bash
# Navigate to backend
cd backend

# Build the Docker image
docker build -t ai-proctor-backend .

# Run the container
docker run -p 8000:8000 ai-proctor-backend
```

Backend will run on: `http://localhost:8000`

**Note:** Docker Desktop must be installed. Download from [docker.com](https://www.docker.com/products/docker-desktop/)

### Step 2: Frontend Setup

Open a new terminal:

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will run on: `http://localhost:3000`

### Step 3: Test the System

1. Open `http://localhost:3000` in your browser
2. Click "Start Interview"
3. Allow camera and microphone permissions
4. Click "Start Interview" button on the interview page
5. The system will start monitoring!

## Verification

### Check Backend

Visit `http://localhost:8000` - you should see:
```json
{
  "status": "ok",
  "message": "AI Proctor API is running",
  "version": "1.0.0"
}
```

### Check Frontend

Visit `http://localhost:3000` - you should see the AI Proctor homepage

## Testing Detection Features

### Test Eye Gaze Tracking
- Start an interview session
- Look away from the screen for 3+ seconds
- You should see an alert

### Test Multiple Person Detection
- Have another person appear in the frame
- Alert should trigger immediately

### Test Phone Detection
- Show your phone to the camera
- Alert should trigger for "phone_detected"

## Common Issues

### Backend won't start
- Ensure Python 3.9+ is installed: `python --version`
- Check if virtual environment is activated (you should see `(venv)` in terminal)
- Try: `pip install --upgrade pip` then reinstall requirements

### Frontend won't start
- Ensure Node.js 18+ is installed: `node --version`
- Delete `node_modules` and run `npm install` again
- Check if port 3000 is already in use

### Camera not working
- Grant browser permissions for camera/microphone
- Try a different browser (Chrome recommended)
- Ensure no other app is using the camera

### WebSocket connection failed
- Verify backend is running on port 8000
- Check browser console for errors
- Ensure no firewall is blocking connections

## Development Tips

### Hot Reload
- Backend: Automatically reloads on file changes
- Frontend: Automatically reloads on file changes

### Viewing Logs
- Backend logs appear in the terminal running the backend
- Frontend logs: Open browser DevTools (F12) → Console

### API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI)

## Next Steps

1. Read the full README.md for detailed documentation
2. Customize settings in `backend/.env`
3. Explore the code in `backend/app/ml_models/`
4. Build additional features!

## Project Structure Quick Reference

```
backend/
├── app/
│   ├── ml_models/        # AI detection models
│   ├── services/         # Business logic
│   ├── api/routes/       # API endpoints
│   └── main.py          # Entry point

frontend/
├── app/
│   ├── interview/       # Interview page
│   ├── dashboard/       # Dashboard page
│   └── page.tsx         # Home page
```

## Resources

- FastAPI Docs: https://fastapi.tiangolo.com
- Next.js Docs: https://nextjs.org/docs
- MediaPipe: https://developers.google.com/mediapipe
- YOLO: https://docs.ultralytics.com

Happy Coding!
