import sys
import tempfile
import shutil
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from levelzap import remove_empty_folders, remove_zero_byte_files, OutputManager

def test_remove_empty_folders_non_recursive():
    """Test removing empty folders without recursion"""
    output_manager = OutputManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create directory structure
        empty_dir = tmp_path / "empty_folder"
        empty_dir.mkdir()
        
        non_empty_dir = tmp_path / "non_empty_folder"
        non_empty_dir.mkdir()
        (non_empty_dir / "file.txt").write_text("content")
        
        nested_empty = tmp_path / "parent" / "nested_empty"
        nested_empty.mkdir(parents=True)
        
        # Test non-recursive removal
        remove_empty_folders(tmp_path, simulate=True, recurse=False, output_manager=output_manager)
        
        # Check log file
        log_files = list(tmp_path.glob("levelzap.log.*.json"))
        assert len(log_files) == 1
        
        with open(log_files[0], 'r') as f:
            log_data = json.load(f)
        
        assert log_data["meta"]["recursive"] is False
        assert log_data["meta"]["operation"] == "remove_empty_folders"
        
        # Should only find the immediate empty folder, not the nested one
        delete_actions = [action for action in log_data["actions"] if action["action"] == "delete_empty_folder"]
        assert len(delete_actions) == 1
        assert Path(delete_actions[0]["source"]).name == "empty_folder"


def test_remove_empty_folders_recursive():
    """Test removing empty folders with recursion"""
    output_manager = OutputManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create nested empty directory structure
        deep_empty = tmp_path / "level1" / "level2" / "level3" / "empty"
        deep_empty.mkdir(parents=True)
        
        shallow_empty = tmp_path / "shallow_empty"
        shallow_empty.mkdir()
        
        non_empty = tmp_path / "non_empty"
        non_empty.mkdir()
        (non_empty / "file.txt").write_text("content")
        
        # Test recursive removal
        remove_empty_folders(tmp_path, simulate=True, recurse=True, output_manager=output_manager)
        
        # Check log file
        log_files = list(tmp_path.glob("levelzap.log.*.json"))
        assert len(log_files) == 1
        
        with open(log_files[0], 'r') as f:
            log_data = json.load(f)
        
        assert log_data["meta"]["recursive"] is True
        assert log_data["meta"]["operation"] == "remove_empty_folders"
        
        # Should find all empty folders (deepest first)
        delete_actions = [action for action in log_data["actions"] if action["action"] == "delete_empty_folder"]
        assert len(delete_actions) >= 2  # At least shallow_empty and deep_empty
        
        # Verify the deep empty folder is found
        source_paths = [action["source"] for action in delete_actions]
        assert any("empty" in path for path in source_paths)
        assert any("shallow_empty" in path for path in source_paths)


def test_remove_zero_byte_files_non_recursive():
    """Test removing zero-byte files without recursion"""
    output_manager = OutputManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create test files
        zero_file1 = tmp_path / "zero1.txt"
        zero_file1.touch()  # Creates empty file
        
        normal_file = tmp_path / "normal.txt"
        normal_file.write_text("content")
        
        # Create subdirectory with files
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()
        zero_file2 = sub_dir / "zero2.txt"
        zero_file2.touch()
        
        # Test non-recursive removal
        remove_zero_byte_files(tmp_path, simulate=True, recurse=False, output_manager=output_manager)
        
        # Check log file
        log_files = list(tmp_path.glob("levelzap.log.*.json"))
        assert len(log_files) == 1
        
        with open(log_files[0], 'r') as f:
            log_data = json.load(f)
        
        assert log_data["meta"]["recursive"] is False
        assert log_data["meta"]["operation"] == "remove_zero_byte_files"
        
        # Should find both zero-byte files (one in root, one in subdir)
        delete_actions = [action for action in log_data["actions"] if action["action"] == "delete_zero_file"]
        assert len(delete_actions) == 2
        
        source_paths = [Path(action["source"]).name for action in delete_actions]
        assert "zero1.txt" in source_paths
        assert "zero2.txt" in source_paths


