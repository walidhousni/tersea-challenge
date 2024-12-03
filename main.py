from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()

# Modèle Pydantic avec gestion de l'ObjectId de MongoDB
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError('Invalid objectid')
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type='string')

class Book(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    title: str
    author: str
    description: str = None

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}

# Connexion à MongoDB
client = AsyncIOMotorClient('mongodb://mongo:27017')
db = client.books_db
collection = db.books

# GET /books
@app.get("/books", response_model=List[Book])
async def get_books():
    books = []
    cursor = collection.find({})
    async for document in cursor:
        books.append(Book(**document))
    return books

# GET /books/{book_id}
@app.get("/books/{book_id}", response_model=Book)
async def get_book(book_id: str):
    book = await collection.find_one({"_id": ObjectId(book_id)})
    if book:
        return Book(**book)
    raise HTTPException(status_code=404, detail="Book not found")

# POST /books
@app.post("/books", response_model=Book)
async def create_book(book: Book):
    book = book.dict(by_alias=True)
    result = await collection.insert_one(book)
    book["_id"] = result.inserted_id
    return Book(**book)

# PUT /books/{book_id}
@app.put("/books/{book_id}", response_model=Book)
async def update_book(book_id: str, updated_book: Book):
    updated_book = updated_book.dict(by_alias=True)
    result = await collection.replace_one({"_id": ObjectId(book_id)}, updated_book)
    if result.modified_count:
        return updated_book
    raise HTTPException(status_code=404, detail="Book not found")

# DELETE /books/{book_id}
@app.delete("/books/{book_id}")
async def delete_book(book_id: str):
    result = await collection.delete_one({"_id": ObjectId(book_id)})
    if result.deleted_count:
        return {"message": "Book deleted"}
    raise HTTPException(status_code=404, detail="Book not found")
