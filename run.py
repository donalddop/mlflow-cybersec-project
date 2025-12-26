#!/usr/bin/env python
"""
Task runner for the cybersecurity news triage system.
Usage: python run.py [command]
"""

import subprocess
import sys
from pathlib import Path

TASKS = {
    "help": {
        "desc": "Show this help message",
        "cmd": None,
    },
    "web": {
        "desc": "Launch web labeling interface",
        "cmd": "python src/web/app.py",
    },
    "ingest": {
        "desc": "Ingest news from RSS feeds",
        "cmd": "python src/scripts/ingest_news.py",
    },
    "embed": {
        "desc": "Generate embeddings for articles",
        "cmd": "python src/scripts/generate_embeddings.py",
    },
    "label": {
        "desc": "Launch CLI labeling tool",
        "cmd": "python src/scripts/label_news.py",
    },
    "train": {
        "desc": "Train the relevance classifier",
        "cmd": "python src/scripts/train.py",
    },
    "status": {
        "desc": "Show database statistics",
        "cmd": "python src/scripts/db_status.py",
    },
    "init-db": {
        "desc": "Initialize database schema",
        "cmd": "python src/scripts/init_db.py",
    },
    "pipeline": {
        "desc": "Run full pipeline (ingest + embed)",
        "cmd": ["python src/scripts/ingest_news.py", "python src/scripts/generate_embeddings.py"],
    },
}


def show_help():
    """Display available commands."""
    print("\n🛡️  Cybersecurity News Triage - Task Runner\n")
    print("Usage: uv run python run.py [command]\n")
    print("Available commands:")
    for name, task in TASKS.items():
        print(f"  {name:12s}  {task['desc']}")
    print()


def run_task(task_name):
    """Execute a task."""
    if task_name not in TASKS:
        print(f"❌ Unknown task: {task_name}")
        print(f"Run 'python run.py help' to see available commands")
        sys.exit(1)

    task = TASKS[task_name]

    if task_name == "help":
        show_help()
        return

    cmd = task["cmd"]

    if isinstance(cmd, list):
        # Run multiple commands
        for c in cmd:
            print(f"\n▶ Running: {c}\n")
            result = subprocess.run(c, shell=True)
            if result.returncode != 0:
                sys.exit(result.returncode)
    else:
        # Run single command
        print(f"\n▶ Running: {cmd}\n")
        result = subprocess.run(cmd, shell=True)
        sys.exit(result.returncode)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)

    task_name = sys.argv[1]
    run_task(task_name)
