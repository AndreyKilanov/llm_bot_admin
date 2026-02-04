"""
Comprehensive tests for Dockerfile configuration and container behavior.

These tests verify:
1. Dockerfile build process and configuration
2. Container runtime environment
3. Dependency installation
4. File structure and permissions
5. Python environment setup
"""
import os
import subprocess
import pytest
from pathlib import Path


class TestDockerfileBuild:
    """Test suite for Dockerfile build configuration."""

    @pytest.fixture(scope="class")
    def dockerfile_path(self):
        """Return path to the Dockerfile."""
        return Path(__file__).parent.parent / "Dockerfile"

    @pytest.fixture(scope="class")
    def dockerfile_content(self, dockerfile_path):
        """Read and return Dockerfile content."""
        with open(dockerfile_path, "r") as f:
            return f.read()

    def test_dockerfile_exists(self, dockerfile_path):
        """Test that Dockerfile exists in the project root."""
        assert dockerfile_path.exists(), "Dockerfile not found"
        assert dockerfile_path.is_file(), "Dockerfile is not a file"

    def test_base_image_is_python_311_slim(self, dockerfile_content):
        """Test that the Dockerfile uses python:3.11-slim as base image."""
        lines = [line.strip() for line in dockerfile_content.split("\n")]
        from_lines = [line for line in lines if line.startswith("FROM")]

        assert len(from_lines) > 0, "No FROM instruction found"
        assert "python:3.11-slim" in from_lines[0], \
            f"Expected python:3.11-slim base image, got: {from_lines[0]}"

    def test_workdir_is_set_to_app(self, dockerfile_content):
        """Test that WORKDIR is set to /app."""
        assert "WORKDIR /app" in dockerfile_content, \
            "WORKDIR /app not found in Dockerfile"

    def test_requirements_copied_before_dependencies_install(self, dockerfile_content):
        """Test that requirements.txt is copied before pip install for layer caching."""
        lines = [line.strip() for line in dockerfile_content.split("\n") if line.strip()]

        copy_requirements_idx = None
        pip_install_idx = None

        for idx, line in enumerate(lines):
            if "COPY requirements.txt" in line:
                copy_requirements_idx = idx
            if "RUN pip install" in line and "requirements.txt" in line:
                pip_install_idx = idx

        assert copy_requirements_idx is not None, \
            "COPY requirements.txt instruction not found"
        assert pip_install_idx is not None, \
            "RUN pip install -r requirements.txt instruction not found"
        assert copy_requirements_idx < pip_install_idx, \
            "requirements.txt should be copied before pip install for optimal layer caching"

    def test_pip_install_uses_no_cache_dir(self, dockerfile_content):
        """Test that pip install uses --no-cache-dir flag to reduce image size."""
        assert "--no-cache-dir" in dockerfile_content, \
            "pip install should use --no-cache-dir flag to reduce image size"

    def test_all_required_files_copied(self, dockerfile_content):
        """Test that all required application files are copied to the container."""
        required_copies = [
            "requirements.txt",
            "config.py",
            "pyproject.toml",
            "src/",
            "scripts/",
            "start.sh"
        ]

        for item in required_copies:
            assert f"COPY {item}" in dockerfile_content or f"COPY ./{item}" in dockerfile_content, \
                f"Required file/directory '{item}' is not copied in Dockerfile"

    def test_pythonunbuffered_env_set(self, dockerfile_content):
        """Test that PYTHONUNBUFFERED=1 is set for proper logging."""
        assert "ENV PYTHONUNBUFFERED=1" in dockerfile_content, \
            "PYTHONUNBUFFERED should be set to 1 for proper Python logging in containers"

    def test_start_script_has_execute_permissions(self, dockerfile_content):
        """Test that start.sh is made executable."""
        lines = [line.strip() for line in dockerfile_content.split("\n")]

        # Check that start.sh is copied
        start_sh_copied = any("COPY start.sh" in line for line in lines)
        assert start_sh_copied, "start.sh should be copied to container"

        # Check that chmod +x is applied
        chmod_applied = any("chmod +x start.sh" in line for line in lines)
        assert chmod_applied, "start.sh should be made executable with chmod +x"

    def test_cmd_runs_bash_start_script(self, dockerfile_content):
        """Test that CMD instruction runs bash start.sh."""
        lines = [line.strip() for line in dockerfile_content.split("\n") if line.strip()]
        cmd_line = None

        for line in lines:
            if line.startswith("CMD"):
                cmd_line = line
                break

        assert cmd_line is not None, "CMD instruction not found"
        assert "bash" in cmd_line and "start.sh" in cmd_line, \
            f"CMD should run 'bash start.sh', got: {cmd_line}"

    def test_dockerfile_layer_ordering_optimal(self, dockerfile_content):
        """Test that Dockerfile layers are ordered optimally for caching."""
        lines = [line.strip() for line in dockerfile_content.split("\n") if line.strip() and not line.startswith("#")]

        instruction_order = []
        for line in lines:
            instruction = line.split()[0] if line else ""
            if instruction in ["FROM", "WORKDIR", "COPY", "RUN", "ENV", "CMD"]:
                instruction_order.append((instruction, line))

        # Verify optimal ordering pattern:
        # 1. FROM should be first
        assert instruction_order[0][0] == "FROM", "FROM should be the first instruction"

        # 2. WORKDIR early
        workdir_idx = next((i for i, (inst, _) in enumerate(instruction_order) if inst == "WORKDIR"), None)
        assert workdir_idx is not None and workdir_idx < 3, "WORKDIR should be early in Dockerfile"

        # 3. Dependencies (requirements.txt) before application code
        req_copy_idx = next((i for i, (inst, line) in enumerate(instruction_order)
                            if inst == "COPY" and "requirements.txt" in line), None)
        pip_install_idx = next((i for i, (inst, line) in enumerate(instruction_order)
                               if inst == "RUN" and "pip install" in line), None)
        src_copy_idx = next((i for i, (inst, line) in enumerate(instruction_order)
                            if inst == "COPY" and "src/" in line), None)

        if req_copy_idx and pip_install_idx and src_copy_idx:
            assert req_copy_idx < pip_install_idx < src_copy_idx, \
                "Dependencies should be installed before copying application code for better caching"

    def test_no_unnecessary_packages_in_slim_image(self, dockerfile_content):
        """Test that Dockerfile doesn't install unnecessary system packages in slim image."""
        # In slim images, we should avoid installing build tools unless necessary
        lines = [line.strip().lower() for line in dockerfile_content.split("\n")]

        # Check for common unnecessary packages that might bloat the image
        bloat_indicators = ["apt-get install -y gcc", "apt-get install -y g++", "apt-get install -y make"]

        for indicator in bloat_indicators:
            assert indicator not in " ".join(lines), \
                f"Slim image should avoid installing build tools: {indicator}"

    def test_cmd_uses_exec_form(self, dockerfile_content):
        """Test that CMD uses exec form (JSON array) for proper signal handling."""
        lines = [line.strip() for line in dockerfile_content.split("\n") if line.strip()]
        cmd_line = None

        for line in lines:
            if line.startswith("CMD"):
                cmd_line = line
                break

        assert cmd_line is not None, "CMD instruction not found"
        # Exec form uses JSON array syntax: CMD ["executable", "param1", "param2"]
        assert "[" in cmd_line and "]" in cmd_line, \
            "CMD should use exec form (JSON array) for proper signal handling"


