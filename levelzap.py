import argparse
import os
import sys
import shutil
import json
import hashlib
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from colorama import Fore, Style
import urllib.request

LEVELZAP_VERSION = "0.4"

class OutputManager:
    """Handles all output, logging, and display operations for LevelZap"""
    
    def __init__(self):
        pass
    
    def print_header(self):
        """Print the application header"""
        print(f"{Fore.CYAN}{Style.BRIGHT}LevelZap v{LEVELZAP_VERSION}{Style.RESET_ALL} - Flatten and clean folder structures")
        print(f"{Fore.GREEN}Visit https://github.com/dterracino/levelzap-python for updates{Style.RESET_ALL}\n")
    
    def print_operation_start(self, operation_type, folder_count, root_path, simulate=False):
        """Print operation start information"""
        action = "🔍 Simulating" if simulate else "🚀 Processing"
        print(f"{action} {folder_count} folders in: {root_path}\n")
    
    def print_error(self, message):
        """Print error message with formatting"""
        print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")
    
    def print_warning(self, message):
        """Print warning message with formatting"""
        print(f"{Fore.YELLOW}⚠️  {message}{Style.RESET_ALL}")
    
    def print_success(self, message):
        """Print success message with formatting"""
        print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")
    
    def print_info(self, message):
        """Print info message"""
        print(message)
    
    def print_overwrite_warning(self):
        """Print overwrite mode warning"""
        print("⚠️  WARNING: You have enabled destructive overwrite mode!")
        print("⚠️  Some changes made in this mode will NOT be fully reversible.")
        print("⚠️  Proceed only if you have backups or are sure of the operation.")
    
    def print_log_completion(self, log_path, simulate=False):
        """Print log completion message"""
        if simulate:
            print(f"\n📝 Simulation complete. Log saved to: {log_path}")
        else:
            print(f"\n📝 Log written to: {log_path}")

