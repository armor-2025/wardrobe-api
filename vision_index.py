import os, json, io, requests
from PIL import Image
import numpy as np
import torch
import faiss
import open_clip
from meilisearch import Client

MEILI_HOST = os.getenv("MEILI_HOST", "http://127.0.0.1:7700")
MEILI_KEY  = os.getenv("MEILI_KEY",  "master_key")
INDEX_UID  = "products"

INDEX_PATH = "faiss.index"
META_PATH  = "faiss_meta.json"

def get_products(limit=1000):
    cli = Client(MEILI_HOST, MEILI_KEY)
    res = cli.index(INDEX_UID).get_documents(parameters={"limit": limit})

    # Normalize different return shapes (client versions differ)
    if hasattr(res, "results"):          # DocumentsResults object
        docs = res.results
    elif isinstance(res, dict) and "results" in res:
        docs = res["results"]
    elif isinstance(res, list):
        docs = res
    else:
        try:
            docs = list(res)
        except Exception:
            raise TypeError(f"Unsupported get_documents return type: {type(res)}")

    # Convert Document-like objects to plain dicts
    def _to_dict(x):
        if isinstance(x, dict):
            return x
        # pydantic v2
        if hasattr(x, "model_dump"):
            try:
                return x.model_dump()
            except Exception:
                pass
        # pydantic v1
        if hasattr(x, "dict"):
            try:
                return x.dict()
            except Exception:
                pass
        # last resort
        try:
            return json.loads(json.dumps(x, default=lambda o: getattr(o, "__dict__", 
{})))
        except Exception:
            raise TypeError(f"Cannot convert document of type {type(x)} to dict")

    docs = [_to_dict(d) for d in docs]

    # Only keep docs that have at least one image URL
    return [d for d in docs if isinstance(d.get("images"), list) and d["images"]]

def load_img_from_url(url, timeout=15):
    # use system CA bundle if exported earlier
    verify = os.getenv("SSL_CERT_FILE") or True
    r = requests.get(url, timeout=timeout, verify=verify)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")

def build():
    print("Loading CLIP model...")
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="openai"
    )
    model.eval()
    device = "cpu"
    model.to(device)

    print("Fetching products from Meilisearch...")
    docs = get_products(limit=1000)

    vectors = []
    meta = []

    with torch.no_grad():
        for d in docs:
            url = d["images"][0]
            try:
                img = preprocess(load_img_from_url(url)).unsqueeze(0).to(device)
                emb = model.encode_image(img)
                emb = emb / emb.norm(dim=-1, keepdim=True)
                vectors.append(emb.cpu().numpy().astype("float32"))
                meta.append({
                    "id": d.get("id"),
                    "title": d.get("title", ""),
                    "image": url,
                })
                print(f"ok: {d.get('id')}")
            except Exception as e:
                print(f"skip {d.get('id')}: {e}")

    if not vectors:
        raise RuntimeError("No vectors produced — check your images.")

    X = np.concatenate(vectors, axis=0)
    print(f"Building FAISS index with {X.shape[0]} vectors of dim {X.shape[1]}...")

    faiss.normalize_L2(X)
    index = faiss.IndexFlatIP(X.shape[1])
    index.add(X)

    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, "w") as f:
        json.dump(meta, f)

    print(f"Saved {INDEX_PATH} and {META_PATH}")

if __name__ == "__main__":
    build()
