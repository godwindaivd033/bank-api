from unittest.mock import AsyncMock
import pytest
from app.services.connectionmanager import ConnectionManager

@pytest.mark.asyncio
async def test_connect():
    manager= ConnectionManager()
    websocket= AsyncMock()

    await manager.connect(1, websocket)
    websocket.accept.assert_awaited_once()
    assert manager.active_connections[1] is websocket


#---Testing for the disconnection---
def test_disconnect():
    manager= ConnectionManager()
    websocket= AsyncMock()
    manager.active_connections[1] = websocket
    manager.disconnect(1)
    assert 1 not in manager.active_connections


#---Testing for sending of message---
@pytest.mark.asyncio
async def test_send_to_user():
    manager= ConnectionManager()
    websocket= AsyncMock()
    await manager.connect(1, websocket)
    await manager.send_to_user(1, "Transaction sucessful")
    websocket.send_text.assert_awaited_once_with("Transaction sucessful")

@pytest.mark.asyncio
async def test_send_to_user_not_connected():
    manager = ConnectionManager()
    # nobody connected — active_connections is empty

    # should not raise, and should be a genuine no-op
    await manager.send_to_user(1, "Should be a no-op")

    assert manager.active_connections == {}