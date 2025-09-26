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

# list for CSV-Logs
download_log = []

while True:
    print(f"\nFetching maps with offset={offset}, limit={limit} ...")
    r = requests.get(
        f'https://osu.ppy.sh/users/{user_id}/beatmapsets/most_played?offset={offset}&limit={limit}'
    )
    data = r.json()

    if not data:  # Break if there is no new data
        print("\nKeine weiteren Beatmaps gefunden. Fertig!")
        break

    for beatmap in data:
        beatmap_id = beatmap['beatmapset']['id']
        beatmap_title = removeDisallowedFilenameChars(str(beatmap['beatmapset']['title']))
        download_url = f"https://osu.ppy.sh/beatmapsets/{beatmap_id}/download?noVideo=1"

        print(f'\n-------{beatmap_id}-------')
        print(download_url)
        print('Downloading beatmap: ' + str(beatmap_title))

        cookies = {'osu_session': osu_session_cookie}

        # retry loop
        retries = 0
        max_retries = 4
        success = False

        while retries <= max_retries and not success:
            r = requests.get(download_url, cookies=cookies)

            if r.status_code == 200 and r.content:
                try:
                    with open(f'./songs/{beatmap_title}.osz', 'wb') as f:  
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
                    print(f"⚠️ Too many requests (429). Waiting 60s before retry {retries}/{max_retries}...")
                    time.sleep(60)
                else:
                    status = "failed (429 too many requests, max retries reached)"
                    print("❌ Giving up on this beatmap after max retries.")
            else:
                status = f"failed (status {r.status_code})"
                print("❌ Download Failed, Status:", r.status_code)
                break  # don’t retry other errors

        # appending results
        download_log.append({
            "beatmap_id": beatmap_id,
            "title": beatmap_title,
            "status": status
        })

    # Prepare for next batch
    offset += limit
    print("\nWaiting 20 seconds before the next batch is downloaded ...")
    time.sleep(20)

# Generate CSV log
csv_file = "download_log.csv"
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["beatmap_id", "title", "status"])
    writer.writeheader()
    writer.writerows(download_log)

print(f"\n📄 Download-Log saved in '{csv_file}'")
