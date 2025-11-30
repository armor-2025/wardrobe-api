def encode_image(img, model, preprocess, device):
    try:
        with torch.no_grad():
            img_tensor = preprocess(img).unsqueeze(0).to(device)
            embedding = model.encode_image(img_tensor)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)
        return embedding.cpu().numpy().astype("float32")[0]
    except Exception as e:
        print(f"Encode error: {str(e)[:60]}")
        return None
