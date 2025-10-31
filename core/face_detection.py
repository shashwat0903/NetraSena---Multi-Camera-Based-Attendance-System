import os
import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from insightface.data import get_image as ins_get_image
from loguru import logger
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from PIL import Image
from pathlib import Path
import time

@dataclass
class Face:
    bbox: np.ndarray  # [x1, y1, x2, y2]
    kps: np.ndarray   # 5 key points
    det_score: float  # detection score
    embedding: np.ndarray
    age: Optional[int] = None
    gender: Optional[str] = None  # 'Male' or 'Female'
    face_img: Optional[np.ndarray] = None

@dataclass
class KnownFace:
    name: str
    embedding: np.ndarray
    image_path: str
    is_suspect: bool = False

class FaceDetector:
    def __init__(self, config: dict):
        self.config = config
        self.recognition_threshold = config['recognition']['recognition_threshold']
        self.detection_threshold = config['recognition']['detection_threshold']
        self.max_batch_size = config['recognition']['max_batch_size']
        self.device = config['recognition']['device']
        self.analysis_enabled = config['recognition'].get('analysis_enabled', True)
        self.model = self._load_model()
        self.known_faces: List[KnownFace] = []
        self.suspects: List[KnownFace] = []
        
    def _load_model(self) -> FaceAnalysis:
        """Load Model insightface"""
        try:
            model = FaceAnalysis(
                name='buffalo_l',
                root='./models',
                allowed_modules=['detection', 'recognition', 'genderage']
            )
            model.prepare(
                ctx_id=0 if self.device == 'cuda' else -1,
                det_thresh=self.detection_threshold,
                det_size=(640, 640)
            )
            logger.success("Face detection model loaded successfully")
            return model
        except Exception as e:
            logger.error(f"Failed to load face detection model: {e}")
            raise

    def load_known_faces(self, known_faces_dir: str) -> None:
        """Load known faces from directory"""
        try:
            self.known_faces.clear()
            known_faces_dir = Path(known_faces_dir)
            
            if not known_faces_dir.exists():
                logger.warning(f"Known faces directory {known_faces_dir} does not exist")
                return
                
            for face_file in known_faces_dir.glob('*.*'):
                if face_file.suffix.lower() not in ['.jpg', '.jpeg', '.png']:
                    continue
                    
                try:
                    img = cv2.imread(str(face_file))
                    if img is None:
                        logger.warning(f"Could not read image {face_file}")
                        continue
                        
                    faces = self.model.get(img)
                    if len(faces) == 0:
                        logger.warning(f"No faces found in {face_file}")
                        continue
                        
                    # Use the first face found in the image
                    face = faces[0]
                    name = face_file.stem
                    self.known_faces.append(KnownFace(
                        name=name,
                        embedding=face.embedding,
                        image_path=str(face_file)
                    ))
                    logger.info(f"Loaded known face: {name}")
                    
                except Exception as e:
                    logger.error(f"Error processing {face_file}: {e}")
                    
            logger.info(f"Loaded {len(self.known_faces)} known faces")
            
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")
            raise

    def load_suspects(self, suspects_dir: str) -> None:
        """Load suspect faces from directory"""
        try:
            self.suspects.clear()
            suspects_dir = Path(suspects_dir)
            
            if not suspects_dir.exists():
                logger.warning(f"Suspects directory {suspects_dir} does not exist")
                return
                
            for face_file in suspects_dir.glob('*.*'):
                if face_file.suffix.lower() not in ['.jpg', '.jpeg', '.png']:
                    continue
                    
                try:
                    img = cv2.imread(str(face_file))
                    if img is None:
                        logger.warning(f"Could not read image {face_file}")
                        continue
                        
                    faces = self.model.get(img)
                    if len(faces) == 0:
                        logger.warning(f"No faces found in {face_file}")
                        continue
                        
                    # Use the first face found in the image
                    face = faces[0]
                    name = face_file.stem
                    self.suspects.append(KnownFace(
                        name=name,
                        embedding=face.embedding,
                        image_path=str(face_file),
                        is_suspect=True
                    ))
                    logger.info(f"Loaded suspect: {name}")
                    
                except Exception as e:
                    logger.error(f"Error processing suspect {face_file}: {e}")
                    
            logger.info(f"Loaded {len(self.suspects)} suspects")
            
        except Exception as e:
            logger.error(f"Error loading suspects: {e}")
            raise

    def detect_faces(self, image: np.ndarray) -> List[Face]:
        """Detect faces in an image"""
        try:
            # Use the model to detect faces
            faces = self.model.get(image)
            results = []
            
            for face in faces:
                try:
                    # Basic size filtering for very small faces
                    bbox = face.bbox.astype(int)
                    x, y, x2, y2 = bbox
                    w, h = x2 - x, y2 - y
                    
                    # Filter out very small faces - reduced threshold for IP cameras
                    if w < 10 or h < 10:
                        continue
                    
                    face_img = self._extract_face_image(image, face.bbox)

                    results.append(Face(
                        bbox=face.bbox,
                        kps=face.kps,
                        det_score=face.det_score,
                        embedding=face.embedding,
                        age=self._get_age(face),
                        gender=self._get_gender(face),
                        face_img=face_img
                    ))
                except Exception as e:
                    logger.error(f"Error processing face: {e}")
                    continue
                    
            return results
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []

    def recognize_faces(self, faces: List[Face]) -> List[Tuple[Face, Optional[KnownFace], float]]:
        """Recognize faces against known faces database"""
        results = []
        
        if not self.known_faces:
            return [(face, None, 0.0) for face in faces]
            
        try:
            # Get all known face embeddings
            known_embeddings = np.array([kf.embedding for kf in self.known_faces])
            
            for face in faces:
                if face.embedding is None or len(face.embedding) == 0:
                    results.append((face, None, 0.0))
                    continue
                    
                # Calculate cosine similarity between current face and all known faces
                similarities = np.dot(known_embeddings, face.embedding) / (
                    np.linalg.norm(known_embeddings, axis=1) * np.linalg.norm(face.embedding)
                )
                
                max_idx = np.argmax(similarities)
                max_similarity = similarities[max_idx]
                
                if max_similarity > self.recognition_threshold:
                    results.append((face, self.known_faces[max_idx], max_similarity))
                else:
                    results.append((face, None, max_similarity))
                    
        except Exception as e:
            logger.error(f"Error recognizing faces: {e}")
            return [(face, None, 0.0) for face in faces]
            
        return results

    def recognize_faces_with_suspects(self, faces: List[Face]) -> List[Tuple[Face, Optional[KnownFace], float, bool]]:
        """Recognize faces against both known faces and suspects database"""
        results = []
        
        # Combine known faces and suspects for recognition
        all_faces = self.known_faces + self.suspects
        
        if not all_faces:
            return [(face, None, 0.0, False) for face in faces]
            
        try:
            # Get all embeddings
            all_embeddings = np.array([kf.embedding for kf in all_faces])
            
            for face in faces:
                if face.embedding is None or len(face.embedding) == 0:
                    results.append((face, None, 0.0, False))
                    continue
                    
                # Calculate cosine similarity between current face and all faces
                similarities = np.dot(all_embeddings, face.embedding) / (
                    np.linalg.norm(all_embeddings, axis=1) * np.linalg.norm(face.embedding)
                )
                
                max_idx = np.argmax(similarities)
                max_similarity = similarities[max_idx]
                
                if max_similarity > self.recognition_threshold:
                    matched_face = all_faces[max_idx]
                    is_suspect = matched_face.is_suspect
                    results.append((face, matched_face, max_similarity, is_suspect))
                else:
                    results.append((face, None, max_similarity, False))
                    
        except Exception as e:
            logger.error(f"Error recognizing faces with suspects: {e}")
            return [(face, None, 0.0, False) for face in faces]
            
        return results

    def _extract_face_image(self, image: np.ndarray, bbox: np.ndarray) -> np.ndarray:
        """Extract face region from image"""
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(image.shape[1], x2)
        y2 = min(image.shape[0], y2)
        
        if x1 >= x2 or y1 >= y2:
            return np.array([])
            
        return image[y1:y2, x1:x2].copy()

    def add_known_face(self, image: np.ndarray, name: str, save_dir: str) -> bool:
        """Add a new known face to the database"""
        try:
            save_dir = Path(save_dir)
            save_dir.mkdir(parents=True, exist_ok=True)
            
            faces = self.detect_faces(image)
            if not faces:
                logger.warning("No faces found in the provided image")
                return False
                
            # Use the first face found
            face = faces[0]
            
            # Save the face image
            timestamp = int(time.time())
            face_path = save_dir / f"{name}_{timestamp}.jpg"
            cv2.imwrite(str(face_path), image)
            
            # Add to known faces
            self.known_faces.append(KnownFace(
                name=name,
                embedding=face.embedding,
                image_path=str(face_path)
            ))
            
            logger.info(f"Added new known face: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding known face: {e}")
            return False
    
    def add_suspect(self, image: np.ndarray, name: str, suspects_dir: str) -> bool:
        """Add a new suspect face to the suspects directory"""
        try:
            suspects_dir = Path(suspects_dir)
            suspects_dir.mkdir(parents=True, exist_ok=True)
            
            # Detect face in the image
            faces = self.model.get(image)
            if len(faces) == 0:
                logger.warning("No faces found in the image")
                return False
                
            # Use the first detected face
            face = faces[0]
            
            # Save image
            image_path = suspects_dir / f"{name}.jpg"
            cv2.imwrite(str(image_path), image)
            
            # Add to suspects list
            self.suspects.append(KnownFace(
                name=name,
                embedding=face.embedding,
                image_path=str(image_path),
                is_suspect=True
            ))
            
            logger.info(f"Suspect '{name}' added successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error adding suspect: {e}")
            return False

    def remove_suspect(self, name: str) -> bool:
        """Remove a suspect by name"""
        try:
            # Find and remove from suspects list
            for i, suspect in enumerate(self.suspects):
                if suspect.name == name:
                    # Remove image file if it exists
                    image_path = Path(suspect.image_path)
                    if image_path.exists():
                        image_path.unlink()
                    
                    # Remove from list
                    self.suspects.pop(i)
                    logger.info(f"Suspect '{name}' removed successfully")
                    return True
                    
            logger.warning(f"Suspect '{name}' not found")
            return False
            
        except Exception as e:
            logger.error(f"Error removing suspect: {e}")
            return False

    def _get_age(self, face) -> Optional[int]:
        """Extract age estimation if available"""
        if not self.analysis_enabled:
            return None
        return int(face.age) if hasattr(face, 'age') else None
    

    def _get_gender(self, face) -> Optional[str]:
        """Extract gender prediction if available"""
        if not self.analysis_enabled:
            return None
        if not hasattr(face, 'sex') or face.sex is None:
            return None
        return 'Female' if np.argmax(face.sex) == 1 else 'Male'

    def detect_faces_enhanced(self, image: np.ndarray) -> List[Face]:
        """Enhanced face detection optimized for IP camera feeds"""
        try:
            # First try with original image - don't over-process
            faces = self.model.get(image)
            
            if not faces:
                # If no faces found, try with preprocessing
                # 1. Improve contrast slightly
                enhanced_frame = cv2.convertScaleAbs(image, alpha=1.1, beta=10)
                
                # 2. Try detection on enhanced frame
                faces = self.model.get(enhanced_frame)
            
            results = []
            
            for face in faces:
                try:
                    # Calculate bounding box
                    bbox = face.bbox.astype(int)
                    x, y, x2, y2 = bbox
                    w, h = x2 - x, y2 - y
                    
                    # Filter out very small faces (likely false positives)
                    # Reduced threshold for IP cameras with lower resolution
                    if w < 15 or h < 15:
                        continue
                    
                    # Extract face image
                    face_img = self._extract_face_image(image, face.bbox)

                    results.append(Face(
                        bbox=face.bbox,
                        kps=face.kps,
                        det_score=face.det_score,
                        embedding=face.embedding,
                        age=self._get_age(face),
                        gender=self._get_gender(face),
                        face_img=face_img
                    ))
                    
                except Exception as e:
                    logger.error(f"Error processing detected face: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error in enhanced face detection: {e}")
            return []
            
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better face detection on IP cameras"""
        try:
            # Convert to RGB if needed
            if len(image.shape) == 3 and image.shape[2] == 3:
                # Improve contrast and brightness for better detection
                # Convert to LAB color space for better processing
                lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                
                # Apply CLAHE to L channel
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                l = clahe.apply(l)
                
                # Merge channels back
                enhanced = cv2.merge([l, a, b])
                enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
                
                # Slight sharpening
                kernel = np.array([[-1,-1,-1],
                                 [-1, 9,-1],
                                 [-1,-1,-1]])
                enhanced = cv2.filter2D(enhanced, -1, kernel)
                
                return enhanced
            else:
                return image
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return image
