"""Tests to ensure examples work correctly."""

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


@pytest.mark.parametrize(
    "example_file",
    [
        "basic_usage.py",
        "background_tasks.py",
        "scripts.py",
    ],
)
def test_example_runs_successfully(example_file: str) -> None:
    """Test that each example script runs without errors."""
    example_path = EXAMPLES_DIR / example_file
    assert example_path.exists(), f"Example file {example_file} not found"

    result = subprocess.run(
        [sys.executable, str(example_path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, (
        f"Example {example_file} failed with:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_basic_usage_output() -> None:
    """Test that basic_usage.py produces expected output."""
    example_path = EXAMPLES_DIR / "basic_usage.py"
    result = subprocess.run(
        [sys.executable, str(example_path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert "Hello from dependency!" in result.stdout


def test_background_tasks_output() -> None:
    """Test that background_tasks.py produces expected output."""
    example_path = EXAMPLES_DIR / "background_tasks.py"
    result = subprocess.run(
        [sys.executable, str(example_path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert "DB: Opening connection" in result.stdout
    assert "Mailer: Sending" in result.stdout
    assert "DB: Closing connection" in result.stdout


def test_scripts_output() -> None:
    """Test that scripts.py produces expected output."""
    example_path = EXAMPLES_DIR / "scripts.py"
    result = subprocess.run(
        [sys.executable, str(example_path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert "Database: Connecting" in result.stdout
    assert "Cleanup complete" in result.stdout
    assert "Database: Disconnecting" in result.stdout
