import argparse
import os
import sys
import shutil
import json
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from colorama import Fore, Style
import urllib.request

LEVELZAP_VERSION = "0.2"

def parse_args():
    parser = argparse.ArgumentParser(
        description="📂 LevelZap - Flatten subfolders up one level and clean up."
    )
    parser.add_argument("target", nargs="?", default=".", help="Target directory (default: current dir)")
    parser.add_argument("-s", "--simulate", action="store_true", help="Simulate actions without making changes")
    parser.add_argument("-r", "--revert", action="store_true", help="Revert the most recent log file")
    parser.add_argument("-ra", "--revert-all", action="store_true", help="Revert all previous operations in reverse order")
    parser.add_argument("-kl", "--keep-logs", action="store_true", help="Preserve log files after reversion (they will be marked as reverted)")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-m", "--merge", action="store_true", help="Merge folders if names conflict")
    group.add_argument("-o", "--overwrite", action="store_true", help="Allow overwriting files/folders (destructive; ask for confirmation)")

    parser.add_argument("--update", action="store_true", help="Check for a newer version of LevelZap on GitHub")
    return parser.parse_args()

def ensure_valid_directory(path):
    if not path.exists() or not path.is_dir():
        print(f"❌ Invalid directory: {path}")
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

def perform_action(simulate, action_type, src=None, dst=None, log=None, extra=None):
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
        except OSError:
            print(f"⚠️  Could not delete folder (not empty?): {src}")

def get_log_filename():
    timestamp = datetime.now().isoformat(timespec='seconds').replace(":", "-")
    return f"levelzap_log_{timestamp}.json"

def flatten_folder(root: Path, simulate=False, merge=False, overwrite=False):
    log_file = get_log_filename()
    actions = []
    subfolders = [f for f in root.iterdir() if f.is_dir()]
    total_items = sum(len(list(f.iterdir())) for f in subfolders)
    print(f"{'🔍 Simulating' if simulate else '🚀 Processing'} {len(subfolders)} folders in: {root}\n")
    with tqdm(total=total_items, desc="Flattening", unit="item") as pbar:
        for folder in subfolders:
            for item in folder.iterdir():
                destination = root / item.name
                if destination.exists():
                    if destination.is_dir() and item.is_dir():
                        if merge:
                            for subitem in item.iterdir():
                                dest_sub = destination / subitem.name
                                if dest_sub.exists():
                                    if overwrite:
                                        perform_action(simulate, "overwrite_file", src=subitem, dst=dest_sub, log=actions)
                                        pbar.update(1)
                                        continue
                                    else:
                                        dest_sub = resolve_conflict_path(dest_sub)
                                perform_action(simulate, "move", src=subitem, dst=dest_sub, log=actions)
                                pbar.update(1)
                            perform_action(simulate, "delete_folder", src=item, log=actions)
                            continue
                        elif overwrite:
                            perform_action(simulate, "overwrite_folder", src=item, dst=destination, log=actions)
                            pbar.update(1)
                            continue
                        else:
                            destination = resolve_conflict_path(destination)
                    elif destination.is_file() or item.is_file():
                        if overwrite:
                            perform_action(simulate, "overwrite_file", src=item, dst=destination, log=actions)
                            pbar.update(1)
                            continue
                        else:
                            new_path = resolve_conflict_path(destination)
                            perform_action(simulate, "move_renamed", src=item, dst=new_path, log=actions, extra={"original_conflict": str(destination)})
                            pbar.update(1)
                            continue
                perform_action(simulate, "move", src=item, dst=destination, log=actions)
                pbar.update(1)
            perform_action(simulate, "delete_folder", src=folder, log=actions)
    if not simulate:
        log_path = root / log_file
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({
                "version": LEVELZAP_VERSION,
                "log_timestamp": datetime.now().isoformat(),
                "actions": actions
            }, f, indent=2)
        print(f"\n📝 Log written to: {log_path}")
    else:
        print(f"\n📝 Simulation complete. No changes made.")

def revert_log(log_path: Path, keep_log=False):
    print(f"♻️  Reverting changes using log: {log_path}\n")
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)
        actions = log_data.get("actions", [])
    except Exception as e:
        print(f"❌ Failed to read log file: {e}")
        return
    actions.reverse()
    for action in tqdm(actions, desc="Reverting", unit="step"):
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
            print(f"⚠️  Cannot revert overwrite: {action['original']}")
            continue
    if keep_log:
        with open(log_path, "r+", encoding="utf-8") as f:
            actions = json.load(f)
            f.seek(0)
            json.dump(actions + [{"reverted": True, "timestamp": datetime.now().isoformat()}], f, indent=2)
    else:
        log_path.unlink()
    print("\n✅ Revert completed.")

def revert_all_logs(folder: Path, keep_logs=False):
    log_files = sorted(folder.glob("levelzap_log_*.json"), reverse=True)
    for log_file in log_files:
        revert_log(log_file, keep_log=keep_logs)

def check_for_update():
    url = "https://api.github.com/repos/dterracino/levelzap-python/releases/latest"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.load(response)
            latest_version = data.get("tag_name", "").lstrip("v")
            if latest_version and latest_version != LEVELZAP_VERSION:
                print(f"{Fore.YELLOW}🚨 Update available: v{latest_version} (You are using v{LEVELZAP_VERSION})")
                print(f"🔗 Download it from: {data.get('html_url')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}✅ You are using the latest version: v{LEVELZAP_VERSION}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ Could not check for update: {e}{Style.RESET_ALL}")

def main():
    print(f"{Fore.CYAN}{Style.BRIGHT}LevelZap v{LEVELZAP_VERSION}{Style.RESET_ALL} - Flatten and clean folder structures")
    print(f"{Fore.GREEN}Visit https://github.com/dterracino/levelzap-python for updates{Style.RESET_ALL}\n")
    args = parse_args()

    if args.update:
        check_for_update()
        sys.exit(0)
    target_path = Path(args.target).resolve()
    ensure_valid_directory(target_path)
    if args.revert_all:
        revert_all_logs(target_path, keep_logs=args.keep_logs)
    elif args.revert:
        log_files = sorted(target_path.glob("levelzap_log_*.json"), reverse=True)
        if not log_files:
            print("❌ No log files found to revert.")
            sys.exit(1)
        revert_log(log_files[0], keep_log=args.keep_logs)
    else:
        if args.overwrite:
            print("⚠️  WARNING: You have enabled destructive overwrite mode!")
            print("⚠️  Some changes made in this mode will NOT be fully reversible.")
            print("⚠️  Proceed only if you have backups or are sure of the operation.")
            confirm = input("Type YES to continue: ")
            if confirm.strip() != "YES":
                print("❌ Aborted by user.")
                sys.exit(0)
        flatten_folder(
            target_path,
            simulate=args.simulate,
            merge=args.merge,
            overwrite=args.overwrite
        )

if __name__ == "__main__":
    main()