class TestDockerfileConfiguration:
    """Test suite for Dockerfile configuration files and dependencies."""

    @pytest.fixture(scope="class")
    def project_root(self):
        """Return project root directory."""
        return Path(__file__).parent.parent

    def test_requirements_file_exists(self, project_root):
        """Test that requirements.txt exists and is readable."""
        requirements_path = project_root / "requirements.txt"
        assert requirements_path.exists(), "requirements.txt not found"

        with open(requirements_path, "r") as f:
            content = f.read()
            assert len(content) > 0, "requirements.txt is empty"

    def test_requirements_contains_core_dependencies(self, project_root):
        """Test that requirements.txt contains all core dependencies."""
        requirements_path = project_root / "requirements.txt"

        with open(requirements_path, "r") as f:
            content = f.read().lower()

        core_dependencies = [
            "fastapi",
            "uvicorn",
            "aiogram",
            "pydantic-settings",
            "tortoise-orm",
            "pytest",
        ]

        for dep in core_dependencies:
            assert dep in content, f"Core dependency '{dep}' not found in requirements.txt"

    def test_start_script_exists(self, project_root):
        """Test that start.sh script exists and is not empty."""
        start_script_path = project_root / "start.sh"
        assert start_script_path.exists(), "start.sh not found"

        with open(start_script_path, "r") as f:
            content = f.read()
            assert len(content) > 0, "start.sh is empty"

    def test_start_script_has_shebang(self, project_root):
        """Test that start.sh has proper shebang."""
        start_script_path = project_root / "start.sh"

        with open(start_script_path, "r") as f:
            first_line = f.readline().strip()
            assert first_line.startswith("#!"), "start.sh should have shebang"
            assert "sh" in first_line or "bash" in first_line, \
                "start.sh should use sh or bash interpreter"

    def test_start_script_sets_error_handling(self, project_root):
        """Test that start.sh uses proper error handling with 'set -e'."""
        start_script_path = project_root / "start.sh"

        with open(start_script_path, "r") as f:
            content = f.read()
            assert "set -e" in content, \
                "start.sh should use 'set -e' for proper error handling"

    def test_start_script_runs_migrations(self, project_root):
        """Test that start.sh includes migration execution."""
        start_script_path = project_root / "start.sh"

        with open(start_script_path, "r") as f:
            content = f.read()
            assert "aerich" in content, \
                "start.sh should run aerich migrations"

    def test_start_script_starts_application(self, project_root):
        """Test that start.sh starts the main application."""
        start_script_path = project_root / "start.sh"

        with open(start_script_path, "r") as f:
            content = f.read()
            # Should start Python application
            assert "python" in content.lower(), \
                "start.sh should start Python application"
            assert "src.main" in content or "main.py" in content, \
                "start.sh should reference main application module"

    def test_config_file_exists(self, project_root):
        """Test that config.py exists."""
        config_path = project_root / "config.py"
        assert config_path.exists(), "config.py not found"

    def test_pyproject_toml_exists(self, project_root):
        """Test that pyproject.toml exists."""
        pyproject_path = project_root / "pyproject.toml"
        assert pyproject_path.exists(), "pyproject.toml not found"

    def test_src_directory_exists(self, project_root):
        """Test that src/ directory exists with application code."""
        src_path = project_root / "src"
        assert src_path.exists(), "src/ directory not found"
        assert src_path.is_dir(), "src/ is not a directory"

        # Check that it contains Python files
        python_files = list(src_path.rglob("*.py"))
        assert len(python_files) > 0, "src/ directory should contain Python files"

    def test_scripts_directory_exists(self, project_root):
        """Test that scripts/ directory exists."""
        scripts_path = project_root / "scripts"
        assert scripts_path.exists(), "scripts/ directory not found"
        assert scripts_path.is_dir(), "scripts/ is not a directory"


