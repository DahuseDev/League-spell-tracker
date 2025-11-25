#!/usr/bin/env python3
#pip install requests tqdm
"""
Download League of Legends champion portraits and ultimate (R) icons
from Riot Data Dragon into:
  - heroes/{champ}.png
  - ultimates/{champ}.png

Run once, then drop these folders next to your overlay app.
"""
import os, re, json, sys, time, unicodedata
from pathlib import Path
from typing import Dict, Tuple, Optional

import requests
from tqdm import tqdm

# -------------------- Config --------------------
LANG = "en_US"  # change if you want another locale’s champion data
OUT_HEROES = Path("res/heroes")
OUT_ULTS   = Path("res/ultimates")
RETRY_COUNT = 3
TIMEOUT = 10

# -------------------- Utils ---------------------
def slugify(name: str) -> str:
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^\w]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def get_json(url: str) -> dict:
    for i in range(RETRY_COUNT):
        try:
            r = requests.get(url, timeout=TIMEOUT)
            if r.ok:
                return r.json()
        except Exception:
            pass
        time.sleep(0.6 * (i + 1))
    raise RuntimeError(f"Failed to GET JSON after retries: {url}")

def download_file(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    for i in range(RETRY_COUNT):
        try:
            with requests.get(url, stream=True, timeout=TIMEOUT) as r:
                if not r.ok:
                    time.sleep(0.6 * (i + 1))
                    continue
                total = int(r.headers.get("content-length", 0))
                tmp = dest.with_suffix(dest.suffix + ".part")
                with open(tmp, "wb") as f, tqdm(
                    total=total, unit="B", unit_scale=True, desc=dest.name, leave=False
                ) as pbar:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            if total:
                                pbar.update(len(chunk))
                tmp.replace(dest)
                return True
        except Exception:
            time.sleep(0.6 * (i + 1))
    return False

# -------------------- Data Dragon ----------------
def get_latest_version() -> str:
    versions_url = "https://ddragon.leagueoflegends.com/api/versions.json"
    versions = get_json(versions_url)
    if not versions:
        raise RuntimeError("No versions returned by Data Dragon.")
    return versions[0]  # latest

def list_champions(version: str) -> Dict[str, dict]:
    # Summary of all champions (names + keys)
    url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/{LANG}/champion.json"
    data = get_json(url)
    return data.get("data", {})

def get_champion_detail(version: str, champ_id: str) -> dict:
    # Full champion record including spells (Q/W/E/R)
    url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/{LANG}/champion/{champ_id}.json"
    data = get_json(url)
    # structure is { 'data': { champ_id: { ... } } }
    return data["data"][champ_id]

def portrait_url(version: str, champ_id: str) -> str:
    # Square portrait (what you want for heroes/)
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{champ_id}.png"

def spell_icon_url(version: str, spell_id: str) -> str:
    # Ability icon image
    return f"https://ddragon.leagueoflegends.com/cdn/{version}/img/spell/{spell_id}.png"

# -------------------- Main logic -----------------
def main():
    print("Fetching latest Data Dragon version…")
    version = get_latest_version()
    print(f"Latest version: {version}")

    champs = list_champions(version)
    if not champs:
        print("No champions found, exiting.")
        sys.exit(1)

    # Plan: for each champion:
    #  - portrait: img/champion/{ChampId}.png → heroes/{slug(champName)}.png
    #  - ultimate: spells list index 3 → its 'id' → img/spell/{id}.png
    #    saved as ultimates/{slug(champName)}.png
    portraits_ok = 0
    ults_ok = 0
    fails = []

    for champ_id, cdata in tqdm(champs.items(), desc="Champions", unit="champ"):
        champ_name = cdata.get("name", champ_id)
        champ_slug = slugify(champ_name)

        # --- portrait
        p_url = portrait_url(version, champ_id)
        p_dest = OUT_HEROES / f"{champ_slug}.png"
        ok_portrait = download_file(p_url, p_dest)
        if ok_portrait:
            portraits_ok += 1
        else:
            fails.append((champ_name, "portrait", p_url))

        # --- ultimate icon
        try:
            detail = get_champion_detail(version, champ_id)
            spells = detail.get("spells", [])
            if not spells or len(spells) < 4:
                raise RuntimeError("No spell list or incomplete (expected 4).")
            r_spell = spells[3]  # Q,W,E,**R** (index 3)
            spell_id = r_spell.get("id")  # e.g., "AhriR"
            if not spell_id:
                raise RuntimeError("R spell has no 'id'.")
            u_url = spell_icon_url(version, spell_id)
            u_dest = OUT_ULTS / f"{champ_slug}.png"
            ok_ult = download_file(u_url, u_dest)
            if ok_ult:
                ults_ok += 1
            else:
                fails.append((champ_name, "ultimate", u_url))
        except Exception as e:
            fails.append((champ_name, "ultimate", str(e)))

    print()
    print("===== DONE =====")
    print(f"Portraits saved: {portraits_ok}")
    print(f"Ult icons saved: {ults_ok}")
    if fails:
        print("Some items failed:")
        for name, kind, info in fails[:20]:
            print(f" - {name} [{kind}] -> {info}")
        if len(fails) > 20:
            print(f" ... and {len(fails)-20} more")

    print(f"\nPlace these folders next to your overlay:\n  {OUT_HEROES.resolve()}\n  {OUT_ULTS.resolve()}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
