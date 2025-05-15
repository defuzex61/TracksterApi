from fastapi import FastAPI

from src.routes import albums, recommendations, tracks, playlists,users

app = FastAPI()

app.include_router(tracks.router, prefix="/api", tags=["tracks"])
app.include_router(albums.router, prefix="/api", tags=["albums"])
app.include_router(playlists.router, prefix="/api", tags=["playlists"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(users.router, prefix="/api", tags=["search-tracks"])
app.include_router(recommendations.router, prefix="/api", tags=["recommendations"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)