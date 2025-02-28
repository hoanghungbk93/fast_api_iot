import socketio

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")

def setup_socket_events():
    @sio.event
    async def connect(sid, environ):
        print(f"Client {sid} connected")

    @sio.event
    async def disconnect(sid):
        print(f"Client {sid} disconnected")