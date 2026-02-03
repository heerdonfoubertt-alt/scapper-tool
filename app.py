"""
Serveur FastAPI pour Influencer Scraper
Lancement: python app.py
Puis ouvrir: http://localhost:3000
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import os
import json
from datetime import datetime
from typing import List
import glob

# Import du scraper
from python_influencer_scraper import MultiPlatformInfluencerScraper

app = FastAPI(title="Influencer Scraper", version="2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
TWITCH_CLIENT_ID = "e1bf153bcn7rwhccgw2dbgwaa6rlgx"
TWITCH_CLIENT_SECRET = "s1ixbfiu0j93r18vzbk4nsng04342z"
YOUTUBE_API_KEY = "AIzaSyBL-rRkam041T3sBBhecLPYApe3Q0jVYoI"
RAPIDAPI_KEY = "d25e6c2138msh4b32e30b0cda61ap1117dcjsnadd0cad8dca0"

# État global
current_job = None
log_queue = asyncio.Queue()

# ===== Modèles Pydantic =====

class ScraperRequest(BaseModel):
    keyword: str
    platforms: List[str]
    minFollowersYT: int = 0
    minFollowersTW: int = 0
    maxResults: int = 50

class FilesList(BaseModel):
    files: List[str]

# ===== Fonctions utilitaires =====

async def send_log(message: str):
    """Envoyer un log dans la queue"""
    await log_queue.put({"event": "log", "data": {"line": message}})
    print(message)

async def send_status(status_data: dict):
    """Envoyer le statut dans la queue"""
    await log_queue.put({"event": "status", "data": status_data})

async def send_done(output_file: str):
    """Signaler la fin du traitement"""
    await log_queue.put({"event": "done", "data": {"output": output_file}})

# ===== Routes =====

@app.get("/", response_class=HTMLResponse)
async def index():
    """Page principale"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/logs")
async def stream_logs():
    """SSE pour les logs en temps réel"""
    async def event_generator():
        # Envoyer le statut actuel
        if current_job:
            yield f"event: status\ndata: {json.dumps(current_job)}\n\n"
        
        # Stream des logs
        while True:
            try:
                msg = await asyncio.wait_for(log_queue.get(), timeout=30.0)
                event = msg.get("event", "message")
                data = msg.get("data", {})
                yield f"event: {event}\ndata: {json.dumps(data)}\n\n"
            except asyncio.TimeoutError:
                # Heartbeat
                yield ": heartbeat\n\n"
            except Exception as e:
                print(f"Erreur stream: {e}")
                break
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/api/files", response_model=FilesList)
async def list_files():
    """Lister les fichiers CSV"""
    csv_files = [os.path.basename(f) for f in glob.glob("*.csv")]
    return {"files": csv_files}

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Télécharger un fichier CSV"""
    # Sécurité
    filename = os.path.basename(filename)
    filepath = os.path.join(os.getcwd(), filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    
    return FileResponse(
        filepath,
        media_type="text/csv",
        filename=filename
    )

@app.post("/api/run/influencer-scraper")
async def run_scraper(request: ScraperRequest):
    """Lancer le scraper d'influenceurs"""
    global current_job
    
    # Vérifier qu'aucun job n'est en cours
    if current_job and current_job.get("status") == "running":
        raise HTTPException(
            status_code=409,
            detail="Un programme est déjà en cours d'exécution"
        )
    
    # Validation
    if not request.keyword:
        raise HTTPException(status_code=400, detail="Mot-clé requis")
    
    if not request.platforms or len(request.platforms) == 0:
        raise HTTPException(
            status_code=400,
            detail="Veuillez sélectionner au moins une plateforme"
        )
    
    # Créer le job
    current_job = {
        "status": "running",
        "keyword": request.keyword,
        "platforms": request.platforms,
        "startedAt": datetime.now().isoformat()
    }
    
    await send_status(current_job)
    await send_log(f"▶️ Lancement de la recherche pour '{request.keyword}'")
    await send_log(f"📱 Plateformes: {', '.join(request.platforms)}")
    
    # Lancer le scraping en arrière-plan
    asyncio.create_task(scrape_task(
        keyword=request.keyword,
        platforms=request.platforms,
        min_followers_yt=request.minFollowersYT,
        min_followers_tw=request.minFollowersTW,
        max_results=request.maxResults
    ))
    
    return {"ok": True}

async def scrape_task(
    keyword: str,
    platforms: List[str],
    min_followers_yt: int,
    min_followers_tw: int,
    max_results: int
):
    """Tâche de scraping asynchrone"""
    global current_job
    
    try:
        await send_log("🔧 Initialisation du scraper...")
        
        # Créer le scraper
        scraper = MultiPlatformInfluencerScraper(
            TWITCH_CLIENT_ID,
            TWITCH_CLIENT_SECRET,
            YOUTUBE_API_KEY,
            RAPIDAPI_KEY
        )
        
        await send_log("🔍 Recherche en cours...")
        
        # Lancer la recherche (dans un thread pour ne pas bloquer)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            scraper.search_all_platforms,
            keyword,
            platforms,
            max_results,
            min_followers_yt,
            min_followers_tw
        )
        
        await send_log(f"📊 {len(results)} influenceurs trouvés")
        
        # Exporter les résultats
        output_filename = f"influenceurs_{keyword.replace(' ', '_')}.csv"
        
        await loop.run_in_executor(
            None,
            scraper.export_to_csv,
            results,
            output_filename
        )
        
        # Succès
        current_job["status"] = "done"
        current_job["exitCode"] = 0
        await send_status(current_job)
        await send_log(f"✅ Terminé avec succès !")
        await send_log(f"📄 Fichier créé: {output_filename}")
        await send_done(output_filename)
        
    except Exception as e:
        # Erreur
        current_job["status"] = "error"
        current_job["exitCode"] = 1
        current_job["error"] = str(e)
        await send_status(current_job)
        await send_log(f"❌ Erreur: {str(e)}")
        
        import traceback
        traceback.print_exc()

# ===== Lancement =====

if __name__ == "__main__":
    import uvicorn
    
    # Créer les dossiers nécessaires
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    
    print("="*60)
    print("🚀 Serveur FastAPI démarré !")
    print("📍 Interface web : http://localhost:3000")
    print("📚 Documentation API : http://localhost:3000/docs")
    print("="*60)
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=3000,
        reload=False,
        log_level="info"
    )