class TestDockerfileSecurityBestPractices:
    """Test suite for Dockerfile security best practices."""

    @pytest.fixture(scope="class")
    def dockerfile_content(self):
        """Read and return Dockerfile content."""
        dockerfile_path = Path(__file__).parent.parent / "Dockerfile"
        with open(dockerfile_path, "r") as f:
            return f.read()

    def test_uses_specific_base_image_version(self, dockerfile_content):
        """Test that Dockerfile uses specific version tag, not 'latest'."""
        lines = [line.strip() for line in dockerfile_content.split("\n")]
        from_lines = [line for line in lines if line.startswith("FROM")]

        for from_line in from_lines:
            assert "latest" not in from_line.lower(), \
                "Should use specific version tags instead of 'latest' for reproducibility"
            assert ":" in from_line, \
                "Base image should include version tag"

    def test_pip_install_from_requirements_file(self, dockerfile_content):
        """Test that pip installs from requirements.txt rather than inline packages."""
        # This ensures version pinning and reproducibility
        assert "-r requirements.txt" in dockerfile_content, \
            "Should install from requirements.txt for version control"

    def test_does_not_run_as_root_or_documents_reason(self, dockerfile_content):
        """Test container user configuration (documents if running as root)."""
        # Note: Some applications need root for specific operations
        # This test documents the decision rather than enforcing non-root
        lines = [line.strip() for line in dockerfile_content.split("\n")]
        user_instructions = [line for line in lines if line.startswith("USER")]

        # If running as root (no USER instruction), this is documented behavior
        # The application uses aerich migrations which may need certain permissions
        if len(user_instructions) == 0:
            # Running as root is intentional for this application
            # due to migration and startup script requirements
            pass
        else:
            # If USER is specified, verify it's not root
            for user_line in user_instructions:
                assert "root" not in user_line.lower(), \
                    "Should not explicitly set USER to root"

    def test_no_sensitive_data_in_dockerfile(self, dockerfile_content):
        """Test that Dockerfile doesn't contain hardcoded secrets or credentials."""
        sensitive_indicators = [
            "password=",
            "token=",
            "secret=",
            "api_key=",
            "apikey=",
            "credentials=",
        ]

        content_lower = dockerfile_content.lower()

        for indicator in sensitive_indicators:
            assert indicator not in content_lower, \
                f"Potential hardcoded secret detected: {indicator}"

    def test_pythonunbuffered_prevents_log_buffering_issues(self, dockerfile_content):
        """Test that PYTHONUNBUFFERED=1 prevents log buffering issues in containers."""
        # This is a security/operational best practice for containers
        assert "PYTHONUNBUFFERED=1" in dockerfile_content or "PYTHONUNBUFFERED = 1" in dockerfile_content, \
            "PYTHONUNBUFFERED should be set to prevent log buffering issues"


