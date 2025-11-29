"""
Real AI Item Extraction
Uses actual computer vision to extract items from outfit photos
"""
from PIL import Image, ImageDraw
from rembg import remove
import io
import base64
import numpy as np
import cv2
from typing import List, Dict, Any, Tuple


class RealItemExtractor:
    """
    Extract items using real AI:
    1. Detect clothing regions (color-based segmentation for now)
    2. Remove background with rembg
    3. Extract dominant colors
    4. Classify basic categories
    """
    
    async def extract_items_from_photo(
        self,
        image_data: bytes,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Real extraction pipeline
        """
        # Load image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Step 1: Detect clothing regions
        regions = self._detect_clothing_regions(image)
        
        # Step 2: Process each region
        items = []
        for idx, region in enumerate(regions):
            # Extract the region
            x1, y1, x2, y2 = region['bbox']
            cropped = image.crop((x1, y1, x2, y2))
            
            # Remove background
            segmented = self._remove_background(cropped)
            
            # Extract attributes
            attributes = self._extract_attributes(segmented)
            
            # Encode to base64
            segmented_base64 = self._image_to_base64(segmented)
            
            items.append({
                "item_id": f"extracted-{idx+1:03d}",
                "category": region['category'],
                "confidence": region['confidence'],
                "bounding_box": [x1, y1, x2, y2],
                "segmented_image": segmented_base64,
                "detected_attributes": attributes
            })
        
        return {
            "original_photo": self._image_to_base64(image),
            "items_detected": len(items),
            "items": items
        }
    
    
    def _detect_clothing_regions(self, image: Image.Image) -> List[Dict]:
        """
        Detect clothing regions in image
        
        For now: Simple approach using vertical segmentation
        - Top third: Outerwear/Top
        - Middle third: Top/Bottom
        - Bottom third: Bottom/Shoes
        
        In production: Use YOLOv8 trained on fashion dataset
        """
        width, height = image.size
        
        regions = []
        
        # Detect person first (find the main subject)
        person_bbox = self._detect_person_region(image)
        
        if person_bbox:
            px1, py1, px2, py2 = person_bbox
            person_height = py2 - py1
            person_width = px2 - px1
            
            # Upper body (top 40% of person) - Top/Outerwear
            regions.append({
                'bbox': [
                    px1,
                    py1,
                    px2,
                    int(py1 + person_height * 0.45)
                ],
                'category': 'top',
                'confidence': 0.85
            })
            
            # Lower body (40-70% of person) - Bottom
            regions.append({
                'bbox': [
                    px1,
                    int(py1 + person_height * 0.40),
                    px2,
                    int(py1 + person_height * 0.75)
                ],
                'category': 'bottom',
                'confidence': 0.82
            })
            
            # Feet (bottom 30% of person) - Shoes
            regions.append({
                'bbox': [
                    px1,
                    int(py1 + person_height * 0.70),
                    px2,
                    py2
                ],
                'category': 'shoes',
                'confidence': 0.78
            })
            
            # Check for held items (sides)
            # Left side
            if px1 > width * 0.1:
                regions.append({
                    'bbox': [
                        max(0, px1 - int(person_width * 0.3)),
                        int(py1 + person_height * 0.3),
                        px1,
                        int(py1 + person_height * 0.8)
                    ],
                    'category': 'accessories',
                    'confidence': 0.65
                })
            
            # Right side
            if px2 < width * 0.9:
                regions.append({
                    'bbox': [
                        px2,
                        int(py1 + person_height * 0.3),
                        min(width, px2 + int(person_width * 0.3)),
                        int(py1 + person_height * 0.8)
                    ],
                    'category': 'accessories',
                    'confidence': 0.65
                })
        
        return regions
    
    
    def _detect_person_region(self, image: Image.Image) -> Tuple[int, int, int, int]:
        """
        Detect the person in the image
        Simple approach: Find the largest contiguous region
        """
        # Convert to numpy array
        img_array = np.array(image)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Simple thresholding to find person
        # In your image, person is darker than background
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Find largest contour (assume it's the person)
            largest = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest)
            
            # Add some padding
            padding_x = int(w * 0.1)
            padding_y = int(h * 0.05)
            
            return (
                max(0, x - padding_x),
                max(0, y - padding_y),
                min(image.width, x + w + padding_x),
                min(image.height, y + h + padding_y)
            )
        
        # Fallback: use center 60% of image
        width, height = image.size
        return (
            int(width * 0.2),
            int(height * 0.1),
            int(width * 0.8),
            int(height * 0.9)
        )
    
    
    def _remove_background(self, image: Image.Image) -> Image.Image:
        """
        Remove background using rembg
        Returns image with transparent background
        """
        # Convert PIL to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Remove background
        output = remove(img_byte_arr)
        
        # Convert back to PIL
        return Image.open(io.BytesIO(output))
    
    
    def _extract_attributes(self, image: Image.Image) -> Dict[str, str]:
        """
        Extract visual attributes from segmented image
        """
        # Convert to numpy
        img_array = np.array(image)
        
        # Get dominant color
        color = self._get_dominant_color(img_array)
        
        # Detect pattern (simple check)
        pattern = self._detect_pattern(img_array)
        
        return {
            "color": color,
            "style": "casual",  # Would need ML model for this
            "pattern": pattern,
            "fit": "regular"
        }
    
    
    def _get_dominant_color(self, img_array: np.ndarray) -> str:
        """
        Get dominant color from image
        """
        # Get only non-transparent pixels
        if img_array.shape[2] == 4:  # Has alpha channel
            # Get pixels where alpha > 128 (semi-transparent or opaque)
            mask = img_array[:, :, 3] > 128
            pixels = img_array[mask][:, :3]
        else:
            pixels = img_array.reshape(-1, 3)
        
        if len(pixels) == 0:
            return "unknown"
        
        # Calculate average color
        avg_color = pixels.mean(axis=0)
        
        # Map to color name
        return self._rgb_to_color_name(avg_color)
    
    
    def _rgb_to_color_name(self, rgb: np.ndarray) -> str:
        """
        Convert RGB to basic color name
        """
        r, g, b = rgb
        
        # Simple color mapping
        if r < 50 and g < 50 and b < 50:
            return "black"
        elif r > 200 and g > 200 and b > 200:
            return "white"
        elif r > 150 and g < 100 and b < 100:
            return "red"
        elif r < 100 and g > 150 and b < 100:
            return "green"
        elif r < 100 and g < 100 and b > 150:
            return "blue"
        elif r > 150 and g > 150 and b < 100:
            return "yellow"
        elif r > 100 and g > 100 and b > 150:
            return "purple"
        elif r < 150 and g < 150 and b > 100:
            return "navy"
        elif 80 < r < 150 and 80 < g < 150 and 80 < b < 150:
            return "gray"
        elif r > 100 and g > 50 and b < 80:
            return "brown"
        else:
            return "multi-color"
    
    
    def _detect_pattern(self, img_array: np.ndarray) -> str:
        """
        Detect if image has pattern (stripes, dots, etc.)
        Simple variance-based approach
        """
        if img_array.shape[2] == 4:
            # Convert to grayscale (ignore alpha)
            gray = cv2.cvtColor(img_array[:, :, :3], cv2.COLOR_RGB2GRAY)
        else:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Calculate variance
        variance = np.var(gray)
        
        if variance < 100:
            return "solid"
        elif variance < 1000:
            return "subtle-pattern"
        else:
            return "patterned"
    
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')



# Helper functions for wardrobe integration
def create_wardrobe_items_from_extraction(
    db,
    user_id: int,
    extraction_results: Dict[str, Any]
) -> List[int]:
    """
    Create wardrobe items from extracted items
    
    Returns list of created item IDs
    """
    from interaction_models import UserInteraction
    
    created_ids = []
    
    for item in extraction_results["items"]:
        # In production, save to actual wardrobe table
        # For now, create interaction to track the upload
        
        interaction = UserInteraction(
            user_id=user_id,
            action_type="wardrobe_add",
            item_id=item["item_id"],
            item_type="product",
            weight=15.0,  # High weight for items user owns
            interaction_metadata={
                "category": item["category"],
                "attributes": item["detected_attributes"],
                "source": "outfit_photo_extraction",
                "segmented_image": item["segmented_image"][:100]  # Store reference
            }
        )
        db.add(interaction)
        created_ids.append(item["item_id"])
    
    db.commit()
    return created_ids
