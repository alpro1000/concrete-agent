"""
Concrete Agent - Main Application Entry Point
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="Concrete Agent",
    description="AI-powered construction planning and analysis system",
    version="0.1.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint"""
    return """
    <html>
        <head>
            <title>Concrete Agent</title>
        </head>
        <body>
            <h1>Welcome to Concrete Agent</h1>
            <p>AI-powered construction planning and analysis system</p>
            <ul>
                <li><a href="/docs">API Documentation</a></li>
                <li><a href="/redoc">ReDoc</a></li>
            </ul>
        </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
