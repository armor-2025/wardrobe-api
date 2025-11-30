"""
Enhanced VTO with Hair + Face Preservation
"""
import os
import numpy as np
import cv2
from typing import Optional


class HairAndFaceSwapper:
    """Face swapper that includes hair region"""
    
    def __init__(self):
        self.app = None
        self.swapper = None
        self._initialized = False
    
    def initialize(self):
        """Lazy initialization"""
        if self._initialized:
            return
        
        try:
            from insightface.app import FaceAnalysis
            from insightface.model_zoo import get_model
            
            self.app = FaceAnalysis(name='buffalo_l')
            self.app.prepare(ctx_id=-1)
            
            self.swapper = get_model('inswapper_128.onnx', 
                                    download=True,
                                    download_zip=True)
            
            self._initialized = True
            print("✅ Hair + Face swapper initialized")
            
        except Exception as e:
            print(f"⚠️ Face swapper initialization failed: {e}")
    
    def expand_bbox_for_hair(self, bbox, img_shape):
        """Expand bounding box to include hair region"""
        x1, y1, x2, y2 = bbox
        
        face_width = x2 - x1
        face_height = y2 - y1
        
        # Expand upward for hair
        hair_expansion = face_height * 0.8
        side_expansion = face_width * 0.3
        
        new_x1 = max(0, int(x1 - side_expansion))
        new_y1 = max(0, int(y1 - hair_expansion))
        new_x2 = min(img_shape[1], int(x2 + side_expansion))
        new_y2 = int(y2)
        
        return [new_x1, new_y1, new_x2, new_y2]
    
    def swap_face_with_hair(self, source_image_bytes: bytes, target_image_bytes: bytes) -> Optional[bytes]:
        """Swap face + hair region from source to target"""
        if not self._initialized:
            self.initialize()
        
        if not self._initialized:
            return None
        
        try:
            source_arr = np.frombuffer(source_image_bytes, np.uint8)
            target_arr = np.frombuffer(target_image_bytes, np.uint8)
            
            source_img = cv2.imdecode(source_arr, cv2.IMREAD_COLOR)
            target_img = cv2.imdecode(target_arr, cv2.IMREAD_COLOR)
            
            source_faces = self.app.get(source_img)
            target_faces = self.app.get(target_img)
            
            if not source_faces or not target_faces:
                print("⚠️ No faces detected")
                return None
            
            source_face = source_faces[0]
            target_face = target_faces[0]
            
            # Standard face swap
            result_img = self.swapper.get(target_img, target_face, source_face, paste_back=True)
            
            # Blend hair region
            source_bbox = source_face.bbox.astype(int)
            target_bbox = target_face.bbox.astype(int)
            
            source_expanded = self.expand_bbox_for_hair(source_bbox, source_img.shape)
            target_expanded = self.expand_bbox_for_hair(target_bbox, target_img.shape)
            
            sx1, sy1, sx2, sy2 = source_expanded
            tx1, ty1, tx2, ty2 = target_expanded
            
            source_head = source_img[sy1:sy2, sx1:sx2]
            
            target_height = ty2 - ty1
            target_width = tx2 - tx1
            
            if target_height > 0 and target_width > 0:
                source_head_resized = cv2.resize(source_head, (target_width, target_height))
                
                mask = np.zeros((target_height, target_width), dtype=np.float32)
                center_x, center_y = target_width // 2, target_height // 2
                axes_x, axes_y = target_width // 2, target_height // 2
                
                cv2.ellipse(mask, (center_x, center_y), (axes_x, axes_y), 0, 0, 360, 1, -1)
                mask = cv2.GaussianBlur(mask, (51, 51), 0)
                mask = np.stack([mask] * 3, axis=2)
                
                roi = result_img[ty1:ty2, tx1:tx2]
                blended = (source_head_resized * mask + roi * (1 - mask)).astype(np.uint8)
                result_img[ty1:ty2, tx1:tx2] = blended
            
            _, buffer = cv2.imencode('.png', result_img)
            return buffer.tobytes()
            
        except Exception as e:
            print(f"⚠️ Hair + Face swap failed: {e}")
            import traceback
            traceback.print_exc()
            return None