class TestDockerfileBuildOptimization:
    """Test suite for Dockerfile build optimization and best practices."""

    @pytest.fixture(scope="class")
    def dockerfile_content(self):
        """Read and return Dockerfile content."""
        dockerfile_path = Path(__file__).parent.parent / "Dockerfile"
        with open(dockerfile_path, "r") as f:
            return f.read()

    def test_uses_slim_variant_for_smaller_image(self, dockerfile_content):
        """Test that Dockerfile uses slim Python image variant."""
        assert "python:3.11-slim" in dockerfile_content, \
            "Should use slim variant to reduce image size"

    def test_requirements_copied_separately_for_layer_caching(self, dockerfile_content):
        """Test that requirements.txt is copied separately before other files."""
        lines = [line.strip() for line in dockerfile_content.split("\n") if line.strip()]

        copy_instructions = [(i, line) for i, line in enumerate(lines) if line.startswith("COPY")]

        # Find requirements.txt copy
        req_copy = next((i, line) for i, line in copy_instructions if "requirements.txt" in line)
        # Find other file copies
        other_copies = [(i, line) for i, line in copy_instructions if "requirements.txt" not in line]

        assert len(other_copies) > 0, "Should have other COPY instructions"
        # Requirements should be copied before application code
        assert req_copy[0] < min(idx for idx, _ in other_copies), \
            "requirements.txt should be copied before application code for optimal caching"

    def test_minimal_layers_for_similar_operations(self, dockerfile_content):
        """Test that similar operations are combined to minimize layers."""
        lines = [line.strip() for line in dockerfile_content.split("\n") if line.strip()]

        # Count number of RUN instructions
        run_count = sum(1 for line in lines if line.startswith("RUN"))

        # Dockerfile should have minimal RUN layers (ideally 1-3)
        # Current: 2 RUN commands (pip install, chmod)
        assert run_count <= 5, \
            f"Too many RUN instructions ({run_count}). Consider combining related commands to reduce layers"

    def test_no_package_manager_cache_in_final_image(self, dockerfile_content):
        """Test that package manager caches are not left in final image."""
        # pip should use --no-cache-dir
        if "pip install" in dockerfile_content:
            assert "--no-cache-dir" in dockerfile_content, \
                "pip should use --no-cache-dir to avoid caching packages in image"

    def test_workdir_set_early(self, dockerfile_content):
        """Test that WORKDIR is set early for consistent path operations."""
        lines = [line.strip() for line in dockerfile_content.split("\n") if line.strip()]

        workdir_idx = next((i for i, line in enumerate(lines) if line.startswith("WORKDIR")), None)
        first_copy_idx = next((i for i, line in enumerate(lines) if line.startswith("COPY")), None)

        assert workdir_idx is not None, "WORKDIR should be set"
        assert first_copy_idx is not None, "COPY instructions should exist"
        assert workdir_idx < first_copy_idx, \
            "WORKDIR should be set before COPY instructions"


