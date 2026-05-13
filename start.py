from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import requests
import sys
import re
from urllib.parse import quote, unquote

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# --- Configuration ---
PORT = 7050
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# --- Helper Functions ---

def get_title(imdb_id, content_type='movie'):
    """Fetches the title name from Cinemeta using IMDB ID and content type"""
    print(f"Fetching metadata for: {imdb_id} as {content_type}")

    try:
        url = f"https://v3-cinemeta.strem.io/meta/{content_type}/{imdb_id}.json"
        res = requests.get(url, timeout=5, headers=HEADERS)
        if res.status_code == 200:
            data = res.json()
            if data.get('meta'):
                meta = data['meta']
                title = meta.get('originalTitle') or meta.get('name')
                if title:
                    return title
    except Exception:
        pass

    # Fallback
    fallback_type = 'series' if content_type == 'movie' else 'movie'
    try:
        url = f"https://v3-cinemeta.strem.io/meta/{fallback_type}/{imdb_id}.json"
        res = requests.get(url, timeout=5, headers=HEADERS)
        if res.status_code == 200:
            data = res.json()
            if data.get('meta'):
                meta = data['meta']
                title = meta.get('originalTitle') or meta.get('name')
                if title:
                    print(f"  ⚠ Found as {fallback_type} instead of {content_type}, switching category")
                    return title
    except Exception:
        pass

    return None


def get_torrents(query, content_type='movie'):
    safe_query = quote(query)

    if content_type == 'series':
        category = 200
    else:
        category = 200

    url = f"https://apibay.org/q.php?q={safe_query}&cat={category}"

    # Parse query into title words + episode info
    ep_match = re.search(r'[Ss](\d+)[Ee](\d+)', query)
    if ep_match:
        title_part = query[:ep_match.start()].strip()
        season_num = int(ep_match.group(1))
        episode_num = int(ep_match.group(2))
        title_words = [w.lower() for w in title_part.split() if w]
    else:
        title_words = [w.lower() for w in query.split() if w]
        season_num = None
        episode_num = None

    # --- LOGGING ---
    print(f"  PB API URL: {url}")
    print(f"  Category: {category} ({'TV' if category == 205 else 'Pirating'})")
    print(f"  Required title words: {title_words}")
    if season_num is not None:
        print(f"  Required episode: S{season_num}E{episode_num}")
    # ---------------------

    allowed_keywords = ['1080p', '720p', '4k', '2160p', 'web', 'x265', 'x264', 'h264', 'h265', 'bluray']

    try:
        res = requests.get(url, timeout=10, headers=HEADERS)
        if res.status_code == 200:
            data = res.json()
            if not isinstance(data, list):
                return []

            results = []
            for item in data:
                if item.get('id') == '0' or not item.get('info_hash'):
                    continue

                name = item.get('name', '')
                name_lower = name.lower()

                # Title AND filter - ALL words must appear
                if not all(word in name_lower for word in title_words):
                    continue

                # Flexible episode filter for series
                if season_num is not None and episode_num is not None:
                    ep_patterns = [
                        f's{season_num:02d}e{episode_num:02d}',
                        f's{season_num}e{episode_num}',
                        f's{season_num:02d} e{episode_num:02d}',
                        f'{season_num}x{episode_num:02d}',
                        f'{season_num}x{episode_num}',
                    ]
                    if not any(pat in name_lower for pat in ep_patterns):
                        continue

                # Quality Filter
                if not any(keyword in name_lower for keyword in allowed_keywords):
                    continue

                try:
                    seeders = int(item.get('seeders', 0))
                except:
                    seeders = 0

                size_bytes = int(item.get('size', 0))
                size_str = f"{size_bytes / (1024**3):.1f} GB" if size_bytes > 1024**3 else f"{size_bytes /
(1024**2):.0f} MB"

                results.append({
                    "name": "TGBx",
                    "title": f"{name}\n💾 {size_str} 👥 {seeders}",
                    "infoHash": item.get('info_hash'),
                    "_seeders": seeders
                })

            # Sort results by seeders (descending)
            results.sort(key=lambda x: x['_seeders'], reverse=True)

            return results

    except Exception as e:
        print(f"  API Error: {e}")
        return []


# --- Server Logic ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/manifest.json':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            manifest = {
                "id": "python.pirate.standalone",
                "version": "1.0.0",
                "name": "TheGearyBox",
                "description": "Stremio addon",
                "types": ["movie", "series"],
                "resources": ["stream"],
                "idPrefixes": ["tt"]
            }
            self.wfile.write(json.dumps(manifest).encode('utf-8'))
            return

        if self.path.startswith('/stream/'):
            try:
                parts = self.path.split('/')
                if len(parts) < 4:
                    self.send_error(400)
                    return

                request_type = parts[2]  # 'movie' or 'series'
                file_name = unquote(parts[3])
                full_id = file_name.replace('.json', '')

                print(f"Request Type: {request_type}, ID: {full_id}")

                clean_id = full_id.split(':')[0]
                title = get_title(clean_id, request_type)

                if not title:
                    print(f"Title not found for {clean_id}")
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"streams": []}).encode('utf-8'))
                    return

                # The 1 .replace is escalating.. any bigger and we must clean it..
                query = title.replace('&', 'and').replace("'", "").replace('- ', '').replace(':', '').replace('?', '').replace('!', '')
                streams = []

                # --- DUAL SEARCH LOGIC ----
                if request_type == 'series' and ':' in full_id:
                    p = full_id.split(':')
                    if len(p) >= 3:
                        try:
                            season = int(p[1])
                            episode = int(p[2])

                            # Complete Season Sarch
                            query_season = f"{query} S{season:02d}"
                            print(f"Searching for: {query_season} (Season Pack)")
                            streams_season = get_torrents(query_season, request_type)

                            # 2. Specific Episode Search
                            query_episode = f"{query} S{season:02d}E{episode:02d}"
                            print(f"Searching for: {query_episode} (Specific Episode)")
                            streams_episode = get_torrents(query_episode, request_type)

                            # 3. Merge results and remove duplicates
                            combined_streams = {}
                            for s in streams_season:
                                combined_streams[s['infoHash']] = s
                            for s in streams_episode:
                                combined_streams[s['infoHash']] = s

                            streams = list(combined_streams.values())

                            # 4. Sort the final combined list by seeders
                            streams.sort(key=lambda x: x['_seeders'], reverse=True)

                        except Exception as e:
                            print(f"Error parsing series ID: {e}")
                            # Fallback to default search if parsing fails
                            print(f"Searching for: {query} (Fallback)")
                            streams = get_torrents(query, request_type)
                else:
                    # --- STANDARD MOVIE SEARCH ---
                    print(f"Searching for: {query}")
                    streams = get_torrents(query, request_type)

                # Clean up internal '_seeders' key before sending to Stremio
                for r in streams:
                    if '_seeders' in r:
                        del r['_seeders']

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"streams": streams}).encode('utf-8'))
                return

            except Exception as e:
                print(f"Critical Error: {e}")
                self.send_error(500, 'something went wrong')
                return

        if self.path == '/favicon.ico':
            self.send_response(204)
            return

        self.send_error(404)


# --- Start Server ---
print(f"Server running on http://127.0.0.1:{PORT}")
print("Press CTRL+C to stop")
HTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
