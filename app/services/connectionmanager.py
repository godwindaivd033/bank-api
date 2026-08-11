from fastapi import WebSocket




class ConnectionManager:
    def __init__(self):
        self.active_connections = {} #--creating an empty dictionary to safe websocket connected users---

    #--Creating the method that allows the user to connect to the websocket---
    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        #---adding the new connection to the empty dictionary---
        self.active_connections[user_id] = websocket

    #---Creating the method that allows the user to disconnect from the websocket---
    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)

    #---Creating the method that allows for sending of messages---
    async def send_to_user(self, user_id: int, messages: str):
        connection = self.active_connections.get(user_id)

        if connection:
            await connection.send_text(messages)












manager= ConnectionManager()