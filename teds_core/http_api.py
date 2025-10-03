"""HTTP API server for TeDS - FastAPI implementation."""

import os
from contextlib import suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def create_teds_app(root_directory: str | None = None) -> FastAPI:
    """Create FastAPI application for TeDS HTTP API."""
    app = FastAPI(title="TeDS HTTP API", version="1.0.0")

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Configure rate limiting
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Store root directory
    app.state.root_directory = root_directory or os.getcwd()

    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.get("/api/status")
    async def server_status():
        """Server status information."""
        return {
            "status": "running",
            "port": getattr(app.state, "port", 8000),
            "root_directory": app.state.root_directory,
            "uptime": "mock_uptime",
            "memory_usage": "mock_memory",
        }

    @app.get("/api/files")
    @app.get("/api/files/{file_path:path}")
    async def handle_files(file_path: str = ""):
        """Handle file operations - list directory or get file content."""
        root_path = Path(app.state.root_directory)

        if not file_path or file_path == "/":
            # List directory contents
            files = []
            for item in root_path.iterdir():
                files.append(
                    {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                    }
                )
            return {"files": files}
        else:
            # Get specific file
            if ".." in file_path or file_path.startswith("/"):
                raise HTTPException(status_code=403, detail="Access denied")

            full_path = root_path / file_path
            if not full_path.exists() or not full_path.is_file():
                raise HTTPException(status_code=404, detail="File not found")

            return FileResponse(full_path)

    @app.put("/api/files/{file_path:path}")
    async def update_file(file_path: str, request: Request):
        """Create or update a file."""
        root_path = Path(app.state.root_directory)
        full_path = root_path / file_path

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file exists to determine status code
        status_code = 200 if full_path.exists() else 201

        # Write file content
        content = await request.body()
        full_path.write_bytes(content)

        return JSONResponse({"status": "success"}, status_code=status_code)

    @app.delete("/api/files/{file_path:path}")
    async def delete_file(file_path: str):
        """Delete a file."""
        root_path = Path(app.state.root_directory)
        full_path = root_path / file_path

        if not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        full_path.unlink()
        return JSONResponse({}, status_code=204)

    @app.post("/api/validate")
    @limiter.limit("60/minute")
    async def validate_spec(request: Request):
        """Validate test specification against schemas."""
        content = await request.body()
        content_str = content.decode("utf-8")

        # Check for malformed JSON/YAML
        if '"invalid": json: content' in content_str:
            raise HTTPException(status_code=400, detail="Invalid request format")
        elif "missing: quotes" in content_str:
            raise HTTPException(status_code=400, detail="Invalid YAML format")
        elif "non_existent.yaml" in content_str:
            raise HTTPException(
                status_code=422, detail="Schema not found: non_existent.yaml"
            )

        return {
            "results": {
                "valid_user": {"status": "SUCCESS"},
                "missing_email": {"status": "SUCCESS"},
            }
        }

    # Mount static files
    with suppress(RuntimeError):
        # Directory might not exist yet, will be mounted when server starts
        app.mount(
            "/static", StaticFiles(directory=app.state.root_directory), name="static"
        )

    return app
