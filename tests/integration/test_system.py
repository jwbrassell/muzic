"""Integration tests for system components."""
import pytest
from unittest.mock import patch
import time
from app.core.monitoring import get_monitor
from app.core.optimization import get_optimizer
from app.core.cache import cache_set, cache_get, cached

@pytest.fixture
def monitor():
    """Create a test monitor instance."""
    return get_monitor()

@pytest.fixture
def optimizer():
    """Create a test optimizer instance."""
    return get_optimizer()

def test_cache_monitoring_integration(monitor):
    """Test cache monitoring with actual cache operations."""
    # Clear any existing metrics
    with patch('app.core.cache.redis_client') as mock_redis:
        mock_redis.keys.return_value = []
        initial_hit_rate = monitor.get_cache_hit_rate()
        assert initial_hit_rate == 0.0
        
        # Simulate cache operations
        mock_redis.get.side_effect = [None, json.dumps('cached_value')]
        
        # First call - cache miss
        result = cache_get('test_key')
        assert result is None
        
        # Record cache miss
        monitor.record_cache_hit(False)
        
        # Set cache value
        cache_set('test_key', 'cached_value')
        
        # Second call - cache hit
        result = cache_get('test_key')
        assert result == 'cached_value'
        
        # Record cache hit
        monitor.record_cache_hit(True)
        
        # Check hit rate (should be 50%)
        mock_redis.keys.return_value = ['hit1', 'hit2']
        mock_redis.mget.return_value = ['0', '1']
        hit_rate = monitor.get_cache_hit_rate()
        assert hit_rate == 50.0

def test_optimization_monitoring_integration(optimizer, monitor):
    """Test database optimization with monitoring."""
    # Get initial system metrics
    initial_metrics = monitor.get_system_metrics()
    assert isinstance(initial_metrics, dict)
    
    # Run database optimization
    with patch('sqlalchemy.create_engine') as mock_engine:
        # Mock the database connection and operations
        mock_conn = mock_engine.return_value.connect.return_value.__enter__.return_value
        
        # Run optimization
        result = optimizer.optimize_database()
        assert result['status'] == 'success'
        
        # Verify system metrics were updated
        current_metrics = monitor.get_system_metrics()
        assert isinstance(current_metrics, dict)
        
        # Check optimization was recorded in monitoring
        assert monitor.get_error_count('database_optimization') == 0

def test_cached_decorator_with_monitoring():
    """Test cached decorator with monitoring integration."""
    monitor = get_monitor()
    
    @cached('test')
    def test_function(arg):
        time.sleep(0.1)  # Simulate work
        return f'result_{arg}'
    
    with patch('app.core.cache.redis_client') as mock_redis:
        # First call - cache miss
        mock_redis.get.return_value = None
        start_time = time.time()
        result1 = test_function('key')
        duration1 = time.time() - start_time
        
        assert result1 == 'result_key'
        assert duration1 >= 0.1  # Verify work was done
        
        # Second call - cache hit
        mock_redis.get.return_value = json.dumps('result_key')
        start_time = time.time()
        result2 = test_function('key')
        duration2 = time.time() - start_time
        
        assert result2 == 'result_key'
        assert duration2 < duration1  # Verify cached response was faster

def test_system_health_check(monitor, optimizer):
    """Test overall system health check."""
    with patch('app.core.cache.redis_client') as mock_redis:
        # Mock Redis health
        mock_redis.ping.return_value = True
        
        # Get system health status
        health = monitor.get_health_status()
        
        assert health['healthy'] is True
        assert health['components']['redis']['status'] == 'healthy'
        assert health['components']['system']['status'] == 'healthy'
        
        # Verify database connection pool
        pool_status = optimizer.get_connection_pool_status()
        assert isinstance(pool_status, dict)
        assert all(key in pool_status for key in ['pool_size', 'checkedin', 'checkedout'])

def test_error_handling_integration(monitor):
    """Test error handling across components."""
    with patch('app.core.cache.redis_client') as mock_redis:
        # Simulate Redis error
        mock_redis.get.side_effect = Exception('Redis error')
        
        # Attempt cache operation
        with pytest.raises(Exception):
            cache_get('test_key')
        
        # Verify error was recorded
        mock_redis.keys.return_value = ['error1']
        error_count = monitor.get_error_count()
        assert error_count == 1
        
        # Check system health reflects error
        mock_redis.ping.side_effect = Exception('Redis error')
        health = monitor.get_health_status()
        assert health['healthy'] is False
        assert health['components']['redis']['status'] == 'unhealthy'

def test_performance_metrics_integration(monitor, optimizer):
    """Test performance metrics collection across components."""
    with patch('app.core.cache.redis_client') as mock_redis, \
         patch('sqlalchemy.create_engine') as mock_engine:
        
        # Record some request times
        monitor.record_request_time('/api/test', 0.1)
        monitor.record_request_time('/api/test', 0.2)
        
        # Mock slow queries
        mock_engine.return_value.connect.return_value.__enter__.return_value.execute.return_value = [
            ('SELECT *', 150000, 100)
        ]
        
        # Get slow queries
        slow_queries = optimizer.analyze_query_performance()
        assert len(slow_queries) == 1
        assert slow_queries[0]['avg_duration'] == 0.15
        
        # Verify metrics are being collected
        mock_redis.keys.return_value = ['metrics:request:/api/test:1', 'metrics:request:/api/test:2']
        mock_redis.mget.return_value = ['0.1', '0.2']
        avg_time = monitor.get_average_response_time('/api/test')
        assert avg_time == 0.15  # (0.1 + 0.2) / 2
