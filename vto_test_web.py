from flask import Flask, request, render_template_string, send_file
from flask_cors import CORS
import os
from pathlib import Path
from vto_complete_system import complete_vto_workflow
import tempfile
import shutil

app = Flask(__name__)
CORS(app)

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>VTO Test Interface</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .form-group {
            margin: 20px 0;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input[type="file"] {
            width: 100%;
            padding: 10px;
            border: 2px dashed #ddd;
            border-radius: 5px;
        }
        select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        button {
            width: 100%;
            padding: 15px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 20px;
        }
        button:hover {
            background: #45a049;
        }
        button:disabled {
            background: #cccccc;
            cursor: not-allowed;
        }
        #result {
            margin-top: 30px;
            text-align: center;
        }
        #result img {
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .loading {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        .loading.active {
            display: block;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #4CAF50;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .info {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨 VTO Test Interface</h1>
        
        <div class="info">
            <strong>Cost:</strong> $0.04 per generation<br>
            <strong>Status:</strong> ✅ Face perfect, ✅ Hair perfect, ✅ Glasses perfect
        </div>

        <form id="vtoForm" enctype="multipart/form-data">
            <div class="form-group">
                <label>👤 Model Photo (Your face photo)</label>
                <input type="file" name="model_photo" accept="image/*" required>
            </div>

            <div class="form-group">
                <label>👕 Top Garment (optional)</label>
                <input type="file" name="top" accept="image/*">
            </div>

            <div class="form-group">
                <label>👖 Bottom Garment (optional)</label>
                <input type="file" name="bottom" accept="image/*">
            </div>

            <div class="form-group">
                <label>🧥 Outerwear (optional)</label>
                <input type="file" name="outerwear" accept="image/*">
            </div>

            <div class="form-group">
                <label>👟 Shoes (optional)</label>
                <input type="file" name="shoes" accept="image/*">
            </div>

            <div class="form-group">
                <label>Body Type</label>
                <select name="body_type">
                    <option value="slim">Slim</option>
                    <option value="average" selected>Average</option>
                    <option value="curvy">Curvy</option>
                    <option value="plus">Plus</option>
                </select>
            </div>

            <div class="form-group">
                <label>Height</label>
                <select name="height">
                    <option value="petite">Petite</option>
                    <option value="average" selected>Average</option>
                    <option value="tall">Tall</option>
                    <option value="none">None</option>
                </select>
            </div>

            <div class="form-group">
                <label>Gender Presentation</label>
                <select name="gender">
                    <option value="menswear">Menswear</option>
                    <option value="womenswear">Womenswear</option>
                </select>
            </div>

            <button type="submit">Generate VTO</button>
        </form>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Generating... (~10 seconds)</p>
        </div>

        <div id="result"></div>
    </div>

    <script>
        document.getElementById('vtoForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const resultDiv = document.getElementById('result');
            const loadingDiv = document.getElementById('loading');
            const submitBtn = e.target.querySelector('button');
            
            // Show loading
            loadingDiv.classList.add('active');
            resultDiv.innerHTML = '';
            submitBtn.disabled = true;
            
            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    resultDiv.innerHTML = `
                        <h2>✅ Result:</h2>
                        <img src="${url}" alt="VTO Result">
                        <br><br>
                        <a href="${url}" download="vto_result.png">
                            <button type="button">Download Image</button>
                        </a>
                    `;
                } else {
                    const error = await response.text();
                    resultDiv.innerHTML = `<p style="color: red;">Error: ${error}</p>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
            } finally {
                loadingDiv.classList.remove('active');
                submitBtn.disabled = false;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        # Create temp directory for this request
        temp_dir = tempfile.mkdtemp()
        
        # Save uploaded files
        model_photo = request.files.get('model_photo')
        if not model_photo:
            return "Model photo is required", 400
            
        model_path = os.path.join(temp_dir, 'model.jpg')
        model_photo.save(model_path)
        
        # Get parameters
        body_type = request.form.get('body_type', 'average')
        height = request.form.get('height', 'average')
        gender = request.form.get('gender', 'womenswear')
        
        # Save garment files
        garment_paths = []
        for garment_type in ['top', 'bottom', 'outerwear', 'shoes']:
            garment = request.files.get(garment_type)
            if garment:
                path = os.path.join(temp_dir, f'{garment_type}.jpg')
                garment.save(path)
                garment_paths.append(path)
        
        if not garment_paths:
            return "At least one garment is required", 400
        
        # Generate VTO
        output_dir = os.path.join(temp_dir, 'output')
        complete_vto_workflow(
            model_path,
            body_type,
            height,
            gender,
            garment_paths,
            output_dir
        )
        
        # Result is always at this path
        result_path = os.path.join(output_dir, 'vto_result.png')
        
        # Send result
        return send_file(result_path, mimetype='image/png')
        
    except Exception as e:
        return str(e), 500
    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
