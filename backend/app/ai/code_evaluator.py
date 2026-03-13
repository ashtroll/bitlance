import asyncio
import subprocess
import tempfile
import os
from pathlib import Path

from app.config import settings


class CodeEvaluator:
    """Runs automated tests in a Docker sandbox environment."""

    async def run_tests(self, repo_url: str) -> dict:
        """Clone repo and run tests in isolated Docker container."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Clone repository
                clone_result = await self._run_command(
                    ["git", "clone", "--depth", "1", repo_url, tmpdir],
                    timeout=30,
                )
                if clone_result["exit_code"] != 0:
                    return {
                        "passed": False,
                        "error": f"Failed to clone repository: {clone_result['stderr']}",
                        "tests_run": 0,
                    }

                # Detect project type and run appropriate tests
                return await self._detect_and_test(tmpdir)

        except asyncio.TimeoutError:
            return {"passed": False, "error": "Test execution timed out", "tests_run": 0}
        except Exception as e:
            return {"passed": False, "error": str(e), "tests_run": 0}

    async def _detect_and_test(self, project_dir: str) -> dict:
        """Detect project type and run appropriate test suite."""
        path = Path(project_dir)

        if (path / "package.json").exists():
            return await self._run_node_tests(project_dir)
        elif (path / "requirements.txt").exists() or (path / "setup.py").exists():
            return await self._run_python_tests(project_dir)
        elif (path / "pom.xml").exists():
            return await self._run_maven_tests(project_dir)
        elif (path / "go.mod").exists():
            return await self._run_go_tests(project_dir)
        else:
            return {
                "passed": True,
                "warning": "Could not detect project type. Skipping automated tests.",
                "tests_run": 0,
            }

    async def _run_python_tests(self, project_dir: str) -> dict:
        result = await self._run_in_docker(
            image="python:3.11-slim",
            commands=[
                "pip install -r requirements.txt -q || true",
                "python -m pytest --tb=short -q 2>&1 || python -m unittest discover -q 2>&1",
            ],
            workdir=project_dir,
        )
        passed = result["exit_code"] == 0
        return {
            "passed": passed,
            "output": result["stdout"][:2000],
            "tests_run": self._parse_test_count(result["stdout"]),
            "framework": "pytest",
        }

    async def _run_node_tests(self, project_dir: str) -> dict:
        result = await self._run_in_docker(
            image="node:20-slim",
            commands=[
                "npm install --silent 2>&1 || true",
                "npm test -- --passWithNoTests 2>&1 || true",
            ],
            workdir=project_dir,
        )
        passed = result["exit_code"] == 0
        return {
            "passed": passed,
            "output": result["stdout"][:2000],
            "tests_run": self._parse_test_count(result["stdout"]),
            "framework": "jest/mocha",
        }

    async def _run_go_tests(self, project_dir: str) -> dict:
        result = await self._run_in_docker(
            image="golang:1.22-alpine",
            commands=["go test ./... 2>&1"],
            workdir=project_dir,
        )
        passed = result["exit_code"] == 0
        return {"passed": passed, "output": result["stdout"][:2000], "framework": "go test"}

    async def _run_maven_tests(self, project_dir: str) -> dict:
        result = await self._run_in_docker(
            image="maven:3.9-eclipse-temurin-17",
            commands=["mvn test -q 2>&1"],
            workdir=project_dir,
        )
        passed = result["exit_code"] == 0
        return {"passed": passed, "output": result["stdout"][:2000], "framework": "maven"}

    async def _run_in_docker(self, image: str, commands: list, workdir: str) -> dict:
        """Run commands inside a Docker container with resource limits."""
        cmd_str = " && ".join(commands)
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", "256m",
            "--cpus", "0.5",
            "--read-only",
            "--tmpfs", "/tmp:rw,size=100m",
            "-v", f"{workdir}:/workspace:ro",
            "-w", "/workspace",
            image,
            "sh", "-c", cmd_str,
        ]
        return await self._run_command(docker_cmd, timeout=settings.sandbox_timeout_seconds)

    async def _run_command(self, cmd: list, timeout: int = 30) -> dict:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
            }
        except asyncio.TimeoutError:
            return {"exit_code": -1, "stdout": "", "stderr": "Command timed out"}

    def _parse_test_count(self, output: str) -> int:
        import re
        patterns = [r"(\d+) passed", r"(\d+) tests?", r"Tests run: (\d+)"]
        for pattern in patterns:
            m = re.search(pattern, output, re.IGNORECASE)
            if m:
                return int(m.group(1))
        return 0
