import pytest
from fastapi.testclient import TestClient
from app.main import app
import app.routers.websocket as ws_module
import app.services.user_service as service_module
client = TestClient(app)


# --- Testing WebSocket connection with no token ---

def test_websocket_without_token():

    with pytest.raises(Exception) as error:
        with client.websocket_connect("/ws"):
            pass

    assert error.value.code == 1008


# --- Testing WebSocket connection with invalid token ---

def test_websocket_with_invalid_token(monkeypatch):
    monkeypatch.setattr(ws_module, "decode_access_token", lambda token: None)

    with pytest.raises(Exception) as error:
        with client.websocket_connect("/ws?token=invalid_token"):
            pass

    assert error.value.code == 1008


def test_invalid_payload(monkeypatch):
    #---Creating
    monkeypatch.setattr(
        ws_module,
        "decode_access_token",
        lambda token: None
    )

    with pytest.raises(Exception) as error:
        with client.websocket_connect("/ws?token=valid_token"):
            pass

    assert error.value.code == 1008
        


def test_user_not_found(monkeypatch):
    #---Creating a fake valid token---
    monkeypatch.setattr(ws_module, "decode_access_token", lambda token: {"sub": "naw@gmail.com"})

    #---Creating no email---
    monkeypatch.setattr(ws_module, "get_user_by_email", lambda email: None)

    #--Creating the test protocol--
    with pytest.raises(Exception) as error:
        with client.websocket_connect("/ws?token=validtoken"):
            pass
    assert error.value.code == 1008




# --- Testing WebSocket receiving a message ---

def test_receive_text(monkeypatch):

    class FakeUser:
        id = 1
        email = "test@example.com"

    # Pretend the token is valid
    monkeypatch.setattr(
        ws_module, "decode_access_token", lambda token: {
            "sub": "test@example.com"
        }
    )
    monkeypatch.setattr(
    ws_module,
    "get_user_by_email",
    lambda email: FakeUser()
)
    # Store messages received by our fake handler
    received_messages = []

    async def fake_handle_message(user_id, message):
        received_messages.append((user_id, message))

    # Replace the real handler with our fake handler
    monkeypatch.setattr(
        ws_module,
        "handle_message",
        fake_handle_message
    )

    # We still need the database lookup to return our fake user.
    # This part depends on how your current database is configured.

    with client.websocket_connect("/ws?token=valid_token") as websocket:
        
        websocket.send_text("hello")

    assert received_messages == [
        (1, "hello")
    ]



#---Creating the test for authentication
def test_auth_sucessful(monkeypatch):
    class FakeUser():
        id= 5
        email= "today@gmail.com"

    #---Ceating a fake valid token---
    monkeypatch.setattr(ws_module, "decode_access_token", lambda token: {"sub": "today@gmail.com"})

    #---Creating a fake valid user---
    monkeypatch.setattr(ws_module, "get_user_by_email", lambda email: FakeUser())
    with client.websocket_connect("/ws?token=valid_token") as websocket:
        assert websocket is not None


#---Creating test receive multiple message---
def test_receive_multiple_messages(monkeypatch):
    #--Creating the fake user gotten through session---
    class FakeUser():
        id= 7
        email= "now@gmail.com"

    #---Creating the fake valid token---
    monkeypatch.setattr(ws_module, "decode_access_token", lambda token: {"sub": "now@gmail.com"})

    #---Creating the fake valid user---
    monkeypatch.setattr(ws_module, "get_user_by_email", lambda email: FakeUser())

    received_message= []

    async def fake_handle_message(user_id, message):
        received_message.append((user_id, message))

    monkeypatch.setattr(ws_module, "handle_message", fake_handle_message)


    with client.websocket_connect("/ws?token=valid_token") as websocket:
        websocket.send_text("hello")
        websocket.send_text("wow")
        websocket.send_text("send me my money")


    assert received_message == [(7, "hello"),
                                (7, "wow"),
                                (7, "send me my money")]
