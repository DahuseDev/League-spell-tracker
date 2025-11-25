import requests
from PySide6.QtCore import QThread, Signal
from typing import List, Dict, Optional
from src.commons import is_in_game

# ======================= LOCAL LIVE CLIENT WORKER =============================
class LocalSyncWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def _fetch_allgamedata(self) -> Dict:
        if not is_in_game():
            raise RuntimeError("Not in game (Live Client API gamestats endpoint not reachable).")
        url_http = "http://127.0.0.1:2999/liveclientdata/allgamedata"
        url_https = "https://127.0.0.1:2999/liveclientdata/allgamedata"
        try:
            r = requests.get(url_http, timeout=2)
            if r.status_code == 200: return r.json()
        except Exception: pass
        try:
            r = requests.get(url_https, timeout=2, verify=False)
            if r.status_code == 200: return r.json()
        except Exception: pass
        raise RuntimeError("Not in game (Live Client API not reachable on 127.0.0.1:2999).")

    def run(self):
        try:
            data = self._fetch_allgamedata()
            all_players = data.get("allPlayers", [])
            if not all_players: raise RuntimeError("Live Client API returned no players yet (still loading).")
            active = data.get("activePlayer", {})
            my_name = active.get("summonerName", "")
            my_team: Optional[str] = None
            for p in all_players:
                if p.get("summonerName", "") == my_name:
                    my_team = p.get("team"); break
            if my_team is None and all_players:
                my_team = all_players[0].get("team", "ORDER")
            enemy = [p for p in all_players if p.get("team") != my_team]
            result: List[Dict[str, List[str]]] = []
            for p in enemy:
                champ = p.get("championName", "Unknown") or "Unknown"
                spells = []
                ss = p.get("summonerSpells", {})
                for key in ("summonerSpellOne", "summonerSpellTwo"):
                    if key in ss:
                        spells.append(ss[key].get("displayName", "Unknown") or "Unknown")
                spells = (spells + ["", ""])[:2]
                result.append({"champion": champ, "spells": spells})
            #if not result: raise RuntimeError("Could not determine enemy team (maybe game mode not 5v5?).")
            self.finished_ok.emit(result[:5])
        except Exception as e:
            self.failed.emit(str(e))