import sqlite3
import hashlib
import os
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from loguru import logger
import cv2
import numpy as np
from pathlib import Path

@dataclass
class User:
    user_id: str
    username: str
    password_hash: str
    role: str  # 'admin' or 'subadmin'
    assigned_cameras: List[int]  # List of camera IDs assigned to this user
    face_embedding: Optional[np.ndarray] = None
    face_image_path: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    is_active: bool = True

class UserDatabase:
    def __init__(self, db_path: str = "data/users.db"):
        self.db_path = db_path
        self.init_database()
        self.init_admin_user()
    
    def init_database(self):
        """Initialize the user database with necessary tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    assigned_cameras TEXT,  -- JSON string of camera IDs
                    face_embedding BLOB,
                    face_image_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Login sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS login_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    logout_time TIMESTAMP,
                    ip_address TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            conn.commit()
    
    def init_admin_user(self):
        """Initialize the default admin user"""
        admin_exists = self.get_user('admin')
        if not admin_exists:
            password_hash = self._hash_password('admin@123')
            self.create_user(
                user_id='admin',
                username='admin',
                password_hash=password_hash,
                role='admin',
                assigned_cameras=list(range(5))  # All cameras for admin
            )
            logger.info("Default admin user created")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, user_id: str, username: str, password_hash: str, 
                   role: str, assigned_cameras: List[int], 
                   face_embedding: Optional[np.ndarray] = None,
                   face_image_path: Optional[str] = None) -> bool:
        """Create a new user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Convert face embedding to bytes if provided
                embedding_bytes = None
                if face_embedding is not None:
                    embedding_bytes = face_embedding.tobytes()
                
                cursor.execute('''
                    INSERT INTO users (user_id, username, password_hash, role, 
                                     assigned_cameras, face_embedding, face_image_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, username, password_hash, role, 
                      json.dumps(assigned_cameras), embedding_bytes, face_image_path))
                
                conn.commit()
                logger.info(f"User {username} created successfully")
                return True
                
        except sqlite3.IntegrityError as e:
            logger.error(f"User creation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by user_id"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                
                if row:
                    # Convert face embedding back to numpy array if exists
                    face_embedding = None
                    if row[5]:  # face_embedding column
                        face_embedding = np.frombuffer(row[5], dtype=np.float32)
                    
                    return User(
                        user_id=row[0],
                        username=row[1],
                        password_hash=row[2],
                        role=row[3],
                        assigned_cameras=json.loads(row[4]),
                        face_embedding=face_embedding,
                        face_image_path=row[6],
                        created_at=datetime.fromisoformat(row[7]) if row[7] else None,
                        last_login=datetime.fromisoformat(row[8]) if row[8] else None,
                        is_active=bool(row[9])
                    )
                    
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
                row = cursor.fetchone()
                
                if row:
                    # Convert face embedding back to numpy array if exists
                    face_embedding = None
                    if row[5]:  # face_embedding column
                        face_embedding = np.frombuffer(row[5], dtype=np.float32)
                    
                    return User(
                        user_id=row[0],
                        username=row[1],
                        password_hash=row[2],
                        role=row[3],
                        assigned_cameras=json.loads(row[4]),
                        face_embedding=face_embedding,
                        face_image_path=row[6],
                        created_at=datetime.fromisoformat(row[7]) if row[7] else None,
                        last_login=datetime.fromisoformat(row[8]) if row[8] else None,
                        is_active=bool(row[9])
                    )
                    
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    
    def verify_password(self, user_id: str, password: str) -> bool:
        """Verify user password"""
        user = self.get_user(user_id)
        if user:
            return user.password_hash == self._hash_password(password)
        return False
    
    def update_user_face(self, user_id: str, face_embedding: np.ndarray, 
                        face_image_path: str) -> bool:
        """Update user's face embedding"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                embedding_bytes = face_embedding.tobytes()
                
                cursor.execute('''
                    UPDATE users SET face_embedding = ?, face_image_path = ?
                    WHERE user_id = ?
                ''', (embedding_bytes, face_image_path, user_id))
                
                conn.commit()
                logger.info(f"Face updated for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating user face: {e}")
            return False
    
    def update_last_login(self, user_id: str):
        """Update user's last login time"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
    
    def get_all_subadmins(self) -> List[User]:
        """Get all subadmin users"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE role = "subadmin" AND is_active = 1')
                rows = cursor.fetchall()
                
                users = []
                for row in rows:
                    face_embedding = None
                    if row[5]:  # face_embedding column
                        face_embedding = np.frombuffer(row[5], dtype=np.float32)
                    
                    users.append(User(
                        user_id=row[0],
                        username=row[1],
                        password_hash=row[2],
                        role=row[3],
                        assigned_cameras=json.loads(row[4]),
                        face_embedding=face_embedding,
                        face_image_path=row[6],
                        created_at=datetime.fromisoformat(row[7]) if row[7] else None,
                        last_login=datetime.fromisoformat(row[8]) if row[8] else None,
                        is_active=bool(row[9])
                    ))
                
                return users
                
        except Exception as e:
            logger.error(f"Error getting subadmins: {e}")
            return []
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                conn.commit()
                logger.info(f"User {user_id} deleted")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    def update_user_cameras(self, user_id: str, assigned_cameras: List[int]) -> bool:
        """Update user's assigned cameras"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET assigned_cameras = ?
                    WHERE user_id = ?
                ''', (json.dumps(assigned_cameras), user_id))
                conn.commit()
                logger.info(f"Updated cameras for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating user cameras: {e}")
            return False

class FaceAuthenticator:
    def __init__(self, face_detector, similarity_threshold: float = 0.7):
        self.face_detector = face_detector
        self.similarity_threshold = similarity_threshold
        self.user_db = UserDatabase()
    
    def authenticate_face(self, frame: np.ndarray) -> Optional[User]:
        """Authenticate user by face recognition"""
        try:
            # Detect faces in the frame
            faces = self.face_detector.detect_faces(frame)
            
            if not faces:
                return None
            
            # Use the first detected face
            face = faces[0]
            
            # Get all users with face embeddings
            all_users = self.user_db.get_all_subadmins()
            admin_user = self.user_db.get_user('admin')
            if admin_user and admin_user.face_embedding is not None:
                all_users.append(admin_user)
            
            # Compare with registered face embeddings
            for user in all_users:
                if user.face_embedding is not None:
                    # Calculate similarity
                    similarity = np.dot(face.embedding, user.face_embedding) / (
                        np.linalg.norm(face.embedding) * np.linalg.norm(user.face_embedding)
                    )
                    
                    if similarity > self.similarity_threshold:
                        logger.info(f"Face authenticated for user: {user.username}")
                        return user
            
            return None
            
        except Exception as e:
            logger.error(f"Error in face authentication: {e}")
            return None
    
    def register_user_face(self, user_id: str, frame: np.ndarray) -> bool:
        """Register user's face for authentication"""
        try:
            faces = self.face_detector.detect_faces(frame)
            
            if not faces:
                logger.warning("No faces detected for registration")
                return False
            
            # Use the first detected face
            face = faces[0]
            
            # Save face image
            face_dir = Path("data/user_faces")
            face_dir.mkdir(exist_ok=True)
            
            face_image_path = face_dir / f"{user_id}_face.jpg"
            cv2.imwrite(str(face_image_path), frame)
            
            # Update user's face embedding
            success = self.user_db.update_user_face(
                user_id, face.embedding, str(face_image_path)
            )
            
            if success:
                logger.info(f"Face registered for user: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error registering face: {e}")
            return False
