"""
Checksum Utilities - File integrity verification
Generate and verify checksums for exported files
"""
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FileChecksum:
    """
    Generate and verify file checksums for data integrity
    
    Creates .checksum files alongside exported data files
    """
    
    ALGORITHM = 'sha256'  # More secure than MD5
    CHUNK_SIZE = 8192  # Read files in 8KB chunks
    
    @classmethod
    def calculate_checksum(cls, filepath: Path, algorithm: str = None) -> str:
        """
        Calculate checksum of a file
        
        Args:
            filepath: Path to the file
            algorithm: Hash algorithm ('md5', 'sha256')
            
        Returns:
            Hex digest of the file
        """
        algorithm = algorithm or cls.ALGORITHM
        
        if algorithm == 'md5':
            hasher = hashlib.md5()
        elif algorithm == 'sha256':
            hasher = hashlib.sha256()
        else:
            hasher = hashlib.sha256()
        
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(cls.CHUNK_SIZE), b''):
                    hasher.update(chunk)
            
            return hasher.hexdigest()
            
        except Exception as e:
            logger.error(f"Error calculating checksum for {filepath}: {e}")
            raise
    
    @classmethod
    def calculate_data_checksum(cls, data: any, algorithm: str = None) -> str:
        """
        Calculate checksum of data (dict, list, string)
        
        Args:
            data: Data to hash
            algorithm: Hash algorithm
            
        Returns:
            Hex digest
        """
        algorithm = algorithm or cls.ALGORITHM
        
        if algorithm == 'md5':
            hasher = hashlib.md5()
        else:
            hasher = hashlib.sha256()
        
        # Serialize data consistently
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, sort_keys=True, default=str)
        else:
            data_str = str(data)
        
        hasher.update(data_str.encode('utf-8'))
        
        return hasher.hexdigest()
    
    @classmethod
    def generate_checksum_file(cls, filepath: Path, 
                                extra_metadata: Dict = None) -> Path:
        """
        Generate a checksum file for the given file
        
        Args:
            filepath: Path to the file
            extra_metadata: Additional metadata to store
            
        Returns:
            Path to the checksum file
        """
        filepath = Path(filepath)
        checksum_path = filepath.with_suffix(filepath.suffix + '.checksum')
        
        try:
            checksum = cls.calculate_checksum(filepath)
            file_size = filepath.stat().st_size
            
            checksum_data = {
                'filename': filepath.name,
                'algorithm': cls.ALGORITHM,
                'checksum': checksum,
                'file_size': file_size,
                'created_at': datetime.now().isoformat(),
                'verified': True
            }
            
            if extra_metadata:
                checksum_data['metadata'] = extra_metadata
            
            with open(checksum_path, 'w') as f:
                json.dump(checksum_data, f, indent=2)
            
            logger.info(f"Generated checksum file: {checksum_path.name}")
            
            return checksum_path
            
        except Exception as e:
            logger.error(f"Error generating checksum file: {e}")
            raise
    
    @classmethod
    def verify_checksum(cls, filepath: Path) -> Tuple[bool, Optional[str]]:
        """
        Verify file against its checksum file
        
        Args:
            filepath: Path to the file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        filepath = Path(filepath)
        checksum_path = filepath.with_suffix(filepath.suffix + '.checksum')
        
        if not checksum_path.exists():
            return True, "No checksum file found (skipped verification)"
        
        try:
            with open(checksum_path, 'r') as f:
                checksum_data = json.load(f)
            
            expected_checksum = checksum_data.get('checksum')
            expected_size = checksum_data.get('file_size')
            algorithm = checksum_data.get('algorithm', cls.ALGORITHM)
            
            # Check file size first (fast)
            actual_size = filepath.stat().st_size
            if expected_size and actual_size != expected_size:
                return False, f"File size mismatch: expected {expected_size}, got {actual_size}"
            
            # Calculate and compare checksum
            actual_checksum = cls.calculate_checksum(filepath, algorithm)
            
            if actual_checksum != expected_checksum:
                return False, f"Checksum mismatch: expected {expected_checksum[:16]}..., got {actual_checksum[:16]}..."
            
            logger.info(f"Checksum verified for {filepath.name}")
            return True, None
            
        except Exception as e:
            return False, f"Verification error: {e}"
    
    @classmethod
    def verify_and_load(cls, filepath: Path, loader_func: callable) -> Tuple[any, bool, Optional[str]]:
        """
        Verify checksum and load file if valid
        
        Args:
            filepath: Path to the file
            loader_func: Function to load the file (e.g., json.load)
            
        Returns:
            Tuple of (data, is_valid, error_message)
        """
        is_valid, error = cls.verify_checksum(filepath)
        
        if not is_valid and error and "No checksum file" not in error:
            logger.warning(f"File verification failed: {error}")
            # Still try to load, but warn user
        
        try:
            data = loader_func(filepath)
            return data, is_valid, error
        except Exception as e:
            return None, False, f"Load error: {e}"


def generate_export_checksum(filepath: Path, record_count: int = None) -> Path:
    """
    Convenience function to generate checksum with export metadata
    
    Args:
        filepath: Path to exported file
        record_count: Number of records in the file
        
    Returns:
        Path to checksum file
    """
    metadata = {}
    if record_count is not None:
        metadata['record_count'] = record_count
    
    return FileChecksum.generate_checksum_file(filepath, metadata)


def verify_export_file(filepath: Path) -> Tuple[bool, str]:
    """
    Convenience function to verify an export file
    
    Args:
        filepath: Path to file
        
    Returns:
        Tuple of (is_valid, message)
    """
    is_valid, error = FileChecksum.verify_checksum(filepath)
    
    if is_valid and not error:
        return True, "✓ File integrity verified"
    elif is_valid and error:
        return True, error  # No checksum file found
    else:
        return False, f"✗ {error}"
