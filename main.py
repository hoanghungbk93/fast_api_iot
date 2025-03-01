import sentry_sdk
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import ro_gps, ro_users, ro_pair, ro_chromecast, ro_ui
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
import logfire
from fastapi.middleware.cors import CORSMiddleware
import socketio
from app.sockets.socket_manager import sio, setup_socket_events
from app.config.config import LOGFIRE_TOKEN, SENTRY_DSN

# Initialize Sentry
sentry_sdk.init(
    dsn=SENTRY_DSN,
    traces_sample_rate=1.0
)

app = FastAPI()

# Add Sentry middleware
app.add_middleware(SentryAsgiMiddleware)
logfire.configure(token=LOGFIRE_TOKEN)
logfire.instrument_fastapi(app, capture_headers=True)

# CORS Middleware (giữ nguyên)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tích hợp Socket.IO
sio_app = socketio.ASGIApp(sio)
app.mount("/socket.io", sio_app)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Đăng ký router
app.include_router(ro_users.router)
app.include_router(ro_gps.router)
app.include_router(ro_pair.router)
app.include_router(ro_chromecast.router)
app.include_router(ro_ui.router)
# Setup Socket.IO events
setup_socket_events()

# Hàm chạy server
if __name__ == "__main__":
    import uvicorn
    local_ip = "0.0.0.0"  # Hoặc dùng get_local_ip() nếu cần
    print(f"\nHandshake server running at:")
    print(f"http://{local_ip}:8000")
    print("\nTest code: 1234")
    uvicorn.run("app.main:app", host=local_ip, port=8000, reload=True)