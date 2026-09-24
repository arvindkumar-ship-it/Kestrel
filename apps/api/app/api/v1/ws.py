from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.dependencies import get_ws_ticket_auth
from app.streaming.ws_auth import WSTicketAuth

router = APIRouter(tags=["ws"])


@router.websocket("/ws/alerts")
async def alerts_socket(websocket: WebSocket, ws_auth: WSTicketAuth = Depends(get_ws_ticket_auth)) -> None:
    ticket = websocket.query_params.get("ticket", "")
    principal_id = await ws_auth.redeem_ticket(ticket)
    if principal_id is None:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
