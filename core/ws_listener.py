import asyncio
import json
import time
from typing import Dict, Any, Callable, Optional, List
import config

class VirtusTecWsListener:
    def __init__(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.callback = callback
        self.resolved_events_queue = asyncio.Queue()
        self.resolved_cache: Dict[Any, Dict[str, Any]] = {}
        self._new_resolution_event = asyncio.Event()
        self.latest_wallet_balance = None
        self.last_msg_timestamp = time.time()
        self.connected_url = None
        self.is_connected = False
        self._attached_page = None

    def is_stream_alive(self, max_idle_seconds: float = 60.0) -> bool:
        """Returns True if WebSocket is connected and has received active frames within max_idle_seconds."""
        if not self.is_connected:
            return False
        return (time.time() - self.last_msg_timestamp) < max_idle_seconds

    def attach_to_page(self, page):
        """Attaches WebSocket listeners to page, ensuring active listener on page reloads."""
        if self._attached_page == page and self.is_connected:
            return
        self._attached_page = page

        def on_websocket(ws):
            if "virtual-proxy.virtustec.com" in ws.url:
                print(f"[WS-LISTENER] Attached to VirtusTec feed: {ws.url}")
                self.connected_url = ws.url
                self.is_connected = True
                self.last_msg_timestamp = time.time()
                
                ws.on("framereceived", self._on_frame_received)
                ws.on("close", lambda: self._on_ws_close())

        page.on("websocket", on_websocket)

    def _on_ws_close(self):
        print("[WS-LISTENER] VirtusTec WebSocket closed by remote server.")
        self.is_connected = False

    def _on_frame_received(self, payload: str):
        self.last_msg_timestamp = time.time()
        self.is_connected = True
        try:
            if not isinstance(payload, str):
                return

            if "RESOLVED" not in payload and "wallet" not in payload.lower():
                return

            data = json.loads(payload)

            # Robust payload extraction: handle batch arrays across different VirtusTec wrapper schemas
            items_list: List[Dict[str, Any]] = []
            if isinstance(data, list):
                items_list = data
            elif isinstance(data, dict):
                res = data.get("res")
                if isinstance(res, dict) and isinstance(res.get("body"), list):
                    items_list = res.get("body", [])
                elif isinstance(data.get("body"), list):
                    items_list = data.get("body", [])
                elif isinstance(data.get("events"), list):
                    items_list = data.get("events", [])

            # Iterate through ALL items in the batch (never only body[0])
            for item in items_list:
                if not isinstance(item, dict):
                    continue

                server_status = item.get("serverStatus") or item.get("status")
                if server_status == "RESOLVED":
                    eblock_id = item.get("eBlockId") or item.get("eblock_id") or item.get("id")
                    playlist_id = item.get("playlistId")
                    events = item.get("events", [])

                    if events and isinstance(events[0], dict):
                        ev = events[0]
                        res_data = ev.get("result", {})
                        won_markets = res_data.get("wonMarkets", [])
                        raw_order = res_data.get("data", {}).get("finalOrder", [])
                        final_order = [str(x) for x in raw_order]

                        resolved_event = {
                            "type": "RACE_RESOLVED",
                            "eblock_id": int(eblock_id) if str(eblock_id).isdigit() else eblock_id,
                            "playlist_id": playlist_id,
                            "final_order": final_order,
                            "won_markets": won_markets,
                            "raw_timestamp": item.get("eventTime")
                        }

                        # Store in cache indexed by both int and string race_id for instant retrieval
                        if eblock_id is not None:
                            self.resolved_cache[str(eblock_id)] = resolved_event
                            if str(eblock_id).isdigit():
                                self.resolved_cache[int(eblock_id)] = resolved_event

                        # Keep cache bounded to last 500 records
                        if len(self.resolved_cache) > 1000:
                            old_keys = list(self.resolved_cache.keys())[:200]
                            for k in old_keys:
                                self.resolved_cache.pop(k, None)

                        # Signal waiting workers
                        self._new_resolution_event.set()
                        self.resolved_events_queue.put_nowait(resolved_event)

                        is_bristol = (playlist_id == config.BRISTOL_PLAYLIST_ID) or (len(final_order) == 4 and any("place_" in m for m in won_markets))
                        if is_bristol:
                            print(f"\n[WS-LISTENER] SPEEDWAY BRISTOL RESOLVED! Race #{eblock_id} | Final Order: {final_order} | Winning Markets: {won_markets}")

                        if self.callback:
                            try:
                                self.callback(resolved_event)
                            except Exception:
                                pass

        except Exception as e:
            pass

    async def wait_for_resolution(self, target_eblock_id: Optional[Any] = None, timeout: float = 90.0) -> Optional[Dict[str, Any]]:
        """
        Asynchronously waits for a RESOLVED packet matching target race ID.
        Uses a non-destructive cache check so events are NEVER missed or discarded regardless of order.
        """
        # 1. Instant check: Already in cache?
        if target_eblock_id is not None:
            if str(target_eblock_id) in self.resolved_cache:
                return self.resolved_cache[str(target_eblock_id)]
            if str(target_eblock_id).isdigit() and int(target_eblock_id) in self.resolved_cache:
                return self.resolved_cache[int(target_eblock_id)]

        start_time = time.time()
        while True:
            remaining = timeout - (time.time() - start_time)
            if remaining <= 0:
                print(f"[WS-LISTENER] Timeout ({timeout:.0f}s) waiting for race #{target_eblock_id} resolution.")
                return None

            try:
                # Wait for next resolution signal or tick every 2 seconds
                await asyncio.wait_for(self._new_resolution_event.wait(), timeout=min(remaining, 2.0))
                self._new_resolution_event.clear()
            except asyncio.TimeoutError:
                pass

            # Check cache upon wakeup
            if target_eblock_id is not None:
                if str(target_eblock_id) in self.resolved_cache:
                    return self.resolved_cache[str(target_eblock_id)]
                if str(target_eblock_id).isdigit() and int(target_eblock_id) in self.resolved_cache:
                    return self.resolved_cache[int(target_eblock_id)]
            else:
                if not self.resolved_events_queue.empty():
                    return self.resolved_events_queue.get_nowait()
