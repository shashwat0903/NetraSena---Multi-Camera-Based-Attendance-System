import time
import numpy as np
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from loguru import logger

@dataclass
class TrackedFace:
    """Represents a tracked face with stability"""
    person_id: str
    name: str
    is_suspect: bool
    confidence: float
    bbox: np.ndarray
    last_seen: float
    detection_count: int
    stable: bool = False
    alert_triggered: bool = False

class FaceTracker:
    """Handles face tracking and static detection"""
    
    def __init__(self, stability_threshold: int = 5, timeout_seconds: float = 10.0):
        self.stability_threshold = stability_threshold  # Frames needed for stable detection
        self.timeout_seconds = timeout_seconds  # Seconds before forgetting a face
        self.tracked_faces: Dict[int, Dict[str, TrackedFace]] = {}  # cam_id -> {person_id: TrackedFace}
        self.face_counter = 0
        
    def get_person_id(self, embedding: np.ndarray, cam_id: int) -> str:
        """Get or create a person ID based on face embedding"""
        current_time = time.time()
        
        # Clean up old tracked faces
        self._cleanup_old_faces(cam_id, current_time)
        
        if cam_id not in self.tracked_faces:
            self.tracked_faces[cam_id] = {}
            
        # Check if this face matches any existing tracked face
        for person_id, tracked_face in self.tracked_faces[cam_id].items():
            if tracked_face.last_seen + self.timeout_seconds > current_time:
                # Calculate similarity
                similarity = np.dot(embedding, tracked_face.bbox) / (
                    np.linalg.norm(embedding) * np.linalg.norm(tracked_face.bbox)
                )
                if similarity > 0.8:  # High similarity threshold for same person
                    return person_id
                    
        # Create new person ID
        self.face_counter += 1
        return f"person_{self.face_counter}"
        
    def update_tracked_face(self, cam_id: int, person_id: str, face, known_face, confidence: float, is_suspect: bool):
        """Update or create a tracked face"""
        current_time = time.time()
        
        if cam_id not in self.tracked_faces:
            self.tracked_faces[cam_id] = {}
            
        if person_id in self.tracked_faces[cam_id]:
            # Update existing tracked face
            tracked = self.tracked_faces[cam_id][person_id]
            tracked.last_seen = current_time
            tracked.bbox = face.bbox
            tracked.detection_count += 1
            tracked.confidence = max(tracked.confidence, confidence)
            
            # Mark as stable if detected enough times
            if tracked.detection_count >= self.stability_threshold:
                tracked.stable = True
                
        else:
            # Create new tracked face
            name = known_face.name if known_face else "Unknown"
            self.tracked_faces[cam_id][person_id] = TrackedFace(
                person_id=person_id,
                name=name,
                is_suspect=is_suspect,
                confidence=confidence,
                bbox=face.bbox,
                last_seen=current_time,
                detection_count=1,
                stable=False,
                alert_triggered=False
            )
            
    def should_trigger_alert(self, cam_id: int, person_id: str) -> bool:
        """Check if an alert should be triggered for this face"""
        if cam_id not in self.tracked_faces or person_id not in self.tracked_faces[cam_id]:
            return False
            
        tracked = self.tracked_faces[cam_id][person_id]
        
        # Only trigger alert once per detection session and only for stable faces
        if tracked.stable and not tracked.alert_triggered and tracked.name != "Unknown":
            tracked.alert_triggered = True
            return True
            
        return False
        
    def get_stable_faces(self, cam_id: int) -> List[TrackedFace]:
        """Get all stable faces for a camera"""
        if cam_id not in self.tracked_faces:
            return []
            
        current_time = time.time()
        stable_faces = []
        
        for tracked_face in self.tracked_faces[cam_id].values():
            if (tracked_face.stable and 
                tracked_face.last_seen + self.timeout_seconds > current_time):
                stable_faces.append(tracked_face)
                
        return stable_faces
        
    def _cleanup_old_faces(self, cam_id: int, current_time: float):
        """Remove old tracked faces that have timed out"""
        if cam_id not in self.tracked_faces:
            return
            
        to_remove = []
        for person_id, tracked_face in self.tracked_faces[cam_id].items():
            if tracked_face.last_seen + self.timeout_seconds < current_time:
                to_remove.append(person_id)
                
        for person_id in to_remove:
            del self.tracked_faces[cam_id][person_id]
            logger.debug(f"Removed old tracked face: {person_id} from camera {cam_id}")
            
    def get_face_count(self, cam_id: int) -> Tuple[int, int]:
        """Get count of total faces and suspects for a camera"""
        stable_faces = self.get_stable_faces(cam_id)
        total_faces = len(stable_faces)
        suspects = sum(1 for face in stable_faces if face.is_suspect)
        return total_faces, suspects
        
    def reset_camera(self, cam_id: int):
        """Reset tracking for a specific camera"""
        if cam_id in self.tracked_faces:
            del self.tracked_faces[cam_id]
            logger.info(f"Reset face tracking for camera {cam_id}")
