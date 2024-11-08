import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.user_routers import auth_router
from app.api.invoice_routers import router as invoice_router
from app.core.config import init_db, cleanup_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for FastAPI application startup and shutdown events.
    """
    # Startup
    try:
        print("Starting up database connection...")
        await init_db()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

    yield

    # Shutdown
    try:
        print("Cleaning up database connections...")
        await cleanup_db()
        print("Cleanup completed!")
    except Exception as e:
        print(f"Error during cleanup: {e}")


app = FastAPI(
    title="Invoice API",
    description="API for managing invoices",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
origins = [
    "http://localhost:3000",  # React default port
    "http://localhost:8000",  # FastAPI default port
    "http://127.0.0.1:8000",  # Alternative localhost
    # Add other origins as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # More secure than ["*"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Routers
app.include_router(invoice_router)
app.include_router(auth_router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint to check API status"""
    return {
        "message": "Invoice API is running",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected"
    }


if __name__ == "__main__":
    uvicorn.run(
        "run:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="debug",
        workers=1  # Убрана запятая
    )  # Комментарий перенесен за пределы параметров