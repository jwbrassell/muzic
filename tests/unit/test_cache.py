"""Unit tests for Redis caching module."""
import pytest
from unittest.mock import patch, MagicMock
import json
from app.core.cache import (
    get_redis_client,
    cache_get,
    cache_set,
    cache_delete,
    cache_clear_pattern,
    cached,
    invalidate_cache,
    CacheError
)

@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    with patch('app.core.cache.redis_client') as mock:
        yield mock

def test_cache_get(mock_redis):
    """Test getting value from cache."""
    # Test successful get
    mock_redis.get.return_value = json.dumps({'key': 'value'})
    result = cache_get('test_key')
    assert result == {'key': 'value'}
    mock_redis.get.assert_called_once_with('test_key')
    
    # Test missing key
    mock_redis.get.return_value = None
    result = cache_get('missing_key')
    assert result is None
    
    # Test Redis error
    mock_redis.get.side_effect = Exception('Redis error')
    with pytest.raises(CacheError):
        cache_get('error_key')

def test_cache_set(mock_redis):
    """Test setting value in cache."""
    # Test successful set
    data = {'key': 'value'}
    cache_set('test_key', data)
    mock_redis.set.assert_called_once_with('test_key', json.dumps(data))
    
    # Test set with timeout
    cache_set('test_key', data, timeout=60)
    mock_redis.setex.assert_called_once_with('test_key', 60, json.dumps(data))
    
    # Test Redis error
    mock_redis.set.side_effect = Exception('Redis error')
    with pytest.raises(CacheError):
        cache_set('error_key', data)

def test_cache_delete(mock_redis):
    """Test deleting value from cache."""
    # Test successful delete
    cache_delete('test_key')
    mock_redis.delete.assert_called_once_with('test_key')
    
    # Test Redis error
    mock_redis.delete.side_effect = Exception('Redis error')
    with pytest.raises(CacheError):
        cache_delete('error_key')

def test_cache_clear_pattern(mock_redis):
    """Test clearing cache by pattern."""
    # Test successful clear
    mock_redis.keys.return_value = ['key1', 'key2']
    cache_clear_pattern('test_*')
    mock_redis.delete.assert_called_once_with('key1', 'key2')
    
    # Test no matching keys
    mock_redis.keys.return_value = []
    cache_clear_pattern('test_*')
    assert mock_redis.delete.call_count == 1  # No additional calls
    
    # Test Redis error
    mock_redis.keys.side_effect = Exception('Redis error')
    with pytest.raises(CacheError):
        cache_clear_pattern('error_*')

def test_cached_decorator(mock_redis):
    """Test cached decorator."""
    # Mock cache miss then hit
    mock_redis.get.side_effect = [None, json.dumps('cached_result')]
    
    @cached('test')
    def test_function(arg):
        return f'result_{arg}'
    
    # First call - cache miss
    result1 = test_function('key')
    assert result1 == 'result_key'
    mock_redis.set.assert_called_once()
    
    # Second call - cache hit
    result2 = test_function('key')
    assert result2 == 'cached_result'

def test_cached_decorator_with_custom_key(mock_redis):
    """Test cached decorator with custom key builder."""
    def key_builder(arg1, arg2):
        return f'{arg1}_{arg2}'
    
    @cached('test', key_builder=key_builder)
    def test_function(arg1, arg2):
        return f'result_{arg1}_{arg2}'
    
    result = test_function('a', 'b')
    assert result == 'result_a_b'
    mock_redis.get.assert_called_once_with('test:a_b')

def test_invalidate_cache_decorator(mock_redis):
    """Test invalidate cache decorator."""
    @invalidate_cache('test_*')
    def test_function():
        return 'result'
    
    mock_redis.keys.return_value = ['test_1', 'test_2']
    result = test_function()
    
    assert result == 'result'
    mock_redis.delete.assert_called_once_with('test_1', 'test_2')

def test_health_check(mock_redis):
    """Test Redis health check."""
    # Test successful ping
    mock_redis.ping.return_value = True
    assert get_redis_client().ping() is True
    
    # Test failed ping
    mock_redis.ping.side_effect = Exception('Redis error')
    assert get_redis_client().ping() is False

def test_serialization_error():
    """Test serialization error handling."""
    class UnserializableObject:
        pass
    
    with pytest.raises(CacheError):
        cache_set('test_key', UnserializableObject())

def test_deserialization_error(mock_redis):
    """Test deserialization error handling."""
    mock_redis.get.return_value = 'invalid json'
    
    with pytest.raises(CacheError):
        cache_get('test_key')