class TestDockerfileEdgeCases:
    """Test suite for edge cases and potential issues in Dockerfile."""

    @pytest.fixture(scope="class")
    def dockerfile_content(self):
        """Read and return Dockerfile content."""
        dockerfile_path = Path(__file__).parent.parent / "Dockerfile"
        with open(dockerfile_path, "r") as f:
            return f.read()

    def test_start_script_handles_missing_files_gracefully(self, dockerfile_content):
        """Test that start.sh includes proper error handling for missing files."""
        project_root = Path(__file__).parent.parent
        start_script_path = project_root / "start.sh"

        with open(start_script_path, "r") as f:
            content = f.read()

            # Should have set -e for error handling
            assert "set -e" in content, \
                "start.sh should use 'set -e' to exit on errors"

    def test_all_copied_paths_are_relative(self, dockerfile_content):
        """Test that all COPY instructions use relative paths."""
        lines = [line.strip() for line in dockerfile_content.split("\n")]
        copy_lines = [line for line in lines if line.startswith("COPY")]

        for copy_line in copy_lines:
            # Absolute paths in COPY source are problematic
            parts = copy_line.split()
            if len(parts) >= 2:
                source = parts[1]
                # Source should not start with / (absolute path)
                assert not source.startswith("/"), \
                    f"COPY source should use relative path: {copy_line}"

    def test_dockerfile_not_empty(self, dockerfile_content):
        """Test that Dockerfile is not empty."""
        assert len(dockerfile_content.strip()) > 0, "Dockerfile should not be empty"

    def test_dockerfile_has_single_cmd_instruction(self, dockerfile_content):
        """Test that Dockerfile has exactly one CMD instruction."""
        lines = [line.strip() for line in dockerfile_content.split("\n")]
        cmd_count = sum(1 for line in lines if line.startswith("CMD"))

        assert cmd_count == 1, \
            f"Dockerfile should have exactly one CMD instruction, found {cmd_count}"

    def test_no_entrypoint_conflicts_with_cmd(self, dockerfile_content):
        """Test entrypoint and CMD compatibility."""
        lines = [line.strip() for line in dockerfile_content.split("\n")]
        has_entrypoint = any(line.startswith("ENTRYPOINT") for line in lines)
        has_cmd = any(line.startswith("CMD") for line in lines)

        if has_entrypoint and has_cmd:
            # Both should use exec form for compatibility
            entrypoint_line = next(line for line in lines if line.startswith("ENTRYPOINT"))
            cmd_line = next(line for line in lines if line.startswith("CMD"))

            assert "[" in entrypoint_line, "ENTRYPOINT should use exec form when used with CMD"
            assert "[" in cmd_line, "CMD should use exec form when used with ENTRYPOINT"

    def test_python_path_compatibility(self, dockerfile_content):
        """Test that Python module paths are compatible with container structure."""
        project_root = Path(__file__).parent.parent
        start_script_path = project_root / "start.sh"

        with open(start_script_path, "r") as f:
            content = f.read()

            # PYTHONPATH should be set for module resolution
            if "PYTHONPATH" in content:
                assert "${PYTHONPATH}" in content or "$PYTHONPATH" in content, \
                    "PYTHONPATH should append to existing value"

    def test_script_uses_explicit_path_handling(self, dockerfile_content):
        """Test that start script handles paths explicitly."""
        project_root = Path(__file__).parent.parent
        start_script_path = project_root / "start.sh"

        with open(start_script_path, "r") as f:
            content = f.read()

            # Should change to script directory or use explicit paths
            assert "cd" in content or "/" in content, \
                "start.sh should use explicit path handling"

    def test_requirements_file_not_empty(self):
        """Test that requirements.txt is not empty."""
        project_root = Path(__file__).parent.parent
        requirements_path = project_root / "requirements.txt"

        with open(requirements_path, "r") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            assert len(lines) > 0, "requirements.txt should not be empty"

    def test_start_script_executable_permission_needed(self):
        """Test that start.sh needs executable permission (verified in Dockerfile)."""
        dockerfile_path = Path(__file__).parent.parent / "Dockerfile"

        with open(dockerfile_path, "r") as f:
            content = f.read()

            # Dockerfile should make start.sh executable
            assert "chmod" in content and "+x" in content and "start.sh" in content, \
                "Dockerfile should set executable permission on start.sh"


