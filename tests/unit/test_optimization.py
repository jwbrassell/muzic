"""Unit tests for database optimization module."""
import pytest
from unittest.mock import patch, MagicMock, call
from app.core.optimization import get_optimizer

@pytest.fixture
def optimizer():
    """Create a test optimizer instance."""
    return get_optimizer()

@pytest.fixture
def mock_engine():
    """Create a mock SQLAlchemy engine."""
    with patch('sqlalchemy.create_engine') as mock:
        engine = MagicMock()
        mock.return_value = engine
        yield engine

def test_analyze_table_statistics(optimizer, mock_engine):
    """Test table statistics analysis."""
    # Mock inspector
    mock_inspector = MagicMock()
    mock_inspector.get_table_names.return_value = ['table1', 'table2']
    mock_inspector.get_indexes.return_value = [
        {'name': 'idx1', 'column_names': ['col1']},
        {'name': 'idx2', 'column_names': ['col2']}
    ]
    
    # Mock connection and results
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = [
        MagicMock(scalar=lambda: 100),  # row count for table1
        MagicMock(scalar=lambda: 1024),  # size for table1
        MagicMock(scalar=lambda: 200),  # row count for table2
        MagicMock(scalar=lambda: 2048)   # size for table2
    ]
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    
    with patch('sqlalchemy.inspect', return_value=mock_inspector):
        stats = optimizer.analyze_table_statistics()
        
        assert isinstance(stats, dict)
        assert 'table1' in stats
        assert 'table2' in stats
        
        assert stats['table1']['row_count'] == 100
        assert stats['table1']['size_bytes'] == 1024
        assert stats['table1']['indexes'] == 2
        
        assert stats['table2']['row_count'] == 200
        assert stats['table2']['size_bytes'] == 2048
        assert stats['table2']['indexes'] == 2

def test_optimize_indexes(optimizer, mock_engine):
    """Test index optimization."""
    # Mock inspector
    mock_inspector = MagicMock()
    mock_inspector.get_table_names.return_value = ['users']
    mock_inspector.get_indexes.return_value = [
        {'name': 'idx_users_id', 'column_names': ['id']}
    ]
    mock_inspector.get_columns.return_value = [
        {'name': 'id'},
        {'name': 'created_at'},
        {'name': 'status'}
    ]
    
    with patch('sqlalchemy.inspect', return_value=mock_inspector):
        operations = optimizer.optimize_indexes()
        
        assert isinstance(operations, list)
        assert len(operations) == 2  # Should create indexes for created_at and status
        assert any('created_at' in op for op in operations)
        assert any('status' in op for op in operations)

def test_analyze_query_performance(optimizer, mock_engine):
    """Test query performance analysis."""
    # Mock connection and results
    mock_conn = MagicMock()
    mock_result = [
        ('SELECT * FROM users', 150000, 100),  # 150ms, 100 executions
        ('SELECT * FROM posts', 200000, 50)    # 200ms, 50 executions
    ]
    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    
    queries = optimizer.analyze_query_performance()
    
    assert isinstance(queries, list)
    assert len(queries) == 2
    
    assert queries[0]['query'] == 'SELECT * FROM users'
    assert queries[0]['avg_duration'] == 0.15  # 150ms -> 0.15s
    assert queries[0]['execution_count'] == 100
    
    assert queries[1]['query'] == 'SELECT * FROM posts'
    assert queries[1]['avg_duration'] == 0.2   # 200ms -> 0.2s
    assert queries[1]['execution_count'] == 50

def test_optimize_database(optimizer, mock_engine):
    """Test full database optimization."""
    # Mock connection
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    
    # Mock component functions
    with patch.object(optimizer, 'optimize_indexes') as mock_indexes, \
         patch.object(optimizer, 'analyze_table_statistics') as mock_stats, \
         patch.object(optimizer, 'analyze_query_performance') as mock_queries:
        
        mock_indexes.return_value = ['Created index idx1']
        mock_stats.return_value = {'table1': {'row_count': 100}}
        mock_queries.return_value = [{'query': 'SELECT *', 'avg_duration': 0.1}]
        
        result = optimizer.optimize_database()
        
        assert isinstance(result, dict)
        assert result['status'] == 'success'
        assert 'operations' in result
        assert 'statistics' in result
        assert 'slow_queries' in result
        
        # Verify VACUUM and ANALYZE were called
        vacuum_call = call(text('VACUUM'))
        analyze_call = call(text('ANALYZE'))
        mock_conn.execute.assert_has_calls([vacuum_call, analyze_call], any_order=True)

def test_get_connection_pool_status(optimizer, mock_engine):
    """Test connection pool status retrieval."""
    mock_engine.pool.size.return_value = 5
    mock_engine.pool.checkedin.return_value = 3
    mock_engine.pool.checkedout.return_value = 2
    mock_engine.pool.overflow.return_value = 0
    mock_engine.pool.timeout = 30
    mock_engine.pool.recycle = 1800
    
    status = optimizer.get_connection_pool_status()
    
    assert isinstance(status, dict)
    assert status['pool_size'] == 5
    assert status['checkedin'] == 3
    assert status['checkedout'] == 2
    assert status['overflow'] == 0
    assert status['timeout'] == 30
    assert status['recycle'] == 1800

def test_optimizer_singleton():
    """Test optimizer singleton pattern."""
    optimizer1 = get_optimizer()
    optimizer2 = get_optimizer()
    assert optimizer1 is optimizer2
