import json
import requests
import os
import string
import unicodedata
import time
import csv

validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)
def removeDisallowedFilenameChars(filename):
    cleanedFilename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore')
    return ''.join(chr(c) for c in cleanedFilename if chr(c) in validFilenameChars)

user_id = int(input('Enter User ID from profile URL: '))
osu_session_cookie = str(input('Enter osu session token, instructions in github readme: '))




# Limit hard coded to 20
limit = 20
offset = 0

try:
    os.makedirs("./songs")
except FileExistsError:
    pass

csv_file = "download_log.csv"
download_log = []
completed_ids = set()

# --- Load existing CSV if available ---
if os.path.exists(csv_file):
    choice = input("📄 Found existing download_log.csv. Resume and skip completed? (y/n): ").strip().lower()
    if choice == "y":
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                download_log.append(row)
                if row["status"] == "success":
                    completed_ids.add(row["beatmap_id"])
        print(f"✅ Loaded {len(download_log)} log entries, skipping {len(completed_ids)} completed beatmaps.")

while True:
    print(f"\nFetching maps with offset={offset}, limit={limit} ...")
    r = requests.get(
        f'https://osu.ppy.sh/users/{user_id}/beatmapsets/most_played?offset={offset}&limit={limit}'
    )
    data = r.json()

    if not data:  # Break if there is no new data
        print("\nKeine weiteren Beatmaps gefunden. Fertig!")
        break

    batch_log = []  # collect only this batch's results

    for beatmap in data:
        beatmap_id = str(beatmap['beatmapset']['id'])

        # Skip if already successfully downloaded
        if beatmap_id in completed_ids:
            print(f"⏭️ Skipping {beatmap_id}, already downloaded successfully.")
            continue

        beatmap_title = removeDisallowedFilenameChars(str(beatmap['beatmapset']['title']))
        filename = f"{beatmap_id}_{beatmap_title}.osz"
        filepath = f'./songs/{filename}'
        download_url = f"https://osu.ppy.sh/beatmapsets/{beatmap_id}/download?noVideo=1"

        print(f'\n-------{beatmap_id}-------')
        print(download_url)
        print('Downloading beatmap: ' + str(beatmap_title))
        time.sleep(1)
        cookies = {'osu_session': osu_session_cookie}

        # retry loop
        retries = 0
        max_retries = 4
        success = False

        while retries <= max_retries and not success:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
                "Referer": f"https://osu.ppy.sh/beatmapsets/{beatmap_id}"
            }
            #r = requests.get(download_url, cookies=cookies)
            r = requests.get(download_url, cookies=cookies, headers=headers, allow_redirects=True)

            if r.status_code == 200 and r.content:
                try:
                    with open(filepath, 'wb') as f:  
                        f.write(r.content)
                    status = "success"
                    print("✅ Download successful")
                    success = True
                except Exception as e:
                    status = f"failed ({e})"
                    print("❌ Error While Saving:", e)
                    break  # don’t retry file saving errors
            elif r.status_code == 429:  # too many requests
                retries += 1
                if retries <= max_retries:
                    print(f"⚠️ Too many requests (429). Waiting 10m before retry {retries}/{max_retries}...")
                    time.sleep(600)
                else:
                    status = "failed (429 too many requests, max retries reached)"
                    print("❌ Giving up on this beatmap after max retries.")
            else:
                status = f"failed (status {r.status_code})"
                print("❌ Download Failed, Status:", r.status_code)
                break  # don’t retry other errors

        entry = {
            "beatmap_id": beatmap_id,
            "title": beatmap_title,
            "status": status
        }
        download_log.append(entry)
        batch_log.append(entry)

        if status == "success":
            completed_ids.add(beatmap_id)

    # --- Write CSV after each batch ---
    write_mode = "w" if not os.path.exists(csv_file) else "a"
    with open(csv_file, write_mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["beatmap_id", "title", "status"])
        if write_mode == "w":
            writer.writeheader()
        writer.writerows(batch_log)

    print(f"📄 Updated log with {len(batch_log)} entries.")

    # Prepare for next batch
    offset += limit
    print("\nWaiting 20 seconds before the next batch is downloaded ...")
    time.sleep(20)

print(f"\n✅ All done! Download log is in '{csv_file}'")
