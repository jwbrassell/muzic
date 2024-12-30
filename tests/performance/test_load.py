"""Performance and load tests for the system."""
import pytest
import time
import threading
import queue
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch
from app.core.monitoring import get_monitor
from app.core.optimization import get_optimizer
from app.core.cache import cache_get, cache_set, CacheError

@pytest.fixture
def monitor():
    """Create a test monitor instance."""
    return get_monitor()

@pytest.fixture
def optimizer():
    """Create a test optimizer instance."""
    return get_optimizer()

def test_concurrent_cache_operations():
    """Test cache performance under concurrent load."""
    NUM_THREADS = 50
    NUM_OPERATIONS = 1000
    results = queue.Queue()
    
    def worker(thread_id):
        """Worker function for cache operations."""
        response_times = []
        hits = 0
        misses = 0
        
        for i in range(NUM_OPERATIONS):
            key = f'test_key_{i % 10}'  # Use 10 different keys
            start_time = time.time()
            
            try:
                with patch('app.core.cache.redis_client') as mock_redis:
                    # Simulate cache hit rate
                    if i % 3 == 0:  # 33% miss rate
                        mock_redis.get.return_value = None
                        cache_set(key, f'value_{i}')
                        misses += 1
                    else:
                        mock_redis.get.return_value = f'value_{i}'
                        hits += 1
                    
                    value = cache_get(key)
                    
                response_time = time.time() - start_time
                response_times.append(response_time)
                
            except CacheError:
                continue
        
        results.put({
            'thread_id': thread_id,
            'response_times': response_times,
            'hits': hits,
            'misses': misses
        })
    
    # Run concurrent operations
    start_time = time.time()
    threads = []
    for i in range(NUM_THREADS):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    
    # Analyze results
    all_times = []
    total_hits = 0
    total_misses = 0
    
    while not results.empty():
        result = results.get()
        all_times.extend(result['response_times'])
        total_hits += result['hits']
        total_misses += result['misses']
    
    # Calculate metrics
    avg_response_time = statistics.mean(all_times)
    p95_response_time = statistics.quantiles(all_times, n=20)[18]  # 95th percentile
    hit_rate = (total_hits / (total_hits + total_misses)) * 100
    operations_per_second = (NUM_THREADS * NUM_OPERATIONS) / total_time
    
    # Assert performance requirements
    assert avg_response_time < 0.01  # Average response time under 10ms
    assert p95_response_time < 0.05  # 95th percentile under 50ms
    assert hit_rate > 65.0  # Cache hit rate above 65%
    assert operations_per_second > 1000  # More than 1000 ops/sec

def test_database_optimization_impact(optimizer):
    """Test impact of database optimization on query performance."""
    def measure_query_time():
        """Measure time for a sample query."""
        times = []
        with patch('sqlalchemy.create_engine') as mock_engine:
            mock_conn = mock_engine.return_value.connect.return_value.__enter__.return_value
            
            for _ in range(100):
                start_time = time.time()
                mock_conn.execute("SELECT * FROM large_table")
                times.append(time.time() - start_time)
        
        return statistics.mean(times)
    
    # Measure before optimization
    before_time = measure_query_time()
    
    # Run optimization
    optimizer.optimize_database()
    
    # Measure after optimization
    after_time = measure_query_time()
    
    # Assert optimization improved performance
    assert after_time < before_time
    assert (before_time - after_time) / before_time > 0.1  # At least 10% improvement

def test_system_load(monitor):
    """Test system performance under load."""
    def simulate_load(duration=5):
        """Simulate system load for a specified duration."""
        end_time = time.time() + duration
        operations = 0
        
        while time.time() < end_time:
            # Simulate mixed workload
            with patch('app.core.cache.redis_client') as mock_redis:
                cache_get('test_key')
                cache_set('test_key', 'value')
                monitor.get_system_metrics()
            operations += 3
        
        return operations
    
    # Run load test with multiple threads
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(simulate_load) for _ in range(10)]
        total_operations = sum(f.result() for f in as_completed(futures))
    
    # Get system metrics after load
    metrics = monitor.get_system_metrics()
    
    # Assert system stability
    assert metrics['cpu']['percent'] < 80  # CPU usage under 80%
    assert metrics['memory']['percent'] < 80  # Memory usage under 80%
    assert total_operations / 5 > 1000  # Maintained over 1000 ops/sec

def test_cache_performance_degradation():
    """Test cache performance degradation under increasing load."""
    response_times = []
    
    with patch('app.core.cache.redis_client') as mock_redis:
        # Test with increasing number of cached items
        for num_items in [100, 1000, 10000, 100000]:
            mock_redis.keys.return_value = [f'key_{i}' for i in range(num_items)]
            mock_redis.mget.return_value = ['value'] * num_items
            
            start_time = time.time()
            cache_get('test_key')
            response_times.append(time.time() - start_time)
    
    # Assert reasonable performance degradation
    for i in range(len(response_times) - 1):
        ratio = response_times[i + 1] / response_times[i]
        assert ratio < 10  # Performance shouldn't degrade more than 10x between scales

def test_optimization_scheduling(optimizer, monitor):
    """Test impact of scheduled optimization on system performance."""
    # Simulate system metrics before optimization
    initial_metrics = monitor.get_system_metrics()
    
    # Record some slow queries
    with patch('sqlalchemy.create_engine') as mock_engine:
        mock_conn = mock_engine.return_value.connect.return_value.__enter__.return_value
        mock_conn.execute.return_value = [
            ('SELECT *', 500000, 100)  # 500ms query
        ]
        
        # Get initial slow queries
        initial_queries = optimizer.analyze_query_performance()
        assert len(initial_queries) > 0
        assert initial_queries[0]['avg_duration'] > 0.1
        
        # Run optimization
        result = optimizer.optimize_database()
        assert result['status'] == 'success'
        
        # Mock improved query performance
        mock_conn.execute.return_value = [
            ('SELECT *', 100000, 100)  # 100ms query after optimization
        ]
        
        # Check queries after optimization
        optimized_queries = optimizer.analyze_query_performance()
        assert len(optimized_queries) > 0
        assert optimized_queries[0]['avg_duration'] < initial_queries[0]['avg_duration']
    
    # Verify system metrics after optimization
    final_metrics = monitor.get_system_metrics()
    assert final_metrics['cpu']['percent'] <= initial_metrics['cpu']['percent']
