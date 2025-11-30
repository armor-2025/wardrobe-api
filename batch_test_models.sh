#!/bin/bash

PICS="/Users/gavinwalker/Desktop/AI OUTFIT PICS"
OUTPUT_DIR="batch_vto_results"
mkdir -p "$OUTPUT_DIR"

# Array of models with their gender (using actual filenames with spaces)
declare -a MODELS=(
    "IMG_6735 2.jpg:womenswear"
    "IMG_6737 2.JPG:womenswear"
    "IMG_6738 2.JPG:womenswear"
    "IMG_6739 2.JPG:womenswear"
    "IMG_6740 2.JPG:womenswear"
    "IMG_6741 2.JPG:womenswear"
    "IMG_6742 2.JPG:womenswear"
    "IMG_6743 2.JPG:womenswear"
    "IMG_6744 2.JPG:womenswear"
    "IMG_6745 2.JPG:womenswear"
    "IMG_6747 2.JPG:womenswear"
    "IMG_6748 2.JPG:womenswear"
    "IMG_6749 2.JPG:womenswear"
    "IMG_6750 2.JPG:womenswear"
    "IMG_6751 2.JPG:womenswear"
    "IMG_6752 2.JPG:womenswear"
)

echo "🎯 BATCH VTO TEST - 16 Models"
echo "=============================="

for i in "${!MODELS[@]}"; do
    IFS=':' read -r MODEL GENDER <<< "${MODELS[$i]}"
    
    echo ""
    echo "[$((i+1))/16] Testing $MODEL ($GENDER)..."
    
    python vto_complete_system.py \
        "$PICS/$MODEL" \
        average \
        average \
        "$GENDER" \
        "$PICS/blacktrousers.png" \
        "$PICS/IMG_6663.jpg" \
        "$PICS/IMG_6662.jpg" \
        "$PICS/IMG_6536.PNG"
    
    # Save result with sanitized filename
    SAFE_NAME="${MODEL// /_}"
    cp vto_complete_test/vto_result.png "$OUTPUT_DIR/${SAFE_NAME%.jpg}_result.png" 2>/dev/null || \
    cp vto_complete_test/vto_result.png "$OUTPUT_DIR/${SAFE_NAME%.JPG}_result.png"
    
    echo "✅ Saved"
    
    # Wait 25 seconds between tests
    if [ $i -lt 15 ]; then
        echo "⏳ Waiting 25 seconds..."
        sleep 25
    fi
done

echo ""
echo "🎉 COMPLETE!"
ls -lh "$OUTPUT_DIR/"
