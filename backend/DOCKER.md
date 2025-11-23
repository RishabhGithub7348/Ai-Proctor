# Docker Setup for AI Proctor Backend

## Prerequisites
- Docker installed on your system
- Docker Desktop (recommended for Windows/Mac)

## Quick Start

### 1. Build the Docker Image

```bash
cd backend
docker build -t ai-proctor-backend .
```

### 2. Run the Container

**Basic run:**
```bash
docker run -p 8000:8000 ai-proctor-backend
```

**With Gemini AI verification (optional - disabled by default):**
```bash
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=your-api-key-here \
  -e ENABLE_AI_VERIFICATION=true \
  ai-proctor-backend
```

### 3. Verify it's Running

Open your browser and go to:
- http://localhost:8000 - Should show "AI Proctor API is running"
- http://localhost:8000/health - Health check endpoint

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8000 | Server port |
| `HOST` | 0.0.0.0 | Server host |
| `DEBUG` | false | Enable debug mode |
| `GEMINI_API_KEY` | - | Gemini API key for AI verification |
| `ENABLE_AI_VERIFICATION` | false | Enable AI-based violation verification |
| `AI_VERIFICATION_CONFIDENCE_THRESHOLD` | 0.7 | AI confidence threshold |

## Useful Commands

**Stop the container:**
```bash
docker stop $(docker ps -q --filter ancestor=ai-proctor-backend)
```

**View logs:**
```bash
docker logs -f $(docker ps -q --filter ancestor=ai-proctor-backend)
```

**Remove the image:**
```bash
docker rmi ai-proctor-backend
```

## Troubleshooting

### Port already in use
```bash
docker run -p 8001:8000 ai-proctor-backend
```
Then access at http://localhost:8001

### Check container status
```bash
docker ps -a
```

### Enter container shell
```bash
docker run -it ai-proctor-backend /bin/bash
```
