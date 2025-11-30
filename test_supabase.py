from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("=" * 70)
print("🧪 TESTING SUPABASE")
print("=" * 70)

print("\n📡 Connecting...")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("✅ Connected!")

# Test: Check if products table exists
print("\n🔍 Checking products table...")
result = supabase.table('products').select("count", count="exact").execute()
print(f"✅ Products table exists!")
print(f"   Current products: {result.count}")

print("\n" + "=" * 70)
print("✅ SUPABASE READY!")
print("=" * 70)

print("""
Next: Import products from ASOS with CLIP embeddings!
""")

