import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from levelzap import flatten_folder, OutputManager, resolve_duplicate_file

def test_flatten_folder_recurse():
    """Test recursive flattening functionality"""
    output_manager = OutputManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create nested directory structure
        (tmp_path / "subfolder1").mkdir()
        (tmp_path / "subfolder1" / "deepfolder").mkdir()
        (tmp_path / "subfolder2").mkdir()
        
        # Create test files
        (tmp_path / "subfolder1" / "file1.txt").write_text("file1 content")
        (tmp_path / "subfolder1" / "deepfolder" / "file2.txt").write_text("file2 content")
        (tmp_path / "subfolder2" / "file3.txt").write_text("file3 content")
        
        # Test recursive flatten
        flatten_folder(tmp_path, simulate=True, recurse=True, output_manager=output_manager)
        
        # Check log file was created with recursive flag
        log_files = list(tmp_path.glob("levelzap.log.*.json"))
        assert len(log_files) == 1
        
        import json
        with open(log_files[0], 'r') as f:
            log_data = json.load(f)
        
        assert log_data["meta"]["recursive"] is True
        
        # Check that all files would be moved to root
        moved_files = [action for action in log_data["actions"] if action["action"] == "move"]
        assert len(moved_files) == 3  # All three files should be moved
        
        # Verify destination paths are all in root
        for action in moved_files:
            dest_path = Path(action["destination"])
            assert dest_path.parent == tmp_path


def test_flatten_folder_non_recurse():
    """Test non-recursive flattening (original behavior)"""
    output_manager = OutputManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create nested directory structure
        (tmp_path / "subfolder1").mkdir()
        (tmp_path / "subfolder1" / "deepfolder").mkdir()
        (tmp_path / "subfolder2").mkdir()
        
        # Create test files
        (tmp_path / "subfolder1" / "file1.txt").write_text("file1 content")
        (tmp_path / "subfolder1" / "deepfolder" / "file2.txt").write_text("file2 content")
        (tmp_path / "subfolder2" / "file3.txt").write_text("file3 content")
        
        # Test non-recursive flatten
        flatten_folder(tmp_path, simulate=True, recurse=False, output_manager=output_manager)
        
        # Check log file
        log_files = list(tmp_path.glob("levelzap.log.*.json"))
        assert len(log_files) == 1
        
        import json
        with open(log_files[0], 'r') as f:
            log_data = json.load(f)
        
        assert log_data["meta"]["recursive"] is False
        
        # Check that only immediate subfolder contents would be moved
        moved_actions = [action for action in log_data["actions"] if action["action"] == "move"]
        # Should move: file1.txt, deepfolder (as a folder), file3.txt
        assert len(moved_actions) == 3


def test_duplicate_strategy_rename():
    """Test rename duplicate strategy"""
    output_manager = OutputManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create existing file
        existing_file = tmp_path / "test.txt"
        existing_file.write_text("existing content")
        
        # Test rename strategy
        new_file = tmp_path / "subfolder" / "test.txt"
        new_file.parent.mkdir()
        new_file.write_text("new content")
        
        resolved_path = resolve_duplicate_file(existing_file, new_file, "rename", output_manager)
        
        # Should create a renamed version
        assert resolved_path != existing_file
        assert resolved_path.name.startswith("test_")
        assert resolved_path.suffix == ".txt"


def test_duplicate_strategy_newest():
    """Test newest duplicate strategy"""
    output_manager = OutputManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create older file
        existing_file = tmp_path / "test.txt"
        existing_file.write_text("existing content")
        
        # Create newer file (in subfolder to simulate the scenario)
        import time
        time.sleep(0.01)  # Ensure different timestamp
        new_file = tmp_path / "subfolder" / "test.txt"
        new_file.parent.mkdir()
        new_file.write_text("newer content")
        
        resolved_path = resolve_duplicate_file(existing_file, new_file, "newest", output_manager)
        
        # Should return existing_file path (overwrite with newer)
        assert resolved_path == existing_file


def test_duplicate_strategy_largest():
    """Test largest duplicate strategy"""
    output_manager = OutputManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create smaller file
        existing_file = tmp_path / "test.txt"
        existing_file.write_text("small")
        
        # Create larger file
        new_file = tmp_path / "subfolder" / "test.txt"
        new_file.parent.mkdir()
        new_file.write_text("this is a much larger file content")
        
        resolved_path = resolve_duplicate_file(existing_file, new_file, "largest", output_manager)
        
        # Should return existing_file path (overwrite with larger)
        assert resolved_path == existing_file


def test_recursive_flatten_with_duplicates():
    """Test recursive flattening with duplicate file handling"""
    output_manager = OutputManager()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create directory structure with duplicate filenames
        (tmp_path / "folder1").mkdir()
        (tmp_path / "folder2").mkdir()
        
        # Create files with same name but different content
        (tmp_path / "folder1" / "duplicate.txt").write_text("content1")
        (tmp_path / "folder2" / "duplicate.txt").write_text("content2")
        
        # Test recursive flatten with rename strategy
        flatten_folder(tmp_path, simulate=True, recurse=True, duplicate_strategy="rename", output_manager=output_manager)
        
        # Check log file
        log_files = list(tmp_path.glob("levelzap.log.*.json"))
        assert len(log_files) == 1
        
        import json
        with open(log_files[0], 'r') as f:
            log_data = json.load(f)
        
        # Should have both move and move_renamed actions
        move_actions = [action for action in log_data["actions"] if action["action"] in ["move", "move_renamed"]]
        assert len(move_actions) == 2
        
        # One should be regular move, one should be move_renamed
        regular_moves = [action for action in move_actions if action["action"] == "move"]
        renamed_moves = [action for action in move_actions if action["action"] == "move_renamed"]
        
        assert len(regular_moves) == 1
        assert len(renamed_moves) == 1
        
        # Check that the renamed action has strategy info
        assert "strategy" in renamed_moves[0]
        assert renamed_moves[0]["strategy"] == "rename"