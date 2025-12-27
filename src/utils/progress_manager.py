"""
Progress Manager - Save and resume download progress
Enables recovery from interruptions and crashes
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Default cache directory
CACHE_DIR = Path(__file__).parent.parent.parent / '.cache' / 'progress'


class ProgressManager:
    """
    Manage progress state for resumable operations
    
    Saves checkpoint files to .cache/progress/ directory
    Allows resuming interrupted downloads
    """
    
    def __init__(self, operation_name: str, cache_dir: Path = None):
        """
        Initialize progress manager
        
        Args:
            operation_name: Unique identifier for this operation (e.g., 'socrata_franchise_tax')
            cache_dir: Directory to store progress files
        """
        self.operation_name = self._sanitize_name(operation_name)
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.progress_file = self.cache_dir / f'{self.operation_name}_progress.json'
        self.data_file = self.cache_dir / f'{self.operation_name}_partial.json'
        
        # State
        self.completed_ids: Set[str] = set()
        self.pending_ids: List[str] = []
        self.partial_results: List[Dict] = []
        self.metadata: Dict[str, Any] = {}
        self.started_at: Optional[datetime] = None
        self.last_checkpoint: Optional[datetime] = None
        
    def _sanitize_name(self, name: str) -> str:
        """Sanitize operation name for use as filename"""
        return "".join(c if c.isalnum() or c in '-_' else '_' for c in name)
    
    def has_saved_progress(self) -> bool:
        """Check if there is saved progress to resume"""
        return self.progress_file.exists()
    
    def get_progress_info(self) -> Optional[Dict[str, Any]]:
        """Get information about saved progress without loading full data"""
        if not self.has_saved_progress():
            return None
        
        try:
            with open(self.progress_file, 'r') as f:
                progress = json.load(f)
            
            return {
                'operation': progress.get('operation_name'),
                'started_at': progress.get('started_at'),
                'last_checkpoint': progress.get('last_checkpoint'),
                'completed_count': len(progress.get('completed_ids', [])),
                'pending_count': len(progress.get('pending_ids', [])),
                'partial_results_count': progress.get('partial_results_count', 0),
                'metadata': progress.get('metadata', {})
            }
        except Exception as e:
            logger.error(f"Error reading progress info: {e}")
            return None
    
    def load_progress(self) -> bool:
        """
        Load saved progress state
        
        Returns:
            True if progress was loaded successfully
        """
        if not self.has_saved_progress():
            logger.info(f"No saved progress found for {self.operation_name}")
            return False
        
        try:
            # Load progress state
            with open(self.progress_file, 'r') as f:
                progress = json.load(f)
            
            self.completed_ids = set(progress.get('completed_ids', []))
            self.pending_ids = progress.get('pending_ids', [])
            self.metadata = progress.get('metadata', {})
            self.started_at = progress.get('started_at')
            self.last_checkpoint = progress.get('last_checkpoint')
            
            # Load partial results
            if self.data_file.exists():
                with open(self.data_file, 'r') as f:
                    self.partial_results = json.load(f)
            
            logger.info(f"Loaded progress: {len(self.completed_ids)} completed, {len(self.pending_ids)} pending")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading progress: {e}")
            return False
    
    def save_progress(self) -> bool:
        """
        Save current progress state
        
        Returns:
            True if saved successfully
        """
        try:
            self.last_checkpoint = datetime.now().isoformat()
            
            # Save progress state
            progress = {
                'operation_name': self.operation_name,
                'started_at': self.started_at or datetime.now().isoformat(),
                'last_checkpoint': self.last_checkpoint,
                'completed_ids': list(self.completed_ids),
                'pending_ids': self.pending_ids,
                'partial_results_count': len(self.partial_results),
                'metadata': self.metadata
            }
            
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
            
            # Save partial results
            if self.partial_results:
                with open(self.data_file, 'w') as f:
                    json.dump(self.partial_results, f)
            
            logger.debug(f"Saved checkpoint: {len(self.completed_ids)} completed")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving progress: {e}")
            return False
    
    def start_operation(self, all_ids: List[str], metadata: Dict[str, Any] = None):
        """
        Start a new operation with given IDs
        
        Args:
            all_ids: All IDs to process
            metadata: Optional metadata about the operation
        """
        self.started_at = datetime.now().isoformat()
        self.pending_ids = list(all_ids)
        self.completed_ids = set()
        self.partial_results = []
        self.metadata = metadata or {}
        
        self.save_progress()
        
        logger.info(f"Started operation {self.operation_name} with {len(all_ids)} items")
    
    def mark_completed(self, item_id: str, result: Dict = None):
        """
        Mark an item as completed
        
        Args:
            item_id: ID that was processed
            result: Result data (optional, will be stored in partial results)
        """
        self.completed_ids.add(str(item_id))
        
        if result:
            self.partial_results.append(result)
        
        # Remove from pending if present
        if str(item_id) in self.pending_ids:
            self.pending_ids.remove(str(item_id))
    
    def mark_batch_completed(self, item_ids: List[str], results: List[Dict] = None):
        """
        Mark multiple items as completed
        
        Args:
            item_ids: IDs that were processed
            results: Result data list
        """
        for item_id in item_ids:
            self.completed_ids.add(str(item_id))
            if str(item_id) in self.pending_ids:
                self.pending_ids.remove(str(item_id))
        
        if results:
            self.partial_results.extend(results)
    
    def checkpoint(self, force: bool = False) -> bool:
        """
        Create a checkpoint (save progress)
        
        Args:
            force: Force save even if not enough progress
            
        Returns:
            True if checkpoint was created
        """
        # Auto-checkpoint every 100 items or when forced
        if force or len(self.completed_ids) % 100 == 0:
            return self.save_progress()
        return False
    
    def get_remaining_ids(self) -> List[str]:
        """Get IDs that still need to be processed"""
        return [id for id in self.pending_ids if id not in self.completed_ids]
    
    def get_partial_results(self) -> List[Dict]:
        """Get all partial results collected so far"""
        return self.partial_results
    
    def clear_progress(self) -> bool:
        """
        Clear saved progress (call after successful completion)
        
        Returns:
            True if cleared successfully
        """
        try:
            if self.progress_file.exists():
                self.progress_file.unlink()
            if self.data_file.exists():
                self.data_file.unlink()
            
            self.completed_ids = set()
            self.pending_ids = []
            self.partial_results = []
            
            logger.info(f"Cleared progress for {self.operation_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing progress: {e}")
            return False
    
    def get_completion_percentage(self) -> float:
        """Get completion percentage"""
        total = len(self.completed_ids) + len(self.pending_ids)
        if total == 0:
            return 0.0
        return (len(self.completed_ids) / total) * 100
    
    def get_stats(self) -> Dict[str, Any]:
        """Get progress statistics"""
        return {
            'operation': self.operation_name,
            'completed': len(self.completed_ids),
            'pending': len(self.pending_ids),
            'partial_results': len(self.partial_results),
            'completion_percentage': self.get_completion_percentage(),
            'started_at': self.started_at,
            'last_checkpoint': self.last_checkpoint
        }


def get_all_saved_progress(cache_dir: Path = None) -> List[Dict[str, Any]]:
    """
    Get info about all saved progress files
    
    Args:
        cache_dir: Cache directory to search
        
    Returns:
        List of progress info dictionaries
    """
    cache_dir = cache_dir or CACHE_DIR
    
    if not cache_dir.exists():
        return []
    
    progress_files = list(cache_dir.glob('*_progress.json'))
    results = []
    
    for pf in progress_files:
        try:
            with open(pf, 'r') as f:
                data = json.load(f)
            
            results.append({
                'file': pf.name,
                'operation': data.get('operation_name'),
                'started_at': data.get('started_at'),
                'last_checkpoint': data.get('last_checkpoint'),
                'completed': len(data.get('completed_ids', [])),
                'pending': len(data.get('pending_ids', []))
            })
        except:
            pass
    
    return results


def clear_all_progress(cache_dir: Path = None) -> int:
    """
    Clear all saved progress files
    
    Args:
        cache_dir: Cache directory
        
    Returns:
        Number of files cleared
    """
    cache_dir = cache_dir or CACHE_DIR
    
    if not cache_dir.exists():
        return 0
    
    count = 0
    for f in cache_dir.glob('*'):
        try:
            f.unlink()
            count += 1
        except:
            pass
    
    return count
