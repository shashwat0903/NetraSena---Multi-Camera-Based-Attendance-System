"""
Static Face Tracker - Prevents repeated detections of the same person
"""
import time
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from loguru import logger

@dataclass
class TrackedFace:
    """Represents a face being tracked"""
    person_id: str
    name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    last_seen: float
    is_suspect: bool = False
    age: int = 0
    gender: str = "Unknown"
    detection_count: int = 1

class StaticFaceTracker:
    """
    Tracks faces across frames to prevent repeated detections
    Maintains static detection until person leaves the frame
    """
    
    def __init__(self, timeout_seconds: int = 30, min_detection_confidence: float = 0.6):
        self.timeout_seconds = timeout_seconds
        self.min_detection_confidence = min_detection_confidence
        self.tracked_faces: Dict[int, Dict[str, TrackedFace]] = {}  # camera_id -> {person_id: TrackedFace}
        self.detection_cooldown = 5.0  # seconds before allowing re-detection of same person
        
    def update_tracking(self, camera_id: int, detected_faces: List[Tuple]) -> List[TrackedFace]:
        """
        Update tracking with new detections
        Returns list of tracked faces (only newly detected or confirmed existing)
        """
        current_time = time.time()
        
        # Initialize camera tracking if not exists
        if camera_id not in self.tracked_faces:
            self.tracked_faces[camera_id] = {}
        
        camera_tracks = self.tracked_faces[camera_id]
        
        # Remove expired tracks
        self._cleanup_expired_tracks(camera_id, current_time)
        
        # Process new detections
        new_or_updated_faces = []
        
        for face_data in detected_faces:
            if len(face_data) >= 4:  # face, known_face, confidence, is_suspect
                face, known_face, confidence, is_suspect = face_data[:4]
                
                if confidence < self.min_detection_confidence:
                    continue
                    
                if known_face is None:
                    continue  # Skip unknown faces for static tracking
                    
                person_name = known_face.name
                bbox = face.bbox
                
                # Check if this person is already being tracked
                existing_track = self._find_existing_track(camera_tracks, person_name, bbox)
                
                if existing_track:
                    # Update existing track
                    existing_track.last_seen = current_time
                    existing_track.bbox = bbox
                    existing_track.confidence = max(existing_track.confidence, confidence)
                    existing_track.detection_count += 1
                    
                    # Only return if enough time has passed since last alert
                    if current_time - existing_track.last_seen > self.detection_cooldown:
                        new_or_updated_faces.append(existing_track)
                        existing_track.last_seen = current_time  # Reset cooldown
                else:
                    # Create new track
                    person_id = f"{person_name}_{camera_id}_{int(current_time)}"
                    new_track = TrackedFace(
                        person_id=person_id,
                        name=person_name,
                        confidence=confidence,
                        bbox=bbox,
                        last_seen=current_time,
                        is_suspect=is_suspect,
                        age=getattr(face, 'age', 0),
                        gender=getattr(face, 'gender', 'Unknown')
                    )
                    
                    camera_tracks[person_id] = new_track
                    new_or_updated_faces.append(new_track)
                    
                    logger.info(f"New face tracked: {person_name} on camera {camera_id}")
        
        return new_or_updated_faces
    
    def _find_existing_track(self, camera_tracks: Dict[str, TrackedFace], person_name: str, bbox: Tuple[int, int, int, int]) -> Optional[TrackedFace]:
        """Find if person is already being tracked based on name and position"""
        for track in camera_tracks.values():
            if track.name == person_name:
                # Check if bounding boxes overlap significantly
                if self._bbox_overlap_ratio(track.bbox, bbox) > 0.3:
                    return track
        return None
    
    def _bbox_overlap_ratio(self, bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> float:
        """Calculate overlap ratio between two bounding boxes"""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Calculate intersection
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        
        if x_right <= x_left or y_bottom <= y_top:
            return 0.0
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        bbox1_area = w1 * h1
        bbox2_area = w2 * h2
        union_area = bbox1_area + bbox2_area - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0.0
    
    def _cleanup_expired_tracks(self, camera_id: int, current_time: float):
        """Remove tracks that haven't been seen for too long"""
        if camera_id not in self.tracked_faces:
            return
            
        expired_tracks = []
        for person_id, track in self.tracked_faces[camera_id].items():
            if current_time - track.last_seen > self.timeout_seconds:
                expired_tracks.append(person_id)
        
        for person_id in expired_tracks:
            removed_track = self.tracked_faces[camera_id].pop(person_id)
            logger.info(f"Removed expired track: {removed_track.name} from camera {camera_id}")
    
    def get_active_tracks(self, camera_id: int) -> List[TrackedFace]:
        """Get all currently active tracks for a camera"""
        if camera_id not in self.tracked_faces:
            return []
        return list(self.tracked_faces[camera_id].values())
    
    def clear_camera_tracks(self, camera_id: int):
        """Clear all tracks for a specific camera"""
        if camera_id in self.tracked_faces:
            self.tracked_faces[camera_id].clear()
            logger.info(f"Cleared all tracks for camera {camera_id}")
    
    def clear_all_tracks(self):
        """Clear all tracks for all cameras"""
        self.tracked_faces.clear()
        logger.info("Cleared all face tracks")
    
    def get_track_info(self, camera_id: int) -> Dict:
        """Get tracking information for a camera"""
        if camera_id not in self.tracked_faces:
            return {"active_tracks": 0, "tracked_people": []}
        
        tracks = self.tracked_faces[camera_id]
        return {
            "active_tracks": len(tracks),
            "tracked_people": [{"name": track.name, "confidence": track.confidence, "last_seen": track.last_seen} for track in tracks.values()]
        }