class FileAnalyzer:
    """Handles file analysis operations like counting and size calculation"""
    
    def __init__(self, output_manager):
        self.output = output_manager
    
    def count_files(self, path, recursive=False):
        """Count files in the given path"""
        try:
            path = Path(path)
            if not path.exists() or not path.is_dir():
                raise ValueError(f"Invalid directory: {path}")
            
            count = 0
            if recursive:
                for item in path.rglob('*'):
                    if item.is_file():
                        count += 1
            else:
                for item in path.iterdir():
                    if item.is_file():
                        count += 1
            
            return count
        except Exception as e:
            self.output.print_error(f"Failed to count files: {e}")
            return 0
    
    def calculate_size(self, path, recursive=False):
        """Calculate total size of files in the given path"""
        try:
            path = Path(path)
            if not path.exists() or not path.is_dir():
                raise ValueError(f"Invalid directory: {path}")
            
            total_size = 0
            if recursive:
                for item in path.rglob('*'):
                    if item.is_file():
                        try:
                            total_size += item.stat().st_size
                        except OSError:
                            # Handle permission errors or broken symlinks
                            continue
            else:
                for item in path.iterdir():
                    if item.is_file():
                        try:
                            total_size += item.stat().st_size
                        except OSError:
                            continue
            
            return total_size
        except Exception as e:
            self.output.print_error(f"Failed to calculate size: {e}")
            return 0
    
    def format_size(self, size_bytes):
        """Format size in bytes to human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

def parse_args():
    parser = argparse.ArgumentParser(
        prog="levelzap",
        description="📂 LevelZap - Flatten subfolders up one level and clean up."
    )
    parser.add_argument("target", nargs="?", default=".", help="Target directory (default: current dir)")
    parser.add_argument("-s", "--simulate", action="store_true", help="Simulate actions without making changes")
    parser.add_argument("-r", "--revert", action="store_true", help="Revert the most recent log file")
    parser.add_argument("-ra", "--revert-all", action="store_true", help="Revert all previous operations in reverse order")
    parser.add_argument("-kl", "--keep-logs", action="store_true", help="Preserve log files after reversion (they will be marked as reverted)")
    parser.add_argument("--recurse", action="store_true", help="Apply recursive logic to all operations")
    
    # Analysis operations
    parser.add_argument("--size", action="store_true", help="Calculate complete size of all files in the path")
    parser.add_argument("--count", action="store_true", help="Calculate number of files in the path")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-m", "--merge", action="store_true", help="Merge folders if names conflict")
    group.add_argument("-o", "--overwrite", action="store_true", help="Allow overwriting files/folders (destructive; ask for confirmation)")

    parser.add_argument("--update", action="store_true", help="Check for a newer version of LevelZap on GitHub")
    parser.add_argument("--list-logs", action="store_true", help="List all logs with status, timestamp, and type")
    parser.add_argument("--verify", action="store_true", help="Verify integrity of all LevelZap log files")
    return parser.parse_args()

def ensure_valid_directory(path, output_manager=None):
    """Ensure the given path is a valid directory"""
    try:
        if not path.exists() or not path.is_dir():
            error_msg = f"Invalid directory: {path}"
            if output_manager:
                output_manager.print_error(error_msg)
            else:
                print(f"❌ {error_msg}")
            sys.exit(1)
    except Exception as e:
        error_msg = f"Error accessing directory {path}: {e}"
        if output_manager:
            output_manager.print_error(error_msg)
        else:
            print(f"❌ {error_msg}")
        sys.exit(1)

def resolve_conflict_path(path: Path) -> Path:
    if not path.exists():
        return path
    base = path.stem
    ext = path.suffix
    parent = path.parent
    i = 1
    while True:
        new_name = f"{base}_{i}{ext}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        i += 1

def perform_action(simulate, action_type, src=None, dst=None, log=None, extra=None, output_manager=None):
    """Perform the specified action with error handling"""
    entry = {
        "action": action_type,
        "timestamp": datetime.now().isoformat()
    }
    if src:
        entry["source"] = str(src)
    if dst:
        entry["destination"] = str(dst)
    if extra:
        entry.update(extra)
    if log is not None:
        log.append(entry)
    if simulate:
        return
    
    try:
        if action_type in ("move", "move_renamed"):
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
        elif action_type == "overwrite_file":
            src.replace(dst)
        elif action_type == "overwrite_folder":
            shutil.rmtree(dst)
            src.rename(dst)
        elif action_type == "delete_folder":
            try:
                src.rmdir()
            except OSError as e:
                warning_msg = f"Could not delete folder (not empty?): {src}"
                if output_manager:
                    output_manager.print_warning(warning_msg)
                else:
                    print(f"⚠️  {warning_msg}")
    except Exception as e:
        error_msg = f"Failed to perform {action_type} on {src}: {e}"
        if output_manager:
            output_manager.print_error(error_msg)
        else:
            print(f"❌ {error_msg}")

def get_log_filename():
    epoch_seconds = int(datetime.now().timestamp())
    return f"levelzap.log.{epoch_seconds}.json"

def flatten_folder(root: Path, simulate=False, merge=False, overwrite=False, output_manager=None):
    """Flatten subfolders with improved error handling and output management"""
    if output_manager is None:
        output_manager = OutputManager()
    
    try:
        log_file = get_log_filename()
        actions = []
        subfolders = [f for f in root.iterdir() if f.is_dir()]
        total_items = sum(len(list(f.iterdir())) for f in subfolders)
        
        output_manager.print_operation_start("flatten", len(subfolders), root, simulate)
        
        with tqdm(total=total_items, desc="Flattening", unit="item") as pbar:
            for folder in subfolders:
                try:
                    for item in folder.iterdir():
                        destination = root / item.name
                        if destination.exists():
                            if destination.is_dir() and item.is_dir():
                                if merge:
                                    for subitem in item.iterdir():
                                        dest_sub = destination / subitem.name
                                        if dest_sub.exists():
                                            if overwrite:
                                                perform_action(simulate, "overwrite_file", src=subitem, dst=dest_sub, log=actions, output_manager=output_manager)
                                                pbar.update(1)
                                                continue
                                            else:
                                                dest_sub = resolve_conflict_path(dest_sub)
                                        perform_action(simulate, "move", src=subitem, dst=dest_sub, log=actions, output_manager=output_manager)
                                        pbar.update(1)
                                    perform_action(simulate, "delete_folder", src=item, log=actions, output_manager=output_manager)
                                    continue
                                elif overwrite:
                                    perform_action(simulate, "overwrite_folder", src=item, dst=destination, log=actions, output_manager=output_manager)
                                    pbar.update(1)
                                    continue
                                else:
                                    destination = resolve_conflict_path(destination)
                            elif destination.is_file() or item.is_file():
                                if overwrite:
                                    perform_action(simulate, "overwrite_file", src=item, dst=destination, log=actions, output_manager=output_manager)
                                    pbar.update(1)
                                    continue
                                else:
                                    new_path = resolve_conflict_path(destination)
                                    perform_action(simulate, "move_renamed", src=item, dst=new_path, log=actions, extra={"original_conflict": str(destination)}, output_manager=output_manager)
                                    pbar.update(1)
                                    continue
                        perform_action(simulate, "move", src=item, dst=destination, log=actions, output_manager=output_manager)
                        pbar.update(1)
                    perform_action(simulate, "delete_folder", src=folder, log=actions, output_manager=output_manager)
                except Exception as e:
                    output_manager.print_error(f"Error processing folder {folder}: {e}")
                    continue
        
        # Write log file
        log_path = root / log_file
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                meta = {
                    "version": LEVELZAP_VERSION,
                    "log_timestamp": datetime.now().isoformat(),
                    "simulated": simulate
                }
                log_data = {
                    "meta": meta,
                    "actions": actions
                }
                raw_log = json.dumps(log_data, indent=2).encode("utf-8")
                log_data["meta"]["hash"] = hashlib.sha256(raw_log).hexdigest()
                f.write(json.dumps(log_data, indent=2))
            
            output_manager.print_log_completion(log_path, simulate)
        except Exception as e:
            output_manager.print_error(f"Failed to write log file: {e}")
    
    except Exception as e:
        if output_manager:
            output_manager.print_error(f"Fatal error during flattening operation: {e}")
        else:
            print(f"❌ Fatal error: {e}")
        sys.exit(1)

def revert_log(log_path: Path, keep_log=False, output_manager=None):
    """Revert operations from a log file with improved error handling"""
    if output_manager is None:
        output_manager = OutputManager()
    
    output_manager.print_info(f"♻️  Reverting changes using log: {log_path}\n")
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)
        
        if log_data.get("meta", {}).get("simulated"):
            output_manager.print_error("Cannot revert a simulated log file.")
            return
        
        stored_hash = log_data.get("meta", {}).get("hash")
        meta_copy = dict(log_data.get("meta", {}))
        meta_copy.pop("hash", None)
        data_for_hash = {
            "meta": meta_copy,
            "actions": log_data.get("actions", [])
        }
        computed_hash = hashlib.sha256(json.dumps(data_for_hash, indent=2).encode("utf-8")).hexdigest()
        
        if stored_hash != computed_hash:
            output_manager.print_error("Log file integrity check failed. Possible modification detected.")
            return
        else:
            output_manager.print_success("Log file passed integrity check.")
        
        actions = log_data.get("actions", [])
    except Exception as e:
        output_manager.print_error(f"Failed to read log file: {e}")
        return
    
    actions.reverse()
    for action in tqdm(actions, desc="Reverting", unit="step"):
        try:
            act_type = action["action"]
            if act_type == "move":
                src = Path(action["destination"])
                dst = Path(action["source"])
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    src.rename(dst)
            elif act_type == "move_renamed":
                src = Path(action["destination"])
                dst = Path(action["source"])
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    src.rename(dst)
            elif act_type == "delete_folder":
                path = Path(action["source"])
                path.mkdir(parents=True, exist_ok=True)
            elif act_type.startswith("overwrite"):
                output_manager.print_warning(f"Cannot revert overwrite: {action.get('source', 'unknown')}")
                continue
        except Exception as e:
            output_manager.print_error(f"Error reverting action {act_type}: {e}")
            continue
    
    try:
        if keep_log:
            with open(log_path, "r+", encoding="utf-8") as f:
                actions = json.load(f)
                f.seek(0)
                json.dump(actions + [{"reverted": True, "timestamp": datetime.now().isoformat()}], f, indent=2)
        else:
            log_path.unlink()
        output_manager.print_success("Revert completed.")
    except Exception as e:
        output_manager.print_error(f"Error updating log file: {e}")

def revert_all_logs(folder: Path, keep_logs=False, output_manager=None):
    """Revert all log files with error handling"""
    if output_manager is None:
        output_manager = OutputManager()
    
    try:
        log_files = sorted(folder.glob("levelzap.log.*.json"), reverse=True)
        if not log_files:
            output_manager.print_error("No log files found to revert.")
            return
        
        for log_file in log_files:
            revert_log(log_file, keep_log=keep_logs, output_manager=output_manager)
    except Exception as e:
        output_manager.print_error(f"Error reverting logs: {e}")

def verify_all_logs(folder: Path, output_manager=None):
    """Verify integrity of all log files with error handling"""
    if output_manager is None:
        output_manager = OutputManager()
    
    try:
        log_files = sorted(folder.glob("levelzap.log.*.json"))
        if not log_files:
            output_manager.print_error("No log files found to verify.")
            return

        for log_file in log_files:
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    log_data = json.load(f)
                stored_hash = log_data.get("meta", {}).get("hash")
                meta_copy = dict(log_data.get("meta", {}))
                meta_copy.pop("hash", None)
                temp_data = {
                    "meta": meta_copy,
                    "actions": log_data.get("actions", [])
                }
                computed_hash = hashlib.sha256(json.dumps(temp_data, indent=2).encode("utf-8")).hexdigest()
                if stored_hash == computed_hash:
                    output_manager.print_success(f"{log_file.name} passed integrity check")
                else:
                    output_manager.print_error(f"{log_file.name} failed integrity check!")
            except Exception as e:
                output_manager.print_error(f"Failed to verify {log_file.name}: {e}")
    except Exception as e:
        output_manager.print_error(f"Error verifying logs: {e}")

def list_logs(folder: Path, output_manager=None):
    """List all log files with status information"""
    if output_manager is None:
        output_manager = OutputManager()
    
    try:
        log_files = sorted(folder.glob("levelzap.log.*.json"))
        if not log_files:
            output_manager.print_error("No log files found.")
            return

        output_manager.print_info("\n📜 Available Logs:")
        for log_file in log_files:
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    log_data = json.load(f)
                    meta = log_data.get("meta", {})
                    timestamp = meta.get("log_timestamp", "unknown")
                    simulated = meta.get("simulated", False)
                    hash_value = meta.get("hash")
                    temp_meta = dict(meta)
                    temp_meta.pop("hash", None)
                    recomputed = hashlib.sha256(json.dumps({"meta": temp_meta, "actions": log_data.get("actions", [])}, indent=2).encode("utf-8")).hexdigest()
                    integrity = hash_value == recomputed
                    status = f"{Fore.GREEN}✅ Valid{Style.RESET_ALL}" if integrity else f"{Fore.RED}❌ Corrupt{Style.RESET_ALL}"
                    sim_flag = "🧪 Simulated" if simulated else "♻️ Real"
                    print(f"{log_file.name} - {timestamp} - {sim_flag} - {status}")
            except Exception as e:
                output_manager.print_error(f"Failed to read {log_file.name}: {e}")
    except Exception as e:
        output_manager.print_error(f"Error listing logs: {e}")

def check_for_update(output_manager=None):
    """Check for updates with error handling"""
    if output_manager is None:
        output_manager = OutputManager()
    
    url = "https://api.github.com/repos/dterracino/levelzap-python/releases/latest"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.load(response)
            latest_version = data.get("tag_name", "").lstrip("v")
            if latest_version and latest_version != LEVELZAP_VERSION:
                output_manager.print_warning(f"Update available: v{latest_version} (You are using v{LEVELZAP_VERSION})")
                output_manager.print_info(f"🔗 Download it from: {data.get('html_url')}")
            else:
                output_manager.print_success(f"You are using the latest version: v{LEVELZAP_VERSION}")
    except Exception as e:
        output_manager.print_error(f"Could not check for update: {e}")

def display_user_selections(args, output_manager):
    """Display the user's selected options"""
    output_manager.print_info("🔧 Operation Details:")
    output_manager.print_info(f"   Target directory: {args.target}")
    
    if args.simulate:
        output_manager.print_info("   Mode: 🔍 Simulation (no changes will be made)")
    
    if args.recurse:
        output_manager.print_info("   Recursive: ✅ Enabled")
    
    if args.merge:
        output_manager.print_info("   Merge conflicts: ✅ Enabled")
    elif args.overwrite:
        output_manager.print_info("   Overwrite conflicts: ⚠️ Enabled (destructive)")
    
    if args.size or args.count:
        output_manager.print_info("   Analysis operations requested")
    
    output_manager.print_info("")

