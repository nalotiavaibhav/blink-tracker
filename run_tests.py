#!/usr/bin/env python3
"""
Test Runner for Wellness at Work

Provides convenient ways to run different test suites locally.
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n🔄 {description}")
    print(f"📝 Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} - FAILED")
            if result.stderr:
                print("Error output:")
                print(result.stderr)
            if result.stdout:
                print("Standard output:")
                print(result.stdout)
            return False
            
    except FileNotFoundError:
        print(f"❌ {description} - COMMAND NOT FOUND")
        print(f"Make sure the required dependencies are installed.")
        return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run Wellness at Work test suites")
    parser.add_argument("--type", choices=["all", "unit", "integration", "e2e", "backend", "desktop", "quick"], 
                       default="quick", help="Type of tests to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", "-c", action="store_true", help="Run with coverage")
    parser.add_argument("--no-lint", action="store_true", help="Skip linting")
    
    args = parser.parse_args()
    
    # Change to project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print("🧪 Wellness at Work - Test Runner")
    print("=" * 50)
    
    success_count = 0
    total_tests = 0
    
    # Setup base pytest command
    base_pytest = ["python", "-m", "pytest"]
    if args.verbose:
        base_pytest.append("-v")
    if args.coverage:
        base_pytest.extend(["--cov=desktop", "--cov=backend", "--cov=shared", "--cov-report=term"])
    
    # Code Quality Checks (unless skipped)
    if not args.no_lint:
        quality_checks = [
            (["python", "-m", "flake8", "backend/", "desktop/", "shared/", "--count", "--statistics"], 
             "Code Style Check (Flake8)"),
            (["python", "-m", "black", "--check", "backend/", "desktop/", "shared/"], 
             "Code Formatting Check (Black)"),
            (["python", "-m", "isort", "--check-only", "backend/", "desktop/", "shared/"], 
             "Import Sorting Check (isort)")
        ]
        
        for cmd, desc in quality_checks:
            total_tests += 1
            if run_command(cmd, desc):
                success_count += 1
    
    # Test Execution
    test_commands = []
    
    if args.type == "quick" or args.type == "unit":
        test_commands.append((
            base_pytest + ["tests/", "-m", "not slow and not network", "--tb=short"],
            "Quick Unit Tests"
        ))
    
    if args.type == "backend" or args.type == "all":
        test_commands.append((
            base_pytest + ["tests/backend/", "--tb=short"],
            "Backend API Tests"
        ))
    
    if args.type == "desktop" or args.type == "all":
        # Set headless mode for GUI tests
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        
        cmd = base_pytest + ["tests/desktop/", "--tb=short"]
        test_commands.append((cmd, "Desktop Application Tests", env))
    
    if args.type == "integration" or args.type == "all":
        test_commands.append((
            base_pytest + ["tests/integration/", "--tb=short"],
            "Integration Tests"
        ))
    
    if args.type == "e2e" or args.type == "all":
        test_commands.append((
            base_pytest + ["tests/e2e/", "--tb=short", "-s"],
            "End-to-End Tests"
        ))
    
    # Run test commands
    for cmd_info in test_commands:
        total_tests += 1
        if len(cmd_info) == 3:
            cmd, desc, env = cmd_info
            # Run with custom environment
            print(f"\n🔄 {desc}")
            print(f"📝 Command: {' '.join(cmd)}")
            try:
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ {desc} - PASSED")
                    success_count += 1
                else:
                    print(f"❌ {desc} - FAILED")
                    if result.stderr:
                        print(result.stderr)
            except Exception as e:
                print(f"❌ {desc} - ERROR: {e}")
        else:
            cmd, desc = cmd_info
            if run_command(cmd, desc):
                success_count += 1
    
    # Security Check (optional)
    if args.type == "all":
        total_tests += 1
        if run_command(["python", "-m", "safety", "check", "--short-report"], "Security Vulnerability Check"):
            success_count += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print(f"✅ Passed: {success_count}")
    print(f"❌ Failed: {total_tests - success_count}")
    print(f"📊 Total:  {total_tests}")
    
    if success_count == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n💥 {total_tests - success_count} TEST(S) FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
