"""
Item Extraction using Clarifai Fashion API
Professional-grade clothing detection
"""
from PIL import Image
from rembg import remove
import io
import base64
import numpy as np
from typing import List, Dict, Any
from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import resources_pb2, service_pb2, service_pb2_grpc
from clarifai_grpc.grpc.api.status import status_code_pb2


class ClarifaiExtractor:
    """
    Extract items using Clarifai Apparel Detection API
    $0.80 per 1,000 images - professional quality
    """
    
    def __init__(self, api_key: str = None):
        """Initialize Clarifai"""
        self.api_key = api_key or "YOUR_CLARIFAI_API_KEY"
        
        # Set up Clarifai client
        channel = ClarifaiChannel.get_grpc_channel()
        self.stub = service_pb2_grpc.V2Stub(channel)
        self.metadata = (('authorization', f'Key {self.api_key}'),)
        
        # Clarifai's pre-trained apparel model
        self.model_id = "apparel-detection"
        self.user_id = "clarifai"
        self.app_id = "main"
    
    async def extract_items_from_photo(
        self,
        image_data: bytes,
        user_id: int
    ) -> Dict[str, Any]:
        """Extract clothing items using Clarifai"""
        image = Image.open(io.BytesIO(image_data))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to bytes for Clarifai
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        
        # Call Clarifai API
        detections = await self._detect_with_clarifai(img_bytes)
        
        if not detections:
            return {
                "original_photo": self._image_to_base64(image),
                "items_detected": 0,
                "items": [],
                "error": "No clothing items detected"
            }
        
        # Process each detection
        items = []
        for idx, detection in enumerate(detections):
            bbox = detection['bounding_box']
            cropped = self._crop_region(image, bbox)
            segmented = await self._remove_background(cropped)
            attributes = self._extract_attributes_from_detection(detection)
            
            items.append({
                "item_id": f"clarifai-{detection['type']}-{idx+1:03d}",
                "category": detection['type'],
                "confidence": detection['confidence'],
                "bounding_box": bbox,
                "segmented_image": self._image_to_base64(segmented),
                "detected_attributes": attributes
            })
        
        return {
            "original_photo": self._image_to_base64(image),
            "items_detected": len(items),
            "items": items
        }
    
    async def _detect_with_clarifai(self, image_bytes: bytes) -> List[Dict]:
        """Call Clarifai Apparel Detection API"""
        request = service_pb2.PostModelOutputsRequest(
            user_app_id=resources_pb2.UserAppIDSet(
                user_id=self.user_id,
                app_id=self.app_id
            ),
            model_id=self.model_id,
            inputs=[
                resources_pb2.Input(
                    data=resources_pb2.Data(
                        image=resources_pb2.Image(
                            base64=image_bytes
                        )
                    )
                )
            ]
        )
        
        response = self.stub.PostModelOutputs(request, metadata=self.metadata)
        
        if response.status.code != status_code_pb2.SUCCESS:
            print(f"Clarifai API error: {response.status.description}")
            return []
        
        detections = []
        
        for region in response.outputs[0].data.regions:
            bbox_proto = region.region_info.bounding_box
            concepts = region.data.concepts
            if not concepts:
                continue
            
            top_concept = max(concepts, key=lambda c: c.value)
            
            detections.append({
                'type': self._map_clarifai_concept(top_concept.name),
                'confidence': top_concept.value,
                'bounding_box': [
                    bbox_proto.left_col,
                    bbox_proto.top_row,
                    bbox_proto.right_col,
                    bbox_proto.bottom_row
                ],
                'raw_concept': top_concept.name
            })
        
        return detections
    
    def _map_clarifai_concept(self, concept: str) -> str:
        """Map Clarifai concept names to our categories"""
        concept_lower = concept.lower()
        
        if any(x in concept_lower for x in ['shirt', 'top', 'blouse', 'sweater', 'hoodie']):
            return 'top'
        elif any(x in concept_lower for x in ['pants', 'jeans', 'trousers', 'skirt', 'shorts']):
            return 'bottom'
        elif any(x in concept_lower for x in ['dress', 'gown']):
            return 'dress'
        elif any(x in concept_lower for x in ['jacket', 'coat', 'blazer']):
            return 'outerwear'
        elif any(x in concept_lower for x in ['shoe', 'sneaker', 'boot', 'sandal']):
            return 'shoes'
        elif any(x in concept_lower for x in ['bag', 'purse', 'backpack', 'hat', 'belt']):
            return 'accessories'
        else:
            return 'other'
    
    def _crop_region(self, image: Image.Image, bbox: List[float]) -> Image.Image:
        """Crop region from image using normalized bbox"""
        width, height = image.size
        
        left = int(bbox[0] * width)
        top = int(bbox[1] * height)
        right = int(bbox[2] * width)
        bottom = int(bbox[3] * height)
        
        return image.crop((left, top, right, bottom))
    
    async def _remove_background(self, image: Image.Image) -> Image.Image:
        """Remove background using rembg"""
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        output = remove(img_byte_arr)
        return Image.open(io.BytesIO(output))
    
    def _extract_attributes_from_detection(self, detection: Dict) -> Dict[str, str]:
        """Extract attributes from Clarifai detection"""
        return {
            "color": "detected",
            "style": "casual",
            "pattern": "solid",
            "detected_as": detection['raw_concept']
        }
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert image to base64"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')


def create_wardrobe_items_from_extraction(db, user_id: int, extraction_results: Dict[str, Any]) -> List[int]:
    """Create wardrobe items from extraction"""
    from interaction_models import UserInteraction
    
    created_ids = []
    for item in extraction_results["items"]:
        interaction = UserInteraction(
            user_id=user_id,
            action_type="wardrobe_add",
            item_id=item["item_id"],
            item_type="product",
            weight=15.0,
            interaction_metadata={
                "category": item["category"],
                "attributes": item["detected_attributes"],
                "source": "outfit_photo_extraction"
            }
        )
        db.add(interaction)
        created_ids.append(item["item_id"])
    
    db.commit()
    return created_ids
