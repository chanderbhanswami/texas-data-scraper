"""
Rate limiting utilities for API requests
"""
import time
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from collections import deque
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Rate limiter for API requests"""
    
    def __init__(self, max_requests: int, time_window: int = 3600, delay: float = 0.1):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds (default: 3600 = 1 hour)
            delay: Minimum delay between requests in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.delay = delay
        self.requests = deque()
        self.last_request_time = None
        
    def _clean_old_requests(self):
        """Remove requests older than the time window"""
        current_time = time.time()
        cutoff_time = current_time - self.time_window
        
        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()
    
    def can_make_request(self) -> bool:
        """Check if a request can be made without exceeding rate limit"""
        self._clean_old_requests()
        return len(self.requests) < self.max_requests
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits"""
        # Clean old requests
        self._clean_old_requests()
        
        # Check if we've hit the rate limit
        if len(self.requests) >= self.max_requests:
            oldest_request = self.requests[0]
            wait_time = (oldest_request + self.time_window) - time.time()
            
            if wait_time > 0:
                logger.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time + 1)  # Add 1 second buffer
                self._clean_old_requests()
        
        # Enforce minimum delay between requests
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
    
    def record_request(self):
        """Record that a request was made"""
        current_time = time.time()
        self.requests.append(current_time)
        self.last_request_time = current_time
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        self._clean_old_requests()
        return {
            'requests_made': len(self.requests),
            'max_requests': self.max_requests,
            'time_window': self.time_window,
            'requests_remaining': self.max_requests - len(self.requests),
            'window_reset_in': self.time_window - (time.time() - self.requests[0]) if self.requests else 0
        }


class AsyncRateLimiter:
    """Async rate limiter for concurrent API requests"""
    
    def __init__(self, max_requests: int, time_window: int = 3600, delay: float = 0.1):
        """
        Initialize async rate limiter
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds (default: 3600 = 1 hour)
            delay: Minimum delay between requests in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.delay = delay
        self.requests = deque()
        self.last_request_time = None
        self.lock = asyncio.Lock()
        
    async def _clean_old_requests(self):
        """Remove requests older than the time window"""
        current_time = time.time()
        cutoff_time = current_time - self.time_window
        
        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()
    
    async def wait_if_needed(self):
        """Wait if necessary to respect rate limits"""
        async with self.lock:
            # Clean old requests
            await self._clean_old_requests()
            
            # Check if we've hit the rate limit
            if len(self.requests) >= self.max_requests:
                oldest_request = self.requests[0]
                wait_time = (oldest_request + self.time_window) - time.time()
                
                if wait_time > 0:
                    logger.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
                    await asyncio.sleep(wait_time + 1)
                    await self._clean_old_requests()
            
            # Enforce minimum delay between requests
            if self.last_request_time:
                elapsed = time.time() - self.last_request_time
                if elapsed < self.delay:
                    await asyncio.sleep(self.delay - elapsed)
    
    async def record_request(self):
        """Record that a request was made"""
        async with self.lock:
            current_time = time.time()
            self.requests.append(current_time)
            self.last_request_time = current_time
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics (sync method for compatibility)"""
        # Clean old requests synchronously
        current_time = time.time()
        cutoff_time = current_time - self.time_window
        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()
        
        return {
            'requests_made': len(self.requests),
            'max_requests': self.max_requests,
            'time_window': self.time_window,
            'requests_remaining': self.max_requests - len(self.requests),
            'window_reset_in': self.time_window - (time.time() - self.requests[0]) if self.requests else 0
        }


class BackoffRetry:
    """Exponential backoff retry handler"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        """
        Initialize backoff retry handler
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number"""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        return delay
    
    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if should retry based on attempt and exception"""
        if attempt >= self.max_retries:
            return False
        
        # Retry on common transient errors
        retryable_errors = (
            ConnectionError,
            TimeoutError,
            # Add more as needed
        )
        
        return isinstance(exception, retryable_errors)
    
    async def async_retry(self, func, *args, **kwargs):
        """Execute function with async retry logic"""
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if not self.should_retry(attempt, e):
                    raise
                
                delay = self.get_delay(attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
        
        raise Exception(f"Failed after {self.max_retries} retries")
    
    def sync_retry(self, func, *args, **kwargs):
        """Execute function with sync retry logic"""
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if not self.should_retry(attempt, e):
                    raise
                
                delay = self.get_delay(attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
        
        raise Exception(f"Failed after {self.max_retries} retries")