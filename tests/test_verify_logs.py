import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from levelzap import flatten_folder, verify_all_logs

def test_verify_simulation_log(tmp_path, capsys):
    sub = tmp_path / "subfolder"
    sub.mkdir()
    (sub / "file.txt").write_text("data")
    # Generate log file in simulation mode
    flatten_folder(tmp_path, simulate=True)
    # Capture output from verification
    capsys.readouterr()
    verify_all_logs(tmp_path)
    captured = capsys.readouterr()
    assert "passed integrity check" in captured.out
