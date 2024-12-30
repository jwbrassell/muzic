"""Unit tests for monitoring module."""
import pytest
from unittest.mock import patch, MagicMock
from app.core.monitoring import get_monitor

@pytest.fixture
def monitor():
    """Create a test monitor instance."""
    return get_monitor()

def test_get_system_metrics(monitor):
    """Test system metrics collection."""
    metrics = monitor.get_system_metrics()
    
    assert isinstance(metrics, dict)
    assert 'cpu' in metrics
    assert 'memory' in metrics
    assert 'disk' in metrics
    
    assert isinstance(metrics['cpu']['percent'], (int, float))
    assert isinstance(metrics['memory']['percent'], (int, float))
    assert isinstance(metrics['disk']['percent'], (int, float))

def test_get_health_status(monitor):
    """Test health status check."""
    status = monitor.get_health_status()
    
    assert isinstance(status, dict)
    assert 'healthy' in status
    assert isinstance(status['healthy'], bool)
    assert 'components' in status
    assert 'system' in status['components']
    assert 'redis' in status['components']

@patch('app.core.cache.redis_client')
def test_cache_hit_rate(mock_redis, monitor):
    """Test cache hit rate calculation."""
    # Mock Redis data
    mock_redis.keys.return_value = ['hit1', 'hit2', 'hit3']
    mock_redis.mget.return_value = ['1', '0', '1']
    
    hit_rate = monitor.get_cache_hit_rate()
    assert isinstance(hit_rate, float)
    assert 0 <= hit_rate <= 100
    assert hit_rate == pytest.approx(66.67, rel=0.01)  # 2/3 hits = ~66.67%

@patch('app.core.cache.redis_client')
def test_error_count(mock_redis, monitor):
    """Test error count retrieval."""
    # Mock Redis data
    mock_redis.keys.return_value = ['error1', 'error2']
    
    error_count = monitor.get_error_count()
    assert isinstance(error_count, int)
    assert error_count == 2

def test_record_request_time(monitor):
    """Test request time recording."""
    with patch('app.core.cache.redis_client') as mock_redis:
        monitor.record_request_time('/api/test', 0.5)
        mock_redis.setex.assert_called_once()
        
        # Verify the recorded duration
        args = mock_redis.setex.call_args[0]
        assert isinstance(args[0], str)  # Key
        assert args[1] == monitor.metrics_retention  # TTL
        assert float(args[2]) == 0.5  # Duration

def test_monitor_singleton():
    """Test monitor singleton pattern."""
    monitor1 = get_monitor()
    monitor2 = get_monitor()
    assert monitor1 is monitor2