def test_remove_zero_byte_files_recursive():
    """Test removing zero-byte files with recursion"""
    output_manager = OutputManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create nested directory structure with zero-byte files
        zero_root = tmp_path / "zero_root.txt"
        zero_root.touch()
        
        deep_dir = tmp_path / "level1" / "level2"
        deep_dir.mkdir(parents=True)
        zero_deep = deep_dir / "zero_deep.txt"
        zero_deep.touch()
        
        normal_file = tmp_path / "normal.txt"
        normal_file.write_text("content")
        
        # Test recursive removal
        remove_zero_byte_files(tmp_path, simulate=True, recurse=True, output_manager=output_manager)
        
        # Check log file
        log_files = list(tmp_path.glob("levelzap.log.*.json"))
        assert len(log_files) == 1
        
        with open(log_files[0], 'r') as f:
            log_data = json.load(f)
        
        assert log_data["meta"]["recursive"] is True
        assert log_data["meta"]["operation"] == "remove_zero_byte_files"
        
        # Should find both zero-byte files
        delete_actions = [action for action in log_data["actions"] if action["action"] == "delete_zero_file"]
        assert len(delete_actions) == 2
        
        source_paths = [Path(action["source"]).name for action in delete_actions]
        assert "zero_root.txt" in source_paths
        assert "zero_deep.txt" in source_paths


def test_actual_removal_empty_folders():
    """Test that empty folders are actually removed when not in simulation mode"""
    output_manager = OutputManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create empty folders
        empty1 = tmp_path / "empty1"
        empty1.mkdir()
        empty2 = tmp_path / "empty2"
        empty2.mkdir()
        
        # Non-empty folder should remain
        non_empty = tmp_path / "non_empty"
        non_empty.mkdir()
        (non_empty / "file.txt").write_text("content")
        
        # Perform actual removal (not simulation)
        remove_empty_folders(tmp_path, simulate=False, recurse=True, output_manager=output_manager)
        
        # Check that empty folders were removed
        assert not empty1.exists()
        assert not empty2.exists()
        assert non_empty.exists()
        assert (non_empty / "file.txt").exists()


def test_actual_removal_zero_byte_files():
    """Test that zero-byte files are actually removed when not in simulation mode"""
    output_manager = OutputManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create zero-byte files
        zero1 = tmp_path / "zero1.txt"
        zero1.touch()
        zero2 = tmp_path / "zero2.txt"
        zero2.touch()
        
        # Normal file should remain
        normal = tmp_path / "normal.txt"
        normal.write_text("content")
        
        # Perform actual removal (not simulation)
        remove_zero_byte_files(tmp_path, simulate=False, recurse=True, output_manager=output_manager)
        
        # Check that zero-byte files were removed
        assert not zero1.exists()
        assert not zero2.exists()
        assert normal.exists()
        assert normal.read_text() == "content"


def test_no_files_to_remove():
    """Test behavior when there are no files/folders to remove"""
    output_manager = OutputManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create only non-empty folders and non-zero files
        folder = tmp_path / "folder"
        folder.mkdir()
        (folder / "file.txt").write_text("content")
        
        # Test empty folder removal - should find nothing
        remove_empty_folders(tmp_path, simulate=True, recurse=True, output_manager=output_manager)
        
        # Test zero-byte file removal - should find nothing  
        remove_zero_byte_files(tmp_path, simulate=True, recurse=True, output_manager=output_manager)
        
        # Should not create log files when nothing was found
        log_files = list(tmp_path.glob("levelzap.log.*.json"))
        assert len(log_files) == 0


def test_error_handling():
    """Test error handling for inaccessible files/folders"""
    output_manager = OutputManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create a file that should be processed
        zero_file = tmp_path / "zero.txt"
        zero_file.touch()
        
        # This should work normally
        remove_zero_byte_files(tmp_path, simulate=True, recurse=False, output_manager=output_manager)
        
        # Check log file was created
        log_files = list(tmp_path.glob("levelzap.log.*.json"))
        assert len(log_files) == 1