def main():
    output_manager = OutputManager()
    file_analyzer = FileAnalyzer(output_manager)
    
    output_manager.print_header()
    
    try:
        args = parse_args()
        
        # Handle analysis operations first
        if args.size or args.count:
            target_path = Path(args.target).resolve()
            ensure_valid_directory(target_path, output_manager)
            
            display_user_selections(args, output_manager)
            
            if args.size:
                try:
                    total_size = file_analyzer.calculate_size(target_path, args.recurse)
                    formatted_size = file_analyzer.format_size(total_size)
                    recursive_text = " (recursive)" if args.recurse else ""
                    output_manager.print_success(f"Total size{recursive_text}: {formatted_size} ({total_size:,} bytes)")
                except Exception as e:
                    output_manager.print_error(f"Size calculation failed: {e}")
            
            if args.count:
                try:
                    file_count = file_analyzer.count_files(target_path, args.recurse)
                    recursive_text = " (recursive)" if args.recurse else ""
                    output_manager.print_success(f"Total files{recursive_text}: {file_count:,}")
                except Exception as e:
                    output_manager.print_error(f"File count failed: {e}")
            
            if args.size or args.count:
                sys.exit(0)

        # Handle other operations
        if args.list_logs:
            list_logs(Path(args.target).resolve(), output_manager)
            sys.exit(0)

        if args.verify:
            verify_all_logs(Path(args.target).resolve(), output_manager)
            sys.exit(0)

        if args.update:
            check_for_update(output_manager)
            sys.exit(0)
        
        target_path = Path(args.target).resolve()
        ensure_valid_directory(target_path, output_manager)
        
        display_user_selections(args, output_manager)
        
        if args.revert_all:
            revert_all_logs(target_path, keep_logs=args.keep_logs, output_manager=output_manager)
        elif args.revert:
            log_files = sorted(target_path.glob("levelzap.log.*.json"), reverse=True)
            if not log_files:
                output_manager.print_error("No log files found to revert.")
                sys.exit(1)
            revert_log(log_files[0], keep_log=args.keep_logs, output_manager=output_manager)
        else:
            if args.overwrite:
                output_manager.print_overwrite_warning()
                confirm = input("Type YES to continue: ")
                if confirm.strip() != "YES":
                    output_manager.print_error("Aborted by user.")
                    sys.exit(0)
            
            flatten_folder(
                target_path,
                simulate=args.simulate,
                merge=args.merge,
                overwrite=args.overwrite,
                output_manager=output_manager
            )
    
    except KeyboardInterrupt:
        output_manager.print_warning("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        output_manager.print_error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
