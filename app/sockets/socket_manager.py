import socketio
import logging

# Cấu hình logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")
logger = logging.getLogger(__name__)

# Khởi tạo Socket.IO server, không cần cors_allowed_origins vì FastAPI đã xử lý CORS
sio = socketio.AsyncServer(async_mode='asgi')

def setup_socket_events():
    @sio.event
    async def connect(sid, environ):
        logger.info(f"Client {sid} connected")

    @sio.event
    async def disconnect(sid):
        logger.info(f"Client {sid} disconnected")