"""
GPU Acceleration Utilities for Data Processing
Optimized for NVIDIA RTX 3060 with CUDA/cuDNN
"""
import sys
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from src.utils.logger import get_logger
from config.settings import gpu_config

logger = get_logger(__name__)

# Try to import GPU libraries
CUPY_AVAILABLE = False
CUDF_AVAILABLE = False
POLARS_AVAILABLE = False
PYARROW_AVAILABLE = False

# Check for cupy (GPU arrays)
try:
    import cupy as cp
    CUPY_AVAILABLE = True
    logger.info("CuPy loaded - GPU array processing available")
except ImportError:
    pass

# Check for cudf (GPU DataFrames - Linux/WSL2 only)
try:
    import cudf
    CUDF_AVAILABLE = True
    logger.info("cuDF loaded - GPU DataFrame processing available")
except ImportError:
    pass

# Check for polars (fast CPU DataFrames - works on Windows)
try:
    import polars as pl
    POLARS_AVAILABLE = True
    logger.info("Polars loaded - fast DataFrame processing available")
except ImportError:
    pass

# Check for pyarrow (fast columnar data - works on Windows)
try:
    import pyarrow as pa
    PYARROW_AVAILABLE = True
    logger.info("PyArrow loaded - fast columnar processing available")
except ImportError:
    pass

# GPU is available if we have cupy (with optional cudf or polars for DataFrames)
GPU_AVAILABLE = CUPY_AVAILABLE
if GPU_AVAILABLE:
    if CUDF_AVAILABLE:
        logger.info("GPU mode: cupy + cudf (full GPU acceleration)")
    elif POLARS_AVAILABLE and PYARROW_AVAILABLE:
        logger.info("GPU mode: cupy + polars + pyarrow (GPU arrays + fast DataFrames)")
    elif POLARS_AVAILABLE:
        logger.info("GPU mode: cupy + polars (GPU arrays + fast DataFrames)")
    else:
        logger.info("GPU mode: cupy only (GPU array processing)")
else:
    if POLARS_AVAILABLE or PYARROW_AVAILABLE:
        logger.info("CPU mode with fast processing (polars/pyarrow available)")
    else:
        logger.warning("GPU libraries not available - using standard CPU processing")


