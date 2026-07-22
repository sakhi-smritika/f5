#!/usr/bin/env python3
"""
Master seed script to run all Python seed scripts in order.

Run this AFTER `supabase db reset` to apply SQL seeds.
This script will execute all Python seed scripts in the python_seeds/ directory
in numerical order (001_, 002_, etc.).

Usage:
    python seed.py
"""

import importlib
import os
import sys
import time
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file if present

# ANSI color codes for better terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(message: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{message.center(70)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 70}{Colors.ENDC}\n")


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print an info message."""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


def discover_seed_scripts() -> List[Tuple[str, str]]:
    """
    Discover all seed scripts in the python_seeds/ directory.
    Returns a list of tuples: (module_name, file_path)
    """
    python_seeds_dir = Path(__file__).parent / "python_seeds"
    
    if not python_seeds_dir.exists():
        print_error(f"python_seeds/ directory not found at {python_seeds_dir}")
        return []
    
    seed_files = []
    for file in sorted(python_seeds_dir.glob("*.py")):
        # Skip __init__.py and non-numbered files
        if file.name.startswith("__"):
            continue
        if not file.name[0].isdigit():
            continue
        
        module_name = f"python_seeds.{file.stem}"
        seed_files.append((module_name, str(file)))
    
    return seed_files


def run_seed_script(module_name: str, file_path: str) -> bool:
    """
    Run a single seed script.
    Returns True if successful, False otherwise.
    """
    script_name = Path(file_path).stem
    
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}▶ Running: {script_name}{Colors.ENDC}")
    print(f"  Module: {module_name}")
    print(f"  Path: {file_path}")
    print()
    
    start_time = time.time()
    
    try:
        # Import the module
        module = importlib.import_module(module_name)
        
        # Determine the main function to call based on the module name
        if "seed_users" in module_name:
            main_func = getattr(module, "seed_users", None)
        elif "seed_activities" in module_name:
            main_func = getattr(module, "seed_activity", None)
        else:
            # Try to find a main function
            main_func = getattr(module, "main", None) or getattr(module, "seed", None)
        
        if not main_func:
            print_error(f"No main function found in {module_name}")
            print_info("Expected function names: seed_users, seed_activity, main, or seed")
            return False
        
        # Run the seed function
        main_func()
        
        elapsed_time = time.time() - start_time
        print()
        print_success(f"Completed {script_name} in {elapsed_time:.2f}s")
        
        return True
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print()
        print_error(f"Failed to run {script_name} after {elapsed_time:.2f}s")
        print_error(f"Error: {str(e)}")
        
        # Print traceback for debugging
        import traceback
        print(f"\n{Colors.FAIL}Traceback:{Colors.ENDC}")
        traceback.print_exc()
        
        return False


def main():
    """Main entry point for the seed script."""
    print_header("F5 Database Python Seed Scripts")
    
    print_info("This script runs Python seed scripts that create auth users and patch data.")
    print_info("Make sure you've run 'supabase db reset' first to apply SQL seeds.\n")
    
    # Discover all seed scripts
    seed_scripts = discover_seed_scripts()
    
    if not seed_scripts:
        print_warning("No seed scripts found in python_seeds/")
        print_info("Create numbered scripts like: 001_seed_users.py, 002_seed_activities.py")
        sys.exit(1)
    
    print(f"Found {len(seed_scripts)} seed script(s):")
    for module_name, file_path in seed_scripts:
        print(f"  • {Path(file_path).stem}")
    
    # Run each seed script in order
    results = []
    for module_name, file_path in seed_scripts:
        success = run_seed_script(module_name, file_path)
        results.append((Path(file_path).stem, success))
    
    # Print summary
    print_header("Seed Summary")
    
    success_count = sum(1 for _, success in results if success)
    failure_count = len(results) - success_count
    
    for script_name, success in results:
        if success:
            print_success(f"{script_name}")
        else:
            print_error(f"{script_name}")
    
    print()
    print(f"Total: {len(results)} script(s)")
    print(f"Success: {success_count}")
    print(f"Failed: {failure_count}")
    
    if failure_count > 0:
        print()
        print_error("Some seed scripts failed. Check the logs above for details.")
        sys.exit(1)
    else:
        print()
        print_success("All seed scripts completed successfully!")
        print()


if __name__ == "__main__":
    main()
