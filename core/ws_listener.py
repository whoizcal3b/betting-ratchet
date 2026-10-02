import asyncio
import json
import time
from typing import Dict, Any, Callable, Optional
import config

class VirtusTecWsListener:
    def __init__(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.callback = callback
        self.resolved_events_queue = asyncio.Queue()
        self.latest_wallet_balance = None
        self.last_msg_timestamp = time.time()
        self.connected_url = None

    def is_stream_alive(self, max_idle_seconds: float = 60.0) -> bool:
        """Returns True if WebSocket has received active frames within max_idle_seconds."""
        return (time.time() - self.last_msg_timestamp) < max_idle_seconds

    def attach_to_page(self, page):
        def on_websocket(ws):
            if "virtual-proxy.virtustec.com" in ws.url:
                print(f"[WS-LISTENER] Attached to VirtusTec feed: {ws.url}")
                self.connected_url = ws.url
                self.last_msg_timestamp = time.time()
                ws.on("framereceived", self._on_frame_received)

        page.on("websocket", on_websocket)

    def _on_frame_received(self, payload: str):
        self.last_msg_timestamp = time.time()
        try:
            if not isinstance(payload, str):
                return

            if "RESOLVED" not in payload and "wallet" not in payload.lower():
                return

            data = json.loads(payload)
            res = data.get("res", {})
            body = res.get("body")

            if isinstance(body, list) and len(body) > 0:
                first_item = body[0]
                if isinstance(first_item, dict) and first_item.get("serverStatus") == "RESOLVED":
                    eblock_id = first_item.get("eBlockId")
                    playlist_id = first_item.get("playlistId")
                    events = first_item.get("events", [])

                    if events and isinstance(events[0], dict):
                        ev = events[0]
                        res_data = ev.get("result", {})
                        won_markets = res_data.get("wonMarkets", [])
                        final_order = res_data.get("data", {}).get("finalOrder", [])

                        resolved_event = {
                            "type": "RACE_RESOLVED",
                            "eblock_id": eblock_id,
                            "playlist_id": playlist_id,
                            "final_order": final_order,
                            "won_markets": won_markets,
                            "raw_timestamp": first_item.get("eventTime")
                        }

                        # Only print in console if it's our Bristol playlist (23100) or Speedway 4-runner
                        is_bristol = (playlist_id == config.BRISTOL_PLAYLIST_ID) or (len(final_order) == 4 and any("place_" in m for m in won_markets))
                        if is_bristol:
                            print(f"\n[WS-LISTENER] SPEEDWAY BRISTOL RESOLVED! Race #{eblock_id} | Winning Markets: {won_markets} | Finish Order: {final_order}")

                        self.resolved_events_queue.put_nowait(resolved_event)

                        if self.callback:
                            self.callback(resolved_event)

        except Exception as e:
            pass

    async def wait_for_resolution(self, target_eblock_id: Optional[int] = None, timeout: float = 120.0) -> Optional[Dict[str, Any]]:
        """Asynchronously waits for a RESOLVED packet matching our target race ID."""
        start_time = asyncio.get_event_loop().time()
        while True:
            remaining = timeout - (asyncio.get_event_loop().time() - start_time)
            if remaining <= 0:
                print(f"[WS-LISTENER] Timeout ({timeout}s) waiting for race resolution.")
                return None

            try:
                event = await asyncio.wait_for(self.resolved_events_queue.get(), timeout=remaining)
                # Match specific race eBlockId
                if target_eblock_id is None or event.get("eblock_id") == target_eblock_id:
                    return event
                else:
                    # Not our race (football, dogs, horses), discard and keep waiting
                    continue
            except asyncio.TimeoutError:
                return None
