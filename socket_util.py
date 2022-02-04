'''WebSocket Utility Module'''

from typing import List
import fastapi as _fastapi

class ConnectionManager:
    '''
        WebSocket connection Manager
        >>>   connect
        >>>   disconnect
        >>>   broadcast
    '''
    def __init__(self):
        self.active_conns: List[_fastapi.WebSocket] = []
    
    async def connect(self, incoming: _fastapi.WebSocket):
        await incoming.accept()
        self.active_conns.append(incoming)

    async def disconnect(self, outgoing):
        self.active_conns.remove(outgoing)
    
    async def broadcast(self, data):
        for conn in self.active_conns:
            await conn.send_text(data)
