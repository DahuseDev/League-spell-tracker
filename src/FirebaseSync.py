import time
import firebase_admin
import re
from firebase_admin import credentials,db
import os
from dotenv import load_dotenv
load_dotenv()
class FirebaseSync:
    _instance = None
    match_id: str = ""
    DB_URL = os.getenv("FIREBASE_DB_URL")
    DEFAULT_DB_URL = "https://leaguespelltracker-default-rtdb.europe-west1.firebasedatabase.app/"
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                cred = credentials.Certificate("src/firebaseKey.json")
                firebase_admin.initialize_app(cred, {
                    "databaseURL": cls.DB_URL or cls.DEFAULT_DB_URL
                })
            except Exception as e:
                print(f"[FIREBASE] Initialization error: {e}")
                pass
        return cls._instance
    # "/Sett fanatic#SETTilouteur84#biteMaren Gain#GarenPulz Say Run#EUWDekyl#EUW"
    def setMatchID(self, match_id):
        newmatch_id = self._sanitize_key(match_id)
        if self.match_id != newmatch_id:
            self.match_id = newmatch_id
            ref = db.reference(f"/{self.match_id}")
            ref.listen(self.on_snapshot)
            print(f"[FIREBASE] Listening to match ID: {self.match_id}")

    def _sanitize_key(self, key: str) -> str:
        """Sanitize a string to be safe as a RTDB key segment.
        Firebase RTDB keys cannot contain '.', '#', '$', '[', or ']'.
        Also replace '/' to avoid accidental nested paths from user input.
        """
        if not isinstance(key, str):
            key = str(key or "")
        # replace invalid characters with underscore
        return re.sub(r'[.\#\$\[\]/]', '_', key)

    def listen(self, callback):
        print("[FIREBASE] Setting on_snapshot callback.")
        self.on_snapshot = callback

    def mark_spell_used(self, champ, spell):
        timestamp = int(time.time())  # Unix time in seconds
        spell = self.sanitize_spell(spell)
        print(f"[FIREBASE] Marking spell used: {champ} - {spell} at {timestamp}")
        ref = db.reference(f"/{self.match_id}/{champ}/{spell}")
        ref.set({"usedAt": timestamp})

    def reset_spell(self, champ, spell):
        timestamp = int(time.time()) - 600
        spell = self.sanitize_spell(spell)
        print(f"[FIREBASE] Resetting spell: {champ} - {spell}")
        ref = db.reference(f"/{self.match_id}/{champ}/{spell}")
        ref.set({"usedAt": timestamp})

    def sanitize_spell(self, spell_name: str) -> str:
        if spell_name in self.duplicatedSpells:
            spell_name = self.duplicatedSpells[spell_name]
        return spell_name
    
    duplicatedSpells = {
        "Unleashed Teleport": "Teleport",
        "Unleashed Smite": "Smite",
        "Hexflash": "Flash",
    }