import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from levelzap import FileAnalyzer, OutputManager

def test_file_analyzer_count():
    """Test file counting functionality"""
    output_manager = OutputManager()
    analyzer = FileAnalyzer(output_manager)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create test files
        (tmp_path / "file1.txt").write_text("test")
        (tmp_path / "file2.txt").write_text("test")
        
        # Create subdirectory with files
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.txt").write_text("test")
        
        # Test non-recursive count
        count = analyzer.count_files(tmp_path, recursive=False)
        assert count == 2
        
        # Test recursive count
        count_recursive = analyzer.count_files(tmp_path, recursive=True)
        assert count_recursive == 3

def test_file_analyzer_size():
    """Test size calculation functionality"""
    output_manager = OutputManager()
    analyzer = FileAnalyzer(output_manager)
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create test files with known sizes
        (tmp_path / "file1.txt").write_text("hello")  # 5 bytes
        (tmp_path / "file2.txt").write_text("world")  # 5 bytes
        
        # Create subdirectory with file
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.txt").write_text("test")    # 4 bytes
        
        # Test non-recursive size
        size = analyzer.calculate_size(tmp_path, recursive=False)
        assert size == 10
        
        # Test recursive size
        size_recursive = analyzer.calculate_size(tmp_path, recursive=True)
        assert size_recursive == 14

def test_format_size():
    """Test size formatting"""
    output_manager = OutputManager()
    analyzer = FileAnalyzer(output_manager)
    
    assert analyzer.format_size(0) == "0 B"
    assert analyzer.format_size(512) == "512.0 B"
    assert analyzer.format_size(1024) == "1.0 KB"
    assert analyzer.format_size(1536) == "1.5 KB"
    assert analyzer.format_size(1024 * 1024) == "1.0 MB"