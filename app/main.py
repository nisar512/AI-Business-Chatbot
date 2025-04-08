from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from contextlib import asynccontextmanager
from core.config import settings
from db.session import get_db, engine
from db.elasticsearch import elastic_client
from tasks.selenium_tasks import SeleniumService
from routes.api.v1 import users, search
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup events
    logger.info("Starting application...")
    
    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Check Elasticsearch connection
    if not await elastic_client.ping():
        raise RuntimeError("Could not connect to Elasticsearch")
    
    # Initialize Selenium service
    app.state.selenium_service = SeleniumService()
    
    yield
    
    # Shutdown events
    logger.info("Shutting down application...")
    await elastic_client.close()
    await engine.dispose()
    app.state.selenium_service.driver.quit()

app = FastAPI(
    title="My Professional Backend",
    description="API Backend with FastAPI, PostgreSQL, Elasticsearch, and Selenium",
    version="1.0.0",
    lifespan=lifespan,
    dependencies=[Depends(oauth2_scheme)]
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

# # Include routers
# app.include_router(users.router, prefix="/api/v1", tags=["users"])
# app.include_router(search.router, prefix="/api/v1", tags=["search"])

# Health check endpoint
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {
        "status": "ok",
        "database": "ok" if await database_health_check() else "unhealthy",
        "elasticsearch": "ok" if await elasticsearch_health_check() else "unhealthy"
    }

async def database_health_check():
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

async def elasticsearch_health_check():
    try:
        return await elastic_client.ping()
    except Exception as e:
        logger.error(f"Elasticsearch health check failed: {e}")
        return False

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)