## 🧙 League Spell Tracker

This project began as a fun experiment to recreate the spell cooldown overlay feature that Riot removed after disabling tools like Blitz and Porofessor.

Riot claimed those overlays gave players an **unfair advantage**. Ironically, as this little project shows, anyone can rebuild the same functionality in about 10 minutes with GPT - the only difference now is that you'll be **the only one** with access to that information.
So in removing Blitz and Porofessor, Riot may have actually made things more exclusive, not less.

## ⚙️ How to Use

### Build local assets
Run League Assets builder.py to cache champion, spell, and ultimate icons locally.

You only need to do this when new champions or visual updates are added.

## Installation
To install the necessary dependencies, run:

```
pip install -r requirements.txt
```

## Usage
To run the application, execute the following command:

```
python src/SpellTracker.py
```

## Building the Release
To generate a standalone executable for the application, you can use the provided scripts:

- For Windows:
  ```
  build.bat
  ```

### Adjust settings

⚙️ opens sliders for scale and transparency.

🔒 / 🔓 toggles overlay lock, preventing accidental movement.

Left-click a spell to start its cooldown timer.

Right-click resets the spell back to "up".

To enable Team-sync you must provide a Firebase Realtime Database URL and credentials.

1. Create a Firebase project at https://console.firebase.google.com/.
2. Enable Realtime Database and set rules or authentication as needed.
3. Obtain your Realtime Database URL (something like `https://your-project-id-default-rtdb.firebaseio.com`) from the Database panel and paste it in your .env file as:
FIREBASE_DB_URL=https://YOURDATABASEHERE.firebasedatabase.app/
4. In the Firebase console, open Settings > Service Accounts, click Generate New Private Key, then confirm by clicking Generate Key.
5. Store the JSON downloaded into the /src folder and name it as firebaseKey.json
6. Share the same FIREBASE_DB_URL and firebaseKey.json with your teammates and you are ready to start using the Team-Sync feature


### 🧩 The future of this app
Well, as stated initially, it all started as a fun / meme project to prove a point. Since it's well received by the community I might continue improving and developing the app with the following features:

- [ ] Save user settings (scale, transparency, position)
- [ ] Auto-detect match start and sync automatically
- [ ] Show overlay only when League is focused/fullscreen
- [ ] Polish the UI / visual design
- [ ] Release as a runnable .exe or .vbs for easier use

### Contact
You can reach me on Discord, my handle is `'rioterneeko'`