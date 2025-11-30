#!/bin/bash

PICS="/Users/gavinwalker/Desktop/AI OUTFIT PICS"
OUTPUT_DIR="glasses_test_results"
mkdir -p "$OUTPUT_DIR"

# Only the 6 models with glasses
declare -a MODELS=(
    "IMG_6747 2.JPG:womenswear"
    "IMG_6748 2.JPG:womenswear"
    "IMG_6749 2.JPG:womenswear"
    "IMG_6750 2.JPG:womenswear"
    "IMG_6751 2.JPG:womenswear"
    "IMG_6752 2.JPG:womenswear"
)

echo "🤓 Testing 6 Glasses Models"
echo "============================"

for i in "${!MODELS[@]}"; do
    IFS=':' read -r MODEL GENDER <<< "${MODELS[$i]}"
    
    echo ""
    echo "[$((i+1))/6] Testing $MODEL..."
    
    python vto_complete_system.py \
        "$PICS/$MODEL" \
        average \
        average \
        "$GENDER" \
        "$PICS/blacktrousers.png" \
        "$PICS/IMG_6663.jpg" \
        "$PICS/IMG_6662.jpg" \
        "$PICS/IMG_6536.PNG"
    
    SAFE_NAME="${MODEL// /_}"
    cp vto_complete_test/vto_result.png "$OUTPUT_DIR/${SAFE_NAME%.JPG}_result.png"
    
    echo "✅ Saved"
    
    if [ $i -lt 5 ]; then
        echo "⏳ Waiting 20 seconds..."
        sleep 20
    fi
done

echo ""
echo "🎉 Done! Check: $OUTPUT_DIR/"
