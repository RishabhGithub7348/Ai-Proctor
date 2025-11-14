from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import cv2
import numpy as np

from app.core.config import settings
from app.api.routes import proctoring, session
from app.services.connection_manager import ConnectionManager
from app.services.proctoring_service import ProctoringService

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more details
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Connection manager for WebSocket connections
manager = ConnectionManager()

# Proctoring service (global instance)
proctoring_service = ProctoringService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Starting AI Proctor Backend...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    yield
    logger.info("👋 Shutting down AI Proctor Backend...")


# Initialize FastAPI app
app = FastAPI(
    title="AI Proctor API",
    description="Real-time interview proctoring system with AI-powered monitoring",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(proctoring.router, prefix="/api/v1/proctoring", tags=["proctoring"])
app.include_router(session.router, prefix="/api/v1/session", tags=["session"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "AI Proctor API is running",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time video streaming and proctoring
    """
    await manager.connect(websocket, session_id)
    logger.info(f"Client connected to session: {session_id}")

    # Start the proctoring session
    proctoring_service.start_session(session_id)

    try:
        while True:
            # Receive video frame data from client
            data = await websocket.receive_bytes()
            logger.info(f"Received {len(data)} bytes from session {session_id}")

            # Convert bytes to image
            nparr = np.frombuffer(data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is not None:
                # Process the frame with ML models
                results = proctoring_service.process_frame(image, session_id)

                # Log alerts being sent
                if results.get('alerts'):
                    logger.info(f"🚨 Sending {len(results['alerts'])} ALERTS to frontend for session {session_id}")
                    for alert in results['alerts']:
                        logger.info(f"  📢 Alert: {alert['type']} - {alert['message']} (severity: {alert['severity']})")

                # Send results back to client
                await websocket.send_json({
                    "type": "proctoring_result",
                    "data": results,
                    "session_id": session_id
                })

                # Log violations
                if results.get('violations'):
                    logger.warning(f"Session {session_id}: {len(results['violations'])} violations detected")
                    for violation in results['violations']:
                        logger.warning(f"  - {violation['type']}: {violation['description']}")
            else:
                logger.error(f"Failed to decode image for session {session_id}")

    except WebSocketDisconnect:
        proctoring_service.end_session(session_id)
        manager.disconnect(session_id)
        logger.info(f"Client disconnected from session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error in session {session_id}: {str(e)}")
        proctoring_service.end_session(session_id)
        manager.disconnect(session_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