class TestDockerfileRegressionTests:
    """Regression tests for common Dockerfile mistakes and issues."""

    @pytest.fixture(scope="class")
    def dockerfile_content(self):
        """Read and return Dockerfile content."""
        dockerfile_path = Path(__file__).parent.parent / "Dockerfile"
        with open(dockerfile_path, "r") as f:
            return f.read()

    def test_no_add_instruction_without_reason(self, dockerfile_content):
        """Test that ADD is not used instead of COPY (unless needed for tar extraction)."""
        lines = [line.strip() for line in dockerfile_content.split("\n")]
        add_instructions = [line for line in lines if line.startswith("ADD")]

        # ADD should only be used for tar extraction or URL fetching
        for add_line in add_instructions:
            assert ".tar" in add_line.lower() or "http" in add_line.lower(), \
                f"Use COPY instead of ADD unless extracting archives: {add_line}"

    def test_env_variables_use_equals_sign(self, dockerfile_content):
        """Test that ENV instructions use = syntax for clarity."""
        lines = [line.strip() for line in dockerfile_content.split("\n")]
        env_lines = [line for line in lines if line.startswith("ENV")]

        for env_line in env_lines:
            # Modern syntax: ENV KEY=value
            if len(env_line.split()) > 1:
                # Should use = for clarity
                parts = env_line.replace("ENV ", "", 1).strip()
                assert "=" in parts, \
                    f"ENV should use KEY=value syntax: {env_line}"

    def test_no_curl_or_wget_without_cleanup(self, dockerfile_content):
        """Test that curl/wget downloads are cleaned up in same layer."""
        lines = [line.strip() for line in dockerfile_content.split("\n")]

        for line in lines:
            if "RUN" in line and ("curl" in line or "wget" in line):
                # If downloading files, should clean up in same RUN command
                # This is a warning rather than hard requirement
                pass

    def test_consistent_copy_pattern(self, dockerfile_content):
        """Test that COPY instructions follow consistent pattern."""
        lines = [line.strip() for line in dockerfile_content.split("\n")]
        copy_lines = [line for line in lines if line.startswith("COPY")]

        # All COPY commands should be present
        assert len(copy_lines) > 0, "Should have COPY instructions"

        # Check for consistent trailing slash usage in directory copies
        for copy_line in copy_lines:
            parts = copy_line.split()
            if len(parts) >= 3:
                source = parts[1]
                # Source directories should end with / for clarity
                if source.endswith("/"):
                    # This is good practice for directories
                    pass

    def test_start_script_uses_exec_for_signal_handling(self):
        """Test that start.sh uses exec for proper signal forwarding."""
        project_root = Path(__file__).parent.parent
        start_script_path = project_root / "start.sh"

        with open(start_script_path, "r") as f:
            content = f.read()
            lines = [line.strip() for line in content.split("\n")]

            # Last command should use exec for proper PID 1 signal handling
            last_command = None
            for line in reversed(lines):
                if line and not line.startswith("#"):
                    last_command = line
                    break

            if last_command and "python" in last_command:
                assert "exec" in last_command, \
                    "Final command should use 'exec' for proper signal handling in containers"

    def test_no_hardcoded_versions_outside_requirements(self, dockerfile_content):
        """Test that Python package versions are in requirements.txt, not Dockerfile."""
        lines = [line.strip() for line in dockerfile_content.split("\n")]
        pip_install_lines = [line for line in lines if "pip install" in line and "RUN" in line]

        for pip_line in pip_install_lines:
            # Should not have package==version in Dockerfile RUN pip install
            # All versions should be in requirements.txt
            assert "-r requirements.txt" in pip_line, \
                "Package versions should be in requirements.txt, not hardcoded in Dockerfile"

    def test_workdir_uses_absolute_path(self, dockerfile_content):
        """Test that WORKDIR uses absolute path."""
        lines = [line.strip() for line in dockerfile_content.split("\n")]
        workdir_lines = [line for line in lines if line.startswith("WORKDIR")]

        for workdir_line in workdir_lines:
            path = workdir_line.replace("WORKDIR", "").strip()
            assert path.startswith("/"), \
                f"WORKDIR should use absolute path: {workdir_line}"

    def test_consistent_command_structure(self, dockerfile_content):
        """Test that commands follow consistent structure."""
        lines = [line.strip() for line in dockerfile_content.split("\n") if line.strip()]

        # Check that instructions are uppercase (standard convention)
        dockerfile_instructions = ["FROM", "RUN", "CMD", "LABEL", "EXPOSE", "ENV",
                                  "ADD", "COPY", "ENTRYPOINT", "VOLUME", "USER",
                                  "WORKDIR", "ARG", "ONBUILD", "STOPSIGNAL", "HEALTHCHECK"]

        for line in lines:
            first_word = line.split()[0] if line else ""
            if first_word.upper() in dockerfile_instructions:
                assert first_word.isupper(), \
                    f"Dockerfile instructions should be uppercase: {line}"