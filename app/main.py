from fastapi import FastAPI
from app.routers import categories, products, users, reviews


app = FastAPI(version='0.1.0')

app.include_router(categories.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(reviews.router)


@app.get('/')
async def get_page() -> dict:
    return {'detail': "Welcome to store forged with FastAPI"}
