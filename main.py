from fastapi import FastAPI, HTTPException
import requests

TEST_URL = "https://github.com/MaksymBratsiun/NER_BERT/blob/main/inference_NER.py"

app = FastAPI()


@app.get("/api/healthchecker")
def root():
    return {"message": "OK"}