class GPUAccelerator:
    """GPU-accelerated data processing"""
    
    def __init__(self, use_gpu: bool = None):
        """
        Initialize GPU accelerator
        
        Args:
            use_gpu: Whether to use GPU (None = auto-detect)
        """
        self.use_gpu = use_gpu if use_gpu is not None else gpu_config.USE_GPU
        self.gpu_available = GPU_AVAILABLE and self._check_gpu()
        
        if self.use_gpu and not self.gpu_available:
            logger.warning("GPU requested but not available, using CPU")
            self.use_gpu = False
        
        if self.use_gpu:
            self._initialize_gpu()
    
    def _check_gpu(self) -> bool:
        """Check if GPU is available and functional"""
        if not GPU_AVAILABLE:
            return False
        
        try:
            # Test GPU
            device = cp.cuda.Device(gpu_config.GPU_DEVICE_ID)
            device.compute_capability
            
            # Get GPU info
            props = cp.cuda.runtime.getDeviceProperties(gpu_config.GPU_DEVICE_ID)
            self.device_name = props['name'].decode()
            self.compute_capability = f"{props['major']}.{props['minor']}"
            self.total_memory_gb = props['totalGlobalMem'] / (1024**3)
            
            logger.info(f"GPU Detected: {self.device_name}")
            logger.info(f"Compute Capability: {self.compute_capability}")
            logger.info(f"Total Memory: {self.total_memory_gb:.2f} GB")
            
            return True
            
        except Exception as e:
            logger.error(f"GPU check failed: {e}")
            self.device_name = None
            self.compute_capability = None
            self.total_memory_gb = None
            return False
    
    def _initialize_gpu(self):
        """Initialize GPU settings"""
        try:
            # Set device
            cp.cuda.Device(gpu_config.GPU_DEVICE_ID).use()
            
            # Set memory pool limit
            mempool = cp.get_default_memory_pool()
            mempool.set_limit(size=gpu_config.GPU_MEMORY_LIMIT * 1024 * 1024)
            
            logger.info(f"GPU initialized on device {gpu_config.GPU_DEVICE_ID}")
            logger.info(f"Memory limit: {gpu_config.GPU_MEMORY_LIMIT} MB")
            
        except Exception as e:
            logger.error(f"GPU initialization failed: {e}")
            self.use_gpu = False
    
    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process DataFrame with GPU acceleration if available
        
        Args:
            df: Pandas DataFrame
            
        Returns:
            Processed DataFrame
        """
        if not self.use_gpu:
            return df
        
        try:
            # Convert to cuDF
            gdf = cudf.from_pandas(df)
            
            logger.debug(f"Converted DataFrame to GPU ({len(gdf)} rows)")
            
            # Perform GPU operations here
            # (This is a placeholder - add specific operations as needed)
            
            # Convert back to pandas
            result = gdf.to_pandas()
            
            return result
            
        except Exception as e:
            logger.error(f"GPU processing failed: {e}, falling back to CPU")
            return df
    
    def batch_process_records(self, 
                               records: List[Dict],
                               process_func: callable,
                               batch_size: int = 1000) -> List[Dict]:
        """
        Batch process records with GPU acceleration
        
        Args:
            records: List of records to process
            process_func: Function to apply to each batch
            batch_size: Size of each batch
            
        Returns:
            Processed records
        """
        if not self.use_gpu or not records:
            return [process_func(r) for r in records]
        
        try:
            # Convert to DataFrame for batch processing
            df = pd.DataFrame(records)
            
            # Process in batches
            results = []
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                
                # Convert to GPU
                gdf = cudf.from_pandas(batch)
                
                # Process batch
                processed = process_func(gdf)
                
                # Convert back
                if isinstance(processed, cudf.DataFrame):
                    processed = processed.to_pandas()
                
                results.extend(processed.to_dict('records'))
            
            return results
            
        except Exception as e:
            logger.error(f"GPU batch processing failed: {e}")
            return [process_func(r) for r in records]
    
    def deduplicate_gpu(self, records: List[Dict], key_field: str = 'taxpayer_id') -> List[Dict]:
        """
        GPU-accelerated deduplication
        
        Args:
            records: List of records
            key_field: Field to deduplicate by
            
        Returns:
            Deduplicated records
        """
        if not self.use_gpu or not records:
            # CPU fallback
            seen = set()
            result = []
            for record in records:
                key = record.get(key_field)
                if key and key not in seen:
                    seen.add(key)
                    result.append(record)
            return result
        
        try:
            # Convert to cuDF
            df = pd.DataFrame(records)
            gdf = cudf.from_pandas(df)
            
            # GPU deduplication
            gdf_unique = gdf.drop_duplicates(subset=[key_field], keep='first')
            
            # Convert back
            result = gdf_unique.to_pandas().to_dict('records')
            
            logger.info(f"GPU deduplication: {len(records)} -> {len(result)} records")
            
            return result
            
        except Exception as e:
            logger.error(f"GPU deduplication failed: {e}")
            # Fallback to CPU
            seen = set()
            result = []
            for record in records:
                key = record.get(key_field)
                if key and key not in seen:
                    seen.add(key)
                    result.append(record)
            return result
    
    def merge_datasets_gpu(self, 
                          left_records: List[Dict],
                          right_records: List[Dict],
                          on: str = 'taxpayer_id') -> List[Dict]:
        """
        GPU-accelerated dataset merging
        
        Args:
            left_records: First dataset
            right_records: Second dataset
            on: Field to merge on
            
        Returns:
            Merged records
        """
        if not self.use_gpu:
            # CPU fallback
            left_df = pd.DataFrame(left_records)
            right_df = pd.DataFrame(right_records)
            merged = pd.merge(left_df, right_df, on=on, how='outer')
            return merged.to_dict('records')
        
        try:
            # Convert to cuDF
            left_df = cudf.from_pandas(pd.DataFrame(left_records))
            right_df = cudf.from_pandas(pd.DataFrame(right_records))
            
            # GPU merge
            merged = left_df.merge(right_df, on=on, how='outer')
            
            # Convert back
            result = merged.to_pandas().to_dict('records')
            
            logger.info(f"GPU merge: {len(left_records)} + {len(right_records)} -> {len(result)} records")
            
            return result
            
        except Exception as e:
            logger.error(f"GPU merge failed: {e}")
            # Fallback to CPU
            left_df = pd.DataFrame(left_records)
            right_df = pd.DataFrame(right_records)
            merged = pd.merge(left_df, right_df, on=on, how='outer')
            return merged.to_dict('records')
    
    def aggregate_gpu(self, 
                      records: List[Dict],
                      group_by: str,
                      agg_fields: Dict[str, str]) -> List[Dict]:
        """
        GPU-accelerated aggregation
        
        Args:
            records: Records to aggregate
            group_by: Field to group by
            agg_fields: Dictionary of field -> aggregation function
            
        Returns:
            Aggregated records
        """
        if not self.use_gpu:
            df = pd.DataFrame(records)
            result = df.groupby(group_by).agg(agg_fields).reset_index()
            return result.to_dict('records')
        
        try:
            # Convert to cuDF
            df = cudf.from_pandas(pd.DataFrame(records))
            
            # GPU aggregation
            result = df.groupby(group_by).agg(agg_fields).reset_index()
            
            # Convert back
            return result.to_pandas().to_dict('records')
            
        except Exception as e:
            logger.error(f"GPU aggregation failed: {e}")
            df = pd.DataFrame(records)
            result = df.groupby(group_by).agg(agg_fields).reset_index()
            return result.to_dict('records')
    
    def get_gpu_memory_info(self) -> Dict[str, float]:
        """Get GPU memory usage information"""
        if not self.use_gpu:
            return {'available': False}
        
        try:
            mempool = cp.get_default_memory_pool()
            
            return {
                'available': True,
                'used_bytes': mempool.used_bytes(),
                'used_mb': mempool.used_bytes() / (1024 ** 2),
                'total_bytes': mempool.total_bytes(),
                'total_mb': mempool.total_bytes() / (1024 ** 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting GPU memory info: {e}")
            return {'available': False, 'error': str(e)}
    
    def clear_gpu_memory(self):
        """Clear GPU memory cache"""
        if not self.use_gpu:
            return
        
        try:
            mempool = cp.get_default_memory_pool()
            mempool.free_all_blocks()
            logger.info("GPU memory cache cleared")
            
        except Exception as e:
            logger.error(f"Error clearing GPU memory: {e}")
    
    def __del__(self):
        """Cleanup GPU resources"""
        if self.use_gpu:
            try:
                self.clear_gpu_memory()
            except:
                pass


# Singleton instance
_gpu_accelerator = None

def get_gpu_accelerator() -> GPUAccelerator:
    """Get GPU accelerator singleton instance"""
    global _gpu_accelerator
    if _gpu_accelerator is None:
        _gpu_accelerator = GPUAccelerator()
    return _gpu_accelerator