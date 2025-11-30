"""
Real FASHN AI API Test with your credentials
"""
import requests
import base64
import os
import json
import time

print("=" * 70)
print("🧪 Testing FASHN AI API - Real Test")
print("=" * 70)

FASHN_API_KEY = 'fa-cd1JlcPckbGK-j2IesXZQlXgXK54h1vOOFXyw'

base_path = '/Users/gavinwalker/Downloads/files (4)/'

# Load and encode images
print("\n📦 Loading images...")

with open(base_path + 'IMG_6033.jpeg', 'rb') as f:
    person_b64 = base64.b64encode(f.read()).decode('utf-8')
    print("✅ Person image loaded")

with open(base_path + 'IMG_5937.PNG', 'rb') as f:
    garment_b64 = base64.b64encode(f.read()).decode('utf-8')
    print("✅ Garment image loaded (polka dot shirt)")

# Try FASHN AI API
print("\n🔄 Calling FASHN AI API...")

# Based on typical VTO API structure
api_url = 'https://api.fashn.ai/v1/run'

payload = {
    "model_image": f"data:image/jpeg;base64,{person_b64}",
    "garment_image": f"data:image/png;base64,{garment_b64}",
    "category": "tops",
    "num_samples": 1,
    "seed": 42
}

headers = {
    'Authorization': f'Bearer {FASHN_API_KEY}',
    'Content-Type': 'application/json'
}

try:
    print(f"📡 Sending request to {api_url}...")
    response = requests.post(
        api_url,
        headers=headers,
        json=payload,
        timeout=120  # VTO can take time
    )
    
    print(f"✅ Response received: Status {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ SUCCESS!")
        print(json.dumps(result, indent=2)[:500] + "...")
        
        # Check for result image
        if 'output' in result:
            if isinstance(result['output'], list) and len(result['output']) > 0:
                # Download result
                img_url = result['output'][0]
                print(f"\n📥 Downloading result from: {img_url[:50]}...")
                
                img_response = requests.get(img_url)
                with open('fashn_api_result.png', 'wb') as f:
                    f.write(img_response.content)
                
                print("✅ Saved: fashn_api_result.png")
                print("\n💰 Cost: $0.075")
                print("🎯 This is your production VTO solution!")
                
        elif 'id' in result:
            # Async job - need to poll
            job_id = result['id']
            print(f"\n⏳ Job created: {job_id}")
            print("   Polling for result...")
            
            # Poll for result
            for i in range(30):  # Try for up to 60 seconds
                time.sleep(2)
                status_response = requests.get(
                    f'https://api.fashn.ai/v1/status/{job_id}',
                    headers=headers
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    
                    if status_data.get('status') == 'completed':
                        print("✅ Job completed!")
                        
                        if 'output' in status_data:
                            img_url = status_data['output'][0] if isinstance(status_data['output'], list) else status_data['output']
                            
                            img_response = requests.get(img_url)
                            with open('fashn_api_result.png', 'wb') as f:
                                f.write(img_response.content)
                            
                            print("✅ Saved: fashn_api_result.png")
                            break
                    
                    print(f"   Status: {status_data.get('status', 'processing')}...")
                
    elif response.status_code == 401:
        print("❌ Authentication failed")
        print("   Check your API key in the FASHN dashboard")
        
    elif response.status_code == 400:
        print("❌ Bad request")
        print(response.text)
        print("\n💡 The API format might be different. Trying alternative...")
        
        # Try alternative format
        alt_payload = {
            "person": person_b64,
            "garment": garment_b64,
            "type": "upper_body"
        }
        
        alt_response = requests.post(
            'https://api.fashn.ai/try-on',
            headers=headers,
            json=alt_payload,
            timeout=120
        )
        
        print(f"Alternative endpoint status: {alt_response.status_code}")
        print(alt_response.text[:500])
        
    else:
        print(f"❌ Unexpected status: {response.status_code}")
        print(response.text[:500])

except requests.exceptions.Timeout:
    print("⏱️  Request timed out - FASHN AI takes 5-10 seconds per image")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)

