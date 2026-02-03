import requests
import csv
import json
import time
import sys
from typing import List, Dict
import re
import math

class MultiPlatformInfluencerScraper:
    def __init__(self, twitch_client_id=None, twitch_client_secret=None, youtube_api_key=None, rapidapi_key=None):
        self.twitch_client_id = twitch_client_id
        self.twitch_client_secret = twitch_client_secret
        self.youtube_api_key = youtube_api_key
        self.rapidapi_key = rapidapi_key
        self.twitch_token = None
        
        if twitch_client_id and twitch_client_secret:
            self.twitch_token = self.get_twitch_token()
    
    # --- AUTHENTIFICATION ---

    def get_twitch_token(self):
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.twitch_client_id,
            "client_secret": self.twitch_client_secret,
            "grant_type": "client_credentials"
        }
        try:
            response = requests.post(url, params=params)
            return response.json().get("access_token")
        except Exception:
            return None

    # --- OUTILS DE NETTOYAGE ---

    def extract_email_from_bio(self, text: str) -> str:
        if not text: return ""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        return emails[0] if emails else ""

    def detect_region_from_avatar(self, avatar_uri: str) -> str:
        if not avatar_uri: return "Global"
        match = re.search(r'~c3_([a-z]{2})_', avatar_uri)
        return match.group(1).upper() if match else "Global"

    # --- RECHERCHE PAR PLATEFORME ---

    def search_twitch(self, keyword: str, limit: int = 50, min_followers: int = 0) -> List[Dict]:
        if not self.twitch_token: return []
        
        url = "https://api.twitch.tv/helix/search/channels"
        headers = {
            "Client-ID": self.twitch_client_id,
            "Authorization": f"Bearer {self.twitch_token}"
        }
        params = {"query": keyword, "first": min(limit, 100)}
        
        influencers = []
        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            
            for channel in data.get("data", []):
                # Récupération des followers
                f_count = 0
                try:
                    f_resp = requests.get(
                        "https://api.twitch.tv/helix/channels/followers",
                        headers=headers, 
                        params={"broadcaster_id": channel["id"]}
                    )
                    f_count = f_resp.json().get("total", 0)
                except: pass

                if f_count < min_followers: continue

                influencers.append({
                    "platform": "Twitch",
                    "username": channel["broadcaster_login"],
                    "display_name": channel["display_name"],
                    "url": f"https://twitch.tv/{channel['broadcaster_login']}",
                    "followers": f_count,
                    "video_count": 0,
                    "relevance_score": 5.0 if keyword.lower() in channel.get("title", "").lower() else 1.0,
                    "category": channel.get("game_name", ""),
                    "description": channel.get("title", ""),
                    "is_live": channel.get("is_live", False),
                    "email": "",
                    "region": "Global"
                })
        except Exception: pass
        return influencers

    def search_youtube(self, keyword: str, limit: int = 50, min_subscribers: int = 0) -> List[Dict]:
        if not self.youtube_api_key: return []
        
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet", "q": keyword, "type": "channel",
            "maxResults": min(limit, 50), "key": self.youtube_api_key
        }
        
        influencers = []
        try:
            resp = requests.get(url, params=params).json()
            ids = [item["id"]["channelId"] for item in resp.get("items", [])]
            if not ids: return []

            stats_resp = requests.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "snippet,statistics", "id": ",".join(ids), "key": self.youtube_api_key}
            ).json()
            
            for item in stats_resp.get("items", []):
                stats = item.get("statistics", {})
                subs = int(stats.get("subscriberCount", 0))
                if subs < min_subscribers: continue

                snippet = item.get("snippet", {})
                desc = snippet.get("description", "")
                
                influencers.append({
                    "platform": "YouTube",
                    "username": item["id"],
                    "display_name": snippet.get("title", ""),
                    "url": f"https://youtube.com/channel/{item['id']}",
                    "followers": subs,
                    "video_count": stats.get("videoCount", 0),
                    "relevance_score": 5.0 if keyword.lower() in desc.lower() else 1.0,
                    "category": "YouTube",
                    "description": desc[:200],
                    "is_live": False,
                    "email": self.extract_email_from_bio(desc),
                    "region": "Global"
                })
        except Exception: pass
        return influencers

    def search_tiktok(self, keyword: str, limit: int = 50, min_followers: int = 0) -> List[Dict]:
        if not self.rapidapi_key: return []

        headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": "tokapi-mobile-version.p.rapidapi.com"
        }
        influencers = []
        try:
            resp = requests.get(
                "https://tokapi-mobile-version.p.rapidapi.com/v1/search/user",
                headers=headers, params={"keyword": keyword, "count": limit}
            ).json()
            
            # CORRECTION: L'API retourne directement user_list, pas dans data
            for u in resp.get("user_list", []):
                user = u.get("user_info", {})
                stats = u.get("stats", {})
                f_count = stats.get("follower_count", 0)
                
                if f_count < min_followers: continue
                
                bio = user.get("signature", "")
                avatar = user.get("avatar_168x168", {})
                avatar_uri = avatar.get("uri", "") if isinstance(avatar, dict) else ""
                
                influencers.append({
                    "platform": "TikTok",
                    "username": user.get("unique_id", ""),
                    "display_name": user.get("nickname", ""),
                    "url": f"https://tiktok.com/@{user.get('unique_id', '')}",
                    "followers": f_count,
                    "video_count": stats.get("video_count", 0),
                    "relevance_score": 5.0 if keyword.lower() in bio.lower() else 1.0,
                    "category": "TikTok",
                    "description": bio[:200],
                    "is_live": False,
                    "email": self.extract_email_from_bio(bio),
                    "region": self.detect_region_from_avatar(avatar_uri)
                })
        except Exception as e:
            print(f"Erreur TikTok: {e}")
        return influencers

    # --- FONCTIONS APPELÉES PAR APP.PY ---

    def search_all_platforms(self, keyword, platforms, limit, min_subs, min_followers):
        """Cette fonction est le point d'entrée principal pour app.py"""
        all_results = []
        if "twitch" in platforms:
            all_results.extend(self.search_twitch(keyword, limit, min_followers))
        if "youtube" in platforms:
            all_results.extend(self.search_youtube(keyword, limit, min_subs))
        if "tiktok" in platforms:
            all_results.extend(self.search_tiktok(keyword, limit, min_followers))
        return all_results

    def export_to_csv(self, influencers: List[Dict], filename: str):
        """Cette fonction génère le CSV pour app.py"""
        if not influencers:
            print("Aucun influenceur trouvé - pas de CSV généré")
            return
        
        # Définition des colonnes
        fieldnames = [
            "platform", "username", "display_name", "url", "followers", 
            "video_count", "relevance_score", "category", "description", 
            "is_live", "email", "region"
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(influencers)
        
        print(f"{len(influencers)} influenceurs exportés dans {filename}")


# --- MODE CLI (optionnel) ---
if __name__ == "__main__":
    if len(sys.argv) > 1:
        TWITCH_CLIENT_ID = "e1bf153bcn7rwhccgw2dbgwaa6rlgx"
        TWITCH_CLIENT_SECRET = "s1ixbfiu0j93r18vzbk4nsng04342z"
        YOUTUBE_API_KEY = "AIzaSyBL-rRkam041T3sBBhecLPYApe3Q0jVYoI"
        RAPIDAPI_KEY = "d25e6c2138msh4b32e30b0cda61ap1117dcjsnadd0cad8dca0"

        scraper = MultiPlatformInfluencerScraper(
            TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, 
            YOUTUBE_API_KEY, RAPIDAPI_KEY
        )

        keyword = sys.argv[1]
        platforms = sys.argv[2].split(",")
        min_subs = int(sys.argv[3])
        min_followers = int(sys.argv[4])
        limit = int(sys.argv[5])

        results = scraper.search_all_platforms(keyword, platforms, limit, min_subs, min_followers)
        scraper.export_to_csv(results, f"influenceurs_{keyword}.csv")