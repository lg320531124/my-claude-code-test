"""Circular Buffer - Efficient circular buffer implementation."""

from __future__ import annotations
from typing import TypeVar, Generic, Optional, List, Iterator
from dataclasses import dataclass

T = TypeVar('T')


@dataclass
class BufferStats:
    """Buffer statistics."""
    size: int
    capacity: int
    overwrite_count: int = 0
    read_count: int = 0
    write_count: int = 0


class CircularBuffer(Generic[T]):
    """Circular buffer implementation."""
    
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        
        self._capacity = capacity
        self._buffer: List[Optional[T]] = [None] * capacity
        self._head = 0
        self._tail = 0
        self._size = 0
        self._overwrite_count = 0
        self._read_count = 0
        self._write_count = 0
    
    def write(self, item: T) -> None:
        """Write item to buffer."""
        self._buffer[self._head] = item
        self._head = (self._head + 1) % self._capacity
        
        if self._size < self._capacity:
            self._size += 1
        else:
            # Overwrite - move tail
            self._tail = (self._tail + 1) % self._capacity
            self._overwrite_count += 1
        
        self._write_count += 1
    
    def read(self) -> Optional[T]:
        """Read item from buffer."""
        if self._size == 0:
            return None
        
        item = self._buffer[self._tail]
        self._tail = (self._tail + 1) % self._capacity
        self._size -= 1
        self._read_count += 1
        
        return item
    
    def peek(self) -> Optional[T]:
        """Peek at next item."""
        if self._size == 0:
            return None
        return self._buffer[self._tail]
    
    def peek_last(self) -> Optional[T]:
        """Peek at last written item."""
        if self._size == 0:
            return None
        idx = (self._head - 1) % self._capacity
        return self._buffer[idx]
    
    def get_all(self) -> List[T]:
        """Get all items."""
        items = []
        for i in range(self._size):
            idx = (self._tail + i) % self._capacity
            if self._buffer[idx] is not None:
                items.append(self._buffer[idx])
        return items
    
    def get_last(self, n: int) -> List[T]:
        """Get last n items."""
        if n > self._size:
            n = self._size
        
        items = []
        for i in range(n):
            idx = (self._head - 1 - i) % self._capacity
            if self._buffer[idx] is not None:
                items.append(self._buffer[idx])
        
        return list(reversed(items))
    
    def clear(self) -> None:
        """Clear buffer."""
        self._buffer = [None] * self._capacity
        self._head = 0
        self._tail = 0
        self._size = 0
    
    def is_empty(self) -> bool:
        """Check if empty."""
        return self._size == 0
    
    def is_full(self) -> bool:
        """Check if full."""
        return self._size == self._capacity
    
    def size(self) -> int:
        """Get current size."""
        return self._size
    
    def capacity(self) -> int:
        """Get capacity."""
        return self._capacity
    
    def get_stats(self) -> BufferStats:
        """Get statistics."""
        return BufferStats(
            size=self._size,
            capacity=self._capacity,
            overwrite_count=self._overwrite_count,
            read_count=self._read_count,
            write_count=self._write_count,
        )
    
    def __len__(self) -> int:
        return self._size
    
    def __iter__(self) -> Iterator[T]:
        for i in range(self._size):
            idx = (self._tail + i) % self._capacity
            if self._buffer[idx] is not None:
                yield self._buffer[idx]


__all__ = [
    "BufferStats",
    "CircularBuffer",
]
