from fastapi import WebSocket
from typing import Dict, List
import json

class ConnectionManager:
    def __init__(self):
        # Mapeo de usuario_id -> Lista de WebSockets (por si tiene varias pestañas abiertas)
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"DEBUG Socket: Usuario {user_id} conectado.")

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"DEBUG Socket: Usuario {user_id} desconectado.")

    async def send_personal_message(self, message: dict, user_id: int):
        """Envía un mensaje directo a un usuario específico en tiempo real."""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Si falla, probablemente la conexión se cerró abruptamente
                    pass

manager = ConnectionManager()
