from fastapi import APIRouter, UploadFile, File
from agents.version_diff_agent import compare_docs, compare_smeta
import tempfile
import os
import shutil

router = APIRouter()

@router.post("/diff/docs")
async def compare_docs_endpoint(old_docs: list[UploadFile] = File(...), new_docs: list[UploadFile] = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        old_paths, new_paths = [], []
        for file in old_docs:
            path = os.path.join(temp_dir, "old_" + file.filename)
            with open(path, "wb") as f:
                f.write(await file.read())
            old_paths.append(path)

        for file in new_docs:
            path = os.path.join(temp_dir, "new_" + file.filename)
            with open(path, "wb") as f:
                f.write(await file.read())
            new_paths.append(path)

        result = compare_docs(old_paths, new_paths)
        return result
    finally:
        shutil.rmtree(temp_dir)

@router.post("/diff/smeta")
async def compare_smeta_endpoint(old_smeta: UploadFile = File(...), new_smeta: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    try:
        old_path = os.path.join(temp_dir, "old_" + old_smeta.filename)
        with open(old_path, "wb") as f:
            f.write(await old_smeta.read())

        new_path = os.path.join(temp_dir, "new_" + new_smeta.filename)
        with open(new_path, "wb") as f:
            f.write(await new_smeta.read())

        result = compare_smeta(old_path, new_path)
        return result
    finally:
        shutil.rmtree(temp_dir)
