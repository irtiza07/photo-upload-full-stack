import boto3
import time
import psycopg2

from enum import Enum
from typing import Any, List
from typing import Optional
from typing import BinaryIO
from urllib import response

import uvicorn
from fastapi import (
    Cookie,
    FastAPI,
    Header,
    status,
    HTTPException,
    BackgroundTasks,
    Form,
    File,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, Field

from credentials import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

S3_BUCKET_NAME = "test-photos-123"


class PhotoModel(BaseModel):
    id: int
    photo_name: str
    photo_url: str
    is_deleted: bool


app = FastAPI(debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/status")
async def check_status():
    return "Hello World"


@app.post("/photos", status_code=201)
async def add_photo(file: UploadFile):
    print("Create endpoint hit!!")
    print(file.filename)
    print(file.content_type)

    # Upload file to AWS S3
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(S3_BUCKET_NAME)
    bucket.upload_fileobj(file.file, file.filename, ExtraArgs={"ACL": "public-read"})
    uploaded_file_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{file.filename}"

    # Store URL in database
    conn = psycopg2.connect(
        database="exampledb", user="docker", password="docker", host="0.0.0.0"
    )
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO photo (photo_name, photo_url) VALUES ('{file.filename}', '{uploaded_file_url}')"
    )
    conn.commit()
    cur.close()
    conn.close()


@app.get("/photos", response_model=List[PhotoModel])
async def get_all_photos():
    # Connect to existing database
    conn = psycopg2.connect(
        database="exampledb", user="docker", password="docker", host="0.0.0.0"
    )
    cur = conn.cursor()
    cur.execute("SELECT * FROM photo ORDER BY id DESC")
    rows = cur.fetchall()

    formatted_photos = []
    for row in rows:
        formatted_photos.append(
            PhotoModel(
                id=row[0],
                photo_name=row[1],
                photo_url=row[2],
                is_deleted=False if row[3] == 0 else True,
            )
        )

    cur.close()
    conn.close()
    return formatted_photos


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
