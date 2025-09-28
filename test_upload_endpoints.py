#!/usr/bin/env python3
"""
Standalone test for the three specialized upload endpoints
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Create simple FastAPI app just for testing upload endpoints
app = FastAPI(
    title="Upload Endpoints Test",
    description="Testing three specialized upload endpoints",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
try:
    from routers.upload_docs import router as docs_router
    app.include_router(docs_router, prefix="/upload", tags=["Upload Docs"])
    print("✅ Project documents router loaded")
except Exception as e:
    print(f"❌ Failed to load docs router: {e}")

try:
    from routers.upload_smeta import router as smeta_router
    app.include_router(smeta_router, prefix="/upload", tags=["Upload Estimates"])
    print("✅ Estimates router loaded")
except Exception as e:
    print(f"❌ Failed to load smeta router: {e}")

try:
    from routers.upload_drawings import router as drawings_router
    app.include_router(drawings_router, prefix="/upload", tags=["Upload Drawings"])
    print("✅ Drawings router loaded")
except Exception as e:
    print(f"❌ Failed to load drawings router: {e}")

@app.get("/")
async def root():
    return {
        "service": "Upload Endpoints Test",
        "endpoints": {
            "docs": "/docs",
            "upload_docs": "/upload/docs",
            "upload_smeta": "/upload/smeta", 
            "upload_drawings": "/upload/drawings"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "endpoints_loaded": len(app.routes)}

if __name__ == "__main__":
    print("🚀 Starting upload endpoints test server...")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")