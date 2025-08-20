import sys
import tempfile
import subprocess
from pathlib import Path

def test_dry_run_argument_works():
    """Test that --dry-run argument works correctly"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create test structure
        sub = tmp_path / "subfolder"
        sub.mkdir()
        (sub / "file.txt").write_text("test content")
        
        # Test --dry-run
        result = subprocess.run(
            [sys.executable, "levelzap.py", "--dry-run", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parents[1])
        )
        
        assert result.returncode == 0
        assert "Simulation" in result.stdout
        assert "no changes will be made" in result.stdout
        
        # Verify that file is still in original location (not moved)
        assert (sub / "file.txt").exists()
        assert not (tmp_path / "file.txt").exists()

def test_short_s_argument_works():
    """Test that -s argument works correctly"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create test structure  
        sub = tmp_path / "subfolder"
        sub.mkdir()
        (sub / "file.txt").write_text("test content")
        
        # Test -s
        result = subprocess.run(
            [sys.executable, "levelzap.py", "-s", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parents[1])
        )
        
        assert result.returncode == 0
        assert "Simulation" in result.stdout
        assert "no changes will be made" in result.stdout

def test_old_simulate_argument_no_longer_works():
    """Test that --simulate argument no longer works"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Test --simulate should fail
        result = subprocess.run(
            [sys.executable, "levelzap.py", "--simulate", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parents[1])
        )
        
        assert result.returncode != 0
        assert "unrecognized arguments" in result.stderr or "error" in result.stderr.lower()

if __name__ == "__main__":
    test_dry_run_argument_works()
    test_short_s_argument_works() 
    test_old_simulate_argument_no_longer_works()
    print("All tests passed!")