import sqlite3
import time
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Dict
from pathlib import Path
from loguru import logger
import pandas as pd

@dataclass
class EntryExitEvent:
    person_name: str
    event_type: str  # 'entry' or 'exit'
    camera_id: int
    camera_name: str
    timestamp: float
    confidence: float
    session_id: Optional[str] = None
    duration_minutes: Optional[float] = None

@dataclass
class PersonSession:
    person_name: str
    entry_time: float
    entry_camera: int
    exit_time: Optional[float] = None
    exit_camera: Optional[int] = None
    duration_minutes: Optional[float] = None
    session_id: str = None

class EntryExitTracker:
    """Tracks person entry and exit events with duration calculation"""
    
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.active_sessions: Dict[str, PersonSession] = {}
        self.entry_camera_id = 1  # CP Plus Camera 1 (Entry Gate)
        self.exit_camera_id = 2   # CP Plus Camera 2 (Exit Gate)
        self.init_database()
    
    def init_database(self):
        """Initialize the entry/exit tracking database tables"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Create entry_exit_events table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS entry_exit_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        person_name TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        camera_id INTEGER NOT NULL,
                        camera_name TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        confidence REAL NOT NULL,
                        session_id TEXT,
                        duration_minutes REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create person_sessions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS person_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        person_name TEXT NOT NULL,
                        session_id TEXT UNIQUE NOT NULL,
                        entry_time REAL NOT NULL,
                        entry_camera INTEGER NOT NULL,
                        exit_time REAL,
                        exit_camera INTEGER,
                        duration_minutes REAL,
                        status TEXT DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create person_statistics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS person_statistics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        person_name TEXT UNIQUE NOT NULL,
                        total_entries INTEGER DEFAULT 0,
                        total_exits INTEGER DEFAULT 0,
                        total_duration_minutes REAL DEFAULT 0,
                        average_duration_minutes REAL DEFAULT 0,
                        last_entry_time REAL,
                        last_exit_time REAL,
                        current_status TEXT DEFAULT 'outside',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("Entry/Exit tracking database initialized")
                
                # Verify tables exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                logger.info(f"Database tables: {[table[0] for table in tables]}")
                
        except Exception as e:
            logger.error(f"Error initializing entry/exit database: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def process_detection(self, person_name: str, camera_id: int, camera_name: str, confidence: float):
        """Process a face detection for entry/exit tracking"""
        try:
            current_time = time.time()
            logger.info(f"Processing entry/exit detection: {person_name} on camera {camera_id} ({camera_name}) with confidence {confidence:.2f}")
            
            if camera_id == self.entry_camera_id:
                logger.info(f"Entry gate detection for {person_name}")
                self._handle_entry(person_name, camera_id, camera_name, confidence, current_time)
            elif camera_id == self.exit_camera_id:
                logger.info(f"Exit gate detection for {person_name}")
                self._handle_exit(person_name, camera_id, camera_name, confidence, current_time)
            else:
                logger.debug(f"Detection on non-gate camera {camera_id}, ignoring for entry/exit tracking")
            
        except Exception as e:
            logger.error(f"Error processing entry/exit detection: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _handle_entry(self, person_name: str, camera_id: int, camera_name: str, confidence: float, timestamp: float):
        """Handle entry detection"""
        try:
            logger.info(f"Processing ENTRY for {person_name} at camera {camera_id} ({camera_name})")
            
            # Check if person already has an active session
            if person_name in self.active_sessions:
                # Person already inside - don't allow another entry until they exit
                logger.info(f"{person_name} already has active session - ignoring duplicate entry")
                return
            
            # Create new session
            session_id = f"{person_name}_{int(timestamp)}"
            session = PersonSession(
                person_name=person_name,
                entry_time=timestamp,
                entry_camera=camera_id,
                session_id=session_id
            )
            
            self.active_sessions[person_name] = session
            logger.info(f"Created new session {session_id} for {person_name}")
            
            # Log entry event
            self._log_event(EntryExitEvent(
                person_name=person_name,
                event_type='entry',
                camera_id=camera_id,
                camera_name=camera_name,
                timestamp=timestamp,
                confidence=confidence,
                session_id=session_id
            ))
            
            # Update statistics
            self._update_person_statistics(person_name, 'entry', timestamp)
            
            logger.info(f"✅ ENTRY RECORDED: {person_name} entered through {camera_name} at {datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}")
            
        except Exception as e:
            logger.error(f"Error handling entry for {person_name}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _handle_exit(self, person_name: str, camera_id: int, camera_name: str, confidence: float, timestamp: float):
        """Handle exit detection"""
        try:
            logger.info(f"Processing EXIT for {person_name} at camera {camera_id} ({camera_name})")
            
            if person_name not in self.active_sessions:
                # Person not found in active sessions - can't exit without entry
                logger.warning(f"Exit detected for {person_name} but no active session found - ignoring")
                return
            
            # Complete the session
            session = self.active_sessions[person_name]
            
            session.exit_time = timestamp
            session.exit_camera = camera_id
            session.duration_minutes = (timestamp - session.entry_time) / 60
            
            logger.info(f"Session duration for {person_name}: {session.duration_minutes:.1f} minutes")
            
            # Log exit event
            self._log_event(EntryExitEvent(
                person_name=person_name,
                event_type='exit',
                camera_id=camera_id,
                camera_name=camera_name,
                timestamp=timestamp,
                confidence=confidence,
                session_id=session.session_id,
                duration_minutes=session.duration_minutes
            ))
            
            # Update database session
            self._save_completed_session(session)
            
            # Update statistics
            self._update_person_statistics(person_name, 'exit', timestamp, session.duration_minutes)
            
            # Remove from active sessions
            del self.active_sessions[person_name]
            
            logger.info(f"✅ EXIT RECORDED: {person_name} exited through {camera_name} after {session.duration_minutes:.1f} minutes")
            
        except Exception as e:
            logger.error(f"Error handling exit for {person_name}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _log_event(self, event: EntryExitEvent):
        """Log entry/exit event to database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO entry_exit_events 
                    (person_name, event_type, camera_id, camera_name, timestamp, confidence, session_id, duration_minutes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.person_name, event.event_type, event.camera_id, event.camera_name,
                    event.timestamp, event.confidence, event.session_id, event.duration_minutes
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging entry/exit event: {e}")
    
    def _save_completed_session(self, session: PersonSession):
        """Save completed session to database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO person_sessions 
                    (person_name, session_id, entry_time, entry_camera, exit_time, exit_camera, duration_minutes, status, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', CURRENT_TIMESTAMP)
                ''', (
                    session.person_name, session.session_id, session.entry_time, session.entry_camera,
                    session.exit_time, session.exit_camera, session.duration_minutes
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving session: {e}")
    
    def _complete_session_without_exit(self, person_name: str, current_time: float):
        """Complete a session when person enters again without recorded exit"""
        try:
            if person_name in self.active_sessions:
                session = self.active_sessions[person_name]
                session.duration_minutes = (current_time - session.entry_time) / 60
                
                # Save as incomplete session
                with sqlite3.connect(self.database_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO person_sessions 
                        (person_name, session_id, entry_time, entry_camera, duration_minutes, status, updated_at)
                        VALUES (?, ?, ?, ?, ?, 'incomplete', CURRENT_TIMESTAMP)
                    ''', (
                        session.person_name, session.session_id, session.entry_time, 
                        session.entry_camera, session.duration_minutes
                    ))
                    conn.commit()
                
                del self.active_sessions[person_name]
                logger.info(f"Completed incomplete session for {person_name}")
                
        except Exception as e:
            logger.error(f"Error completing incomplete session: {e}")
    
    def _update_person_statistics(self, person_name: str, event_type: str, timestamp: float, duration: Optional[float] = None):
        """Update person statistics"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Get existing statistics
                cursor.execute('SELECT * FROM person_statistics WHERE person_name = ?', (person_name,))
                stats = cursor.fetchone()
                
                if stats:
                    # Update existing statistics
                    if event_type == 'entry':
                        new_entries = stats[2] + 1
                        new_status = 'inside'
                        cursor.execute('''
                            UPDATE person_statistics 
                            SET total_entries = ?, last_entry_time = ?, current_status = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE person_name = ?
                        ''', (new_entries, timestamp, new_status, person_name))
                    
                    elif event_type == 'exit':
                        new_exits = stats[3] + 1
                        new_total_duration = stats[4] + (duration or 0)
                        new_avg_duration = new_total_duration / new_exits if new_exits > 0 else 0
                        new_status = 'outside'
                        
                        cursor.execute('''
                            UPDATE person_statistics 
                            SET total_exits = ?, total_duration_minutes = ?, average_duration_minutes = ?, 
                                last_exit_time = ?, current_status = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE person_name = ?
                        ''', (new_exits, new_total_duration, new_avg_duration, timestamp, new_status, person_name))
                
                else:
                    # Create new statistics record
                    if event_type == 'entry':
                        cursor.execute('''
                            INSERT INTO person_statistics 
                            (person_name, total_entries, last_entry_time, current_status)
                            VALUES (?, 1, ?, 'inside')
                        ''', (person_name, timestamp))
                    
                    elif event_type == 'exit':
                        cursor.execute('''
                            INSERT INTO person_statistics 
                            (person_name, total_exits, total_duration_minutes, average_duration_minutes, last_exit_time, current_status)
                            VALUES (?, 1, ?, ?, ?, 'outside')
                        ''', (person_name, duration or 0, duration or 0, timestamp))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating person statistics: {e}")
    
    def get_person_statistics(self, person_name: Optional[str] = None) -> List[Dict]:
        """Get person statistics"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                if person_name:
                    cursor.execute('SELECT * FROM person_statistics WHERE person_name = ?', (person_name,))
                else:
                    cursor.execute('SELECT * FROM person_statistics ORDER BY total_entries DESC')
                
                results = cursor.fetchall()
                
                columns = ['id', 'person_name', 'total_entries', 'total_exits', 'total_duration_minutes',
                          'average_duration_minutes', 'last_entry_time', 'last_exit_time', 'current_status', 'updated_at']
                
                return [dict(zip(columns, row)) for row in results]
                
        except Exception as e:
            logger.error(f"Error getting person statistics: {e}")
            return []
    
    def export_to_excel(self, output_path: str):
        """Export all entry/exit data to Excel file"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                # Export events
                events_df = pd.read_sql_query('''
                    SELECT person_name, event_type, camera_name, 
                           datetime(timestamp, 'unixepoch', 'localtime') as datetime,
                           confidence, duration_minutes, session_id
                    FROM entry_exit_events 
                    ORDER BY timestamp DESC
                ''', conn)
                
                # Export sessions
                sessions_df = pd.read_sql_query('''
                    SELECT person_name, session_id,
                           datetime(entry_time, 'unixepoch', 'localtime') as entry_datetime,
                           datetime(exit_time, 'unixepoch', 'localtime') as exit_datetime,
                           duration_minutes, status
                    FROM person_sessions 
                    ORDER BY entry_time DESC
                ''', conn)
                
                # Export statistics
                stats_df = pd.read_sql_query('''
                    SELECT person_name, total_entries, total_exits, 
                           total_duration_minutes, average_duration_minutes,
                           datetime(last_entry_time, 'unixepoch', 'localtime') as last_entry,
                           datetime(last_exit_time, 'unixepoch', 'localtime') as last_exit,
                           current_status
                    FROM person_statistics 
                    ORDER BY total_entries DESC
                ''', conn)
                
                # Write to Excel with multiple sheets
                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    events_df.to_excel(writer, sheet_name='Events', index=False)
                    sessions_df.to_excel(writer, sheet_name='Sessions', index=False)
                    stats_df.to_excel(writer, sheet_name='Statistics', index=False)
                
                logger.info(f"Entry/Exit data exported to {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            return False
    
    def get_current_occupants(self) -> List[str]:
        """Get list of people currently inside"""
        return list(self.active_sessions.keys())
    
    def get_system_status(self) -> Dict:
        """Get current system status for debugging"""
        try:
            status = {
                'active_sessions': len(self.active_sessions),
                'entry_camera_id': self.entry_camera_id,
                'exit_camera_id': self.exit_camera_id,
                'current_occupants': list(self.active_sessions.keys()),
                'session_details': {}
            }
            
            for person_name, session in self.active_sessions.items():
                status['session_details'][person_name] = {
                    'entry_time': datetime.fromtimestamp(session.entry_time).strftime('%H:%M:%S'),
                    'duration_so_far': f"{(time.time() - session.entry_time) / 60:.1f} minutes",
                    'session_id': session.session_id
                }
            
            return status
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}
    
    def cleanup_old_sessions(self, hours: int = 24):
        """Clean up sessions older than specified hours without exit"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (hours * 3600)
            
            to_remove = []
            for person_name, session in self.active_sessions.items():
                if session.entry_time < cutoff_time:
                    # Mark as incomplete and remove
                    self._complete_session_without_exit(person_name, current_time)
                    to_remove.append(person_name)
            
            for person_name in to_remove:
                if person_name in self.active_sessions:
                    del self.active_sessions[person_name]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old sessions")
                
        except Exception as e:
            logger.error(f"Error cleaning up old sessions: {e}")

    def clear_all_data(self):
        """Clear all entry/exit data from database and memory"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Clear all tables
                cursor.execute("DELETE FROM entry_exit_events")
                cursor.execute("DELETE FROM person_sessions") 
                cursor.execute("DELETE FROM person_statistics")
                
                conn.commit()
                
            # Clear active sessions in memory
            self.active_sessions.clear()
            
            logger.info("All entry/exit data cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing all data: {e}")
            return False
