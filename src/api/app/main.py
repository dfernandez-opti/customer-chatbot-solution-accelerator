import asyncio
import logging
import os
import sys

# Inicializar Application Insights antes de otros imports (para telemetría y alertas en Defender/Monitor)
_ai_conn = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "").strip()
if _ai_conn:
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        configure_azure_monitor()
    except Exception as _e:
        logging.basicConfig(level=logging.INFO, force=True)
        logging.getLogger(__name__).warning("Application Insights no inicializado: %s", _e)

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging BEFORE importing other modules
# This ensures all loggers created in imported modules inherit this configuration
logging.basicConfig(
    level=logging.INFO,
    force=True,  # Force reconfiguration even if logging was already configured
)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
    logging.WARNING
)
logging.getLogger("app.routers.auth").setLevel(logging.WARNING)
logging.getLogger("app.auth").setLevel(logging.WARNING)
# Handle both local debugging and Docker deployment
try:
    # Try relative imports first (for Docker)
    from .auth import get_current_user
    from .config import settings, has_content_safety_config
    from .routers import auth, cart, chat, products
except ImportError:
    # Fall back to absolute imports (for local debugging)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.auth import get_current_user
    from app.config import settings
    from app.routers import auth, cart, chat, products

# Get logger for this module (logging already configured above)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="E-commerce Chat API with AI-powered customer support",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS (incl. app directa y sandbox Azure Portal si está en ALLOWED_ORIGINS_STR)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(chat.router)
app.include_router(cart.router)
try:
    from .routers import security, opportunities
    app.include_router(security.router)
    app.include_router(opportunities.router)
except ImportError:
    from app.routers import security, opportunities
    app.include_router(security.router)
    app.include_router(opportunities.router)


@app.on_event("startup")
async def startup_event():
    """Log Content Safety status al arrancar"""
    if has_content_safety_config():
        logger.info("Content Safety: ENABLED (moderación activa)")
    else:
        logger.info(
            "Content Safety: disabled (configure CONTENT_SAFETY_ENABLED, ENDPOINT, KEY en backend)"
        )


@app.get("/")
async def read_root():
    """Root endpoint with API information"""
    return {
        "message": f"Welcome to {settings.app_name}!",
        "version": settings.app_version,
        "docs": "/docs",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected" if settings.cosmos_db_endpoint else "not_configured",
        "openai": "configured" if settings.azure_openai_endpoint else "not_configured",
        "auth": "configured" if settings.azure_client_id else "not_configured",
        "content_safety": "enabled" if has_content_safety_config() else "disabled",
        "version": "minimal",
    }


@app.get("/debug/content-safety")
async def debug_content_safety():
    """Diagnóstico de Content Safety: estado y prueba rápida"""
    if not has_content_safety_config():
        return {
            "configured": False,
            "message": "Configure CONTENT_SAFETY_ENABLED, CONTENT_SAFETY_ENDPOINT, CONTENT_SAFETY_KEY en el backend",
            "endpoint_set": bool(settings.content_safety_endpoint),
            "key_set": bool(settings.content_safety_key),
            "enabled": settings.content_safety_enabled,
        }
    # Prueba con texto seguro
    try:
        try:
            from .services.content_safety import check_text_safety
        except ImportError:
            from app.services.content_safety import check_text_safety

        is_safe, reason = await asyncio.to_thread(
            check_text_safety,
            settings.content_safety_endpoint,
            settings.content_safety_key,
            "Hola, quiero información de productos OPTI",
        )
        return {
            "configured": True,
            "test_passed": True,
            "test_result": "safe" if is_safe else f"rejected: {reason}",
        }
    except Exception as e:
        return {
            "configured": True,
            "test_passed": False,
            "error": str(e),
        }


@app.get("/debug/auth")
async def debug_auth(request: Request):
    """Debug endpoint to see authentication headers and current user info"""
    try:
        headers = dict(request.headers)
        current_user = await get_current_user(request)

        return {
            "headers": {
                k: v
                for k, v in headers.items()
                if "x-ms-" in k.lower() or "authorization" in k.lower()
            },
            "all_headers_count": len(headers),
            "current_user": current_user,
            "debug_info": {
                "has_principal_id": "x-ms-client-principal-id" in headers,
                "has_principal": "x-ms-client-principal" in headers,
                "has_principal_name": "x-ms-client-principal-name" in headers,
                "is_guest": current_user.get("is_guest", "unknown"),
            },
        }
    except Exception as e:
        return {"error": str(e), "headers": dict(request.headers)}


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail, "error": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": "An unexpected error occurred",
        },
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", host=settings.host, port=settings.port, reload=settings.debug
    )
