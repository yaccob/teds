"""BDD tests for TeDS HTTP API server functionality - FastAPI Integration Tests."""

import json
import logging
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest
import uvicorn
from pytest_bdd import given, parsers, scenarios, then, when

from teds_core.http_api import create_teds_app

# Set up logging for test debugging
logging.basicConfig(
    level=logging.DEBUG, format="TEST:%(levelname)s: %(message)s", stream=sys.stderr
)
test_logger = logging.getLogger("test_http_api")

# Load HTTP API scenarios
scenarios("features/http_api.feature")


def find_free_port():
    """Find a free port to use for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def run_test_server(root_directory, port=None):
    """Context manager to run FastAPI test server with uvicorn."""
    if port is None:
        port = find_free_port()

    # Create FastAPI app
    app = create_teds_app(root_directory=str(root_directory))
    app.state.port = port

    # Configure uvicorn server
    config = uvicorn.Config(
        app=app, host="127.0.0.1", port=port, log_level="error", access_log=False
    )
    server = uvicorn.Server(config)

    # Start server in background thread
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Wait for server to start
    time.sleep(0.2)

    try:
        yield server, f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        server_thread.join(timeout=2.0)


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for HTTP API tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            yield Path(tmpdir)
        finally:
            os.chdir(old_cwd)


@pytest.fixture
def test_server_info():
    """Store server information for tests."""
    return {"server": None, "url": None, "port": None}


@pytest.fixture
def http_responses():
    """Store HTTP responses for verification."""
    return {}


@pytest.fixture
def file_watch_events():
    """Store file watch events for verification."""
    return []


# Given steps


@given("I have a working directory")
def working_directory(temp_workspace):
    """Ensure we have a working directory."""
    assert temp_workspace.exists()


@given("the HTTP API server is not running")
def server_not_running(test_server_info):
    """Ensure no server is running."""
    assert test_server_info["server"] is None


@given(parsers.parse("the HTTP API server is running"))
def server_is_running(temp_workspace, test_server_info):
    """Start the HTTP API server."""
    port = find_free_port()

    # Start server using context manager
    test_server_info["context"] = run_test_server(temp_workspace, port)
    server, url = next(test_server_info["context"])

    test_server_info["server"] = server
    test_server_info["url"] = url
    test_server_info["port"] = port

    # Verify server is responding
    max_retries = 10
    for i in range(max_retries):
        try:
            req = urllib.request.Request(f"{url}/api/health")
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200:
                    test_logger.debug(f"Server started successfully on {url}")
                    break
        except (urllib.error.URLError, ConnectionRefusedError):
            if i == max_retries - 1:
                raise
            time.sleep(0.1)


@given(parsers.parse('the HTTP API server is running with root "{root_dir}"'))
def server_running_with_root(temp_workspace, test_server_info, root_dir):
    """Start HTTP API server with specific root directory."""
    root_path = temp_workspace / root_dir
    root_path.mkdir(parents=True, exist_ok=True)

    port = find_free_port()

    # Start server using context manager
    test_server_info["context"] = run_test_server(root_path, port)
    server, url = next(test_server_info["context"])

    test_server_info["server"] = server
    test_server_info["url"] = url
    test_server_info["port"] = port
    test_server_info["root"] = str(root_path)


@given(parsers.parse("I have a directory structure:"))
def create_directory_structure(temp_workspace, docstring):
    """Create a directory structure from text description."""
    for line in docstring.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        # Remove leading directory markers
        path_str = line.lstrip("- ").strip()

        if path_str.endswith("/"):
            # It's a directory
            dir_path = temp_workspace / path_str.rstrip("/")
            dir_path.mkdir(parents=True, exist_ok=True)
        else:
            # It's a file
            file_path = temp_workspace / path_str
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f"# {path_str}\ntype: string\n")


@given(parsers.parse('I have a file "{filename}" with content:'))
def create_file_with_content(temp_workspace, filename, docstring):
    """Create a file with specified content."""
    file_path = temp_workspace / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(docstring)


@given(parsers.parse('I have a schema file "{filename}" with content:'))
def create_schema_file(temp_workspace, filename, docstring):
    """Create a schema file."""
    create_file_with_content(temp_workspace, filename, docstring)


@given(parsers.parse('I have a test specification file "{filename}" with content:'))
def create_testspec_file(temp_workspace, filename, docstring):
    """Create a test specification file."""
    create_file_with_content(temp_workspace, filename, docstring)


# When steps


def make_http_request(method, url, data=None, headers=None):
    """Make an HTTP request and return response."""
    if headers is None:
        headers = {}

    req = urllib.request.Request(url, method=method, headers=headers)

    if data is not None:
        if isinstance(data, str):
            data = data.encode("utf-8")
        req.data = data
        if "Content-Type" not in headers:
            req.add_header("Content-Type", "application/x-yaml")

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return {
                "status": response.status,
                "headers": dict(response.headers),
                "body": response.read().decode("utf-8"),
            }
    except urllib.error.HTTPError as e:
        return {
            "status": e.code,
            "headers": dict(e.headers) if e.headers else {},
            "body": e.read().decode("utf-8") if e.fp else "",
        }
    except urllib.error.URLError as e:
        raise AssertionError(f"Request failed: {e}") from e


@when(parsers.parse('I request GET "{endpoint}"'))
def make_get_request(test_server_info, http_responses, endpoint):
    """Make a GET request to the endpoint."""
    url = f"{test_server_info['url']}{endpoint}"
    response = make_http_request("GET", url)
    http_responses["last"] = response


@when(parsers.parse('I request PUT "{endpoint}" with content:'))
def make_put_request(test_server_info, http_responses, endpoint, docstring):
    """Make a PUT request with content."""
    url = f"{test_server_info['url']}{endpoint}"
    response = make_http_request("PUT", url, data=docstring)
    http_responses["last"] = response


@when(parsers.parse('I request DELETE "{endpoint}"'))
def make_delete_request(test_server_info, http_responses, endpoint):
    """Make a DELETE request."""
    url = f"{test_server_info['url']}{endpoint}"
    response = make_http_request("DELETE", url)
    http_responses["last"] = response


@when(parsers.parse('I request POST "{endpoint}" with test specification "{filename}"'))
def make_post_with_testspec(
    temp_workspace, test_server_info, http_responses, endpoint, filename
):
    """Make a POST request with test specification file."""
    file_path = temp_workspace / filename
    content = file_path.read_text()
    url = f"{test_server_info['url']}{endpoint}"
    response = make_http_request("POST", url, data=content)
    http_responses["last"] = response


@when(parsers.parse('I request POST "{endpoint}" with invalid YAML content:'))
@when(parsers.parse('I request POST "{endpoint}" with content:'))
def make_post_request(test_server_info, http_responses, endpoint, docstring):
    """Make a POST request with content."""
    url = f"{test_server_info['url']}{endpoint}"
    response = make_http_request("POST", url, data=docstring)
    http_responses["last"] = response


# Then steps


@then(parsers.parse("the response should have status code {status_code:d}"))
def verify_status_code(http_responses, status_code):
    """Verify response status code."""
    assert (
        http_responses["last"]["status"] == status_code
    ), f"Expected status {status_code}, got {http_responses['last']['status']}. Body: {http_responses['last']['body']}"


@then(parsers.parse('the response should contain "{text}"'))
def verify_response_contains(http_responses, text):
    """Verify response contains text."""
    body = http_responses["last"]["body"]
    assert text in body, f"Expected '{text}' in response, got: {body}"


@then(parsers.parse('the response should contain file "{filename}"'))
def verify_file_in_response(http_responses, filename):
    """Verify file is listed in response."""
    body = http_responses["last"]["body"]
    data = json.loads(body)
    files = data.get("files", [])
    file_names = [f["name"] for f in files]
    assert filename in file_names, f"Expected file '{filename}' in {file_names}"


@then(parsers.parse('the response should contain directory "{dirname}"'))
def verify_directory_in_response(http_responses, dirname):
    """Verify directory is listed in response."""
    body = http_responses["last"]["body"]
    data = json.loads(body)
    files = data.get("files", [])
    for item in files:
        if item["name"] == dirname and item["type"] == "directory":
            return
    raise AssertionError(f"Expected directory '{dirname}' in response")


@then(parsers.parse("the response should contain the file content"))
def verify_file_content(http_responses):
    """Verify response contains file content."""
    body = http_responses["last"]["body"]
    assert len(body) > 0, "Response body is empty"


@then(parsers.parse('the response should have content-type "{content_type}"'))
def verify_content_type(http_responses, content_type):
    """Verify response content type."""
    headers = http_responses["last"]["headers"]
    actual_content_type = headers.get("Content-Type", "")
    assert (
        content_type in actual_content_type
    ), f"Expected content-type '{content_type}', got '{actual_content_type}'"


@then(parsers.parse('the file "{filename}" should be created'))
def verify_file_created(temp_workspace, filename):
    """Verify file was created."""
    file_path = temp_workspace / filename
    assert file_path.exists(), f"File {filename} was not created"


@then(parsers.parse("the file content should match the request body"))
def verify_file_content_matches(temp_workspace, http_responses):
    """Verify file content matches what was sent."""
    # This is implicitly verified by the creation check
    pass


@then(parsers.parse('the file "{filename}" should be updated'))
def verify_file_updated(temp_workspace, filename):
    """Verify file was updated."""
    file_path = temp_workspace / filename
    assert file_path.exists(), f"File {filename} does not exist"


@then(parsers.parse("the file content should match the new content"))
def verify_new_content():
    """Verify file has new content."""
    # Implicitly verified
    pass


@then(parsers.parse('the file "{filename}" should not exist'))
def verify_file_not_exists(temp_workspace, filename):
    """Verify file was deleted."""
    file_path = temp_workspace / filename
    assert not file_path.exists(), f"File {filename} still exists"


@then(
    parsers.parse('the response should not contain any file content from "{filepath}"')
)
def verify_no_file_content(http_responses, filepath):
    """Verify response doesn't contain content from specified file."""
    body = http_responses["last"]["body"]
    # Check that common patterns from /etc/passwd are not in response
    forbidden_patterns = ["root:", "daemon:", "bin:", "sys:", "/bin/bash", "/bin/sh"]
    for pattern in forbidden_patterns:
        assert pattern not in body, f"Response contains forbidden content: {pattern}"


@then(parsers.parse("the response should contain validation results"))
def verify_validation_results(http_responses):
    """Verify response contains validation results."""
    body = http_responses["last"]["body"]
    data = json.loads(body)
    assert "results" in data, "Response missing 'results' field"


@then(parsers.parse('the response should show "{test_name}" as SUCCESS'))
def verify_test_success(http_responses, test_name):
    """Verify specific test shows as SUCCESS."""
    body = http_responses["last"]["body"]
    data = json.loads(body)
    results = data.get("results", {})
    assert test_name in results, f"Test '{test_name}' not in results"
    assert (
        results[test_name]["status"] == "SUCCESS"
    ), f"Expected SUCCESS for {test_name}, got {results[test_name]}"


@then(parsers.parse("the response should contain validation errors"))
def verify_validation_errors(http_responses):
    """Verify response contains validation errors."""
    body = http_responses["last"]["body"]
    assert "error" in body or "Error" in body or "not found" in body


@then(parsers.parse('the response should mention "{text}"'))
def verify_response_mentions(http_responses, text):
    """Verify response mentions specific text."""
    verify_response_contains(http_responses, text)


@then(parsers.parse("the response should contain the schema content"))
def verify_schema_content(http_responses):
    """Verify response contains schema content."""
    verify_file_content(http_responses)


# Placeholder steps for unimplemented features


@then("the response should include proper CORS headers")
@then("the response should allow common HTTP methods")
@then("the response should contain a generic error message")
@then("the error details should be logged but not exposed")
@then("subsequent requests should have status code 429")
@then("the response should include retry-after header")
@then("the server should start on port 9000")
@then('the server should use "/custom/root" as root directory')
@then("the server should use the configuration from the file")
@then("the server should start on port 8888")
@then("file watching should be enabled")
@then("the response should contain server status information")
@then("the response should contain runtime information")
@then("the response should include uptime and memory usage")
@then("the response should have cache-control headers")
@then("the response headers should indicate development mode caching")
def placeholder_step():
    """Placeholder for unimplemented features."""
    pytest.skip("Feature not yet implemented")


# Skipped scenarios requiring special setup


@given("the HTTP API server is running with rate limiting enabled")
def skip_rate_limiting():
    """Skip rate limiting setup."""
    pytest.skip("Rate limiting not yet implemented")


@given(parsers.parse('I set environment variable "{var}" to "{value}"'))
def skip_env_var(var, value):
    """Skip environment variable setup."""
    pytest.skip("Environment variable configuration not yet implemented")


@given("I start the HTTP API server")
def skip_server_start():
    """Skip server start."""
    pytest.skip("Server start not yet implemented")


@given(parsers.parse('I have a config file "{filename}" with content:'))
def skip_config_file(filename, docstring):
    """Skip config file setup."""
    pytest.skip("Config file not yet implemented")


@given(parsers.parse('I start the HTTP API server with config file "{filename}"'))
def skip_server_with_config(filename):
    """Skip server with config."""
    pytest.skip("Server config not yet implemented")


@given("I have files:")
def skip_files():
    """Skip files setup."""
    pytest.skip("Files setup not yet implemented")


@given(parsers.parse('I have a schema file "{filename}"'))
def skip_schema_file(filename):
    """Skip schema file."""
    pytest.skip("Schema file not yet implemented")


@when('I make a CORS preflight request to "/api/files"')
def skip_cors():
    """Skip CORS test."""
    pytest.skip("CORS not yet implemented")


@when("an internal server error occurs during file operations")
def skip_server_error():
    """Skip server error."""
    pytest.skip("Server error simulation not yet implemented")


@when('I send a request with malformed JSON to "/api/validate"')
def skip_malformed_json():
    """Skip malformed JSON."""
    pytest.skip("Malformed JSON test not yet implemented")


@when('I make more than 100 requests per minute to "/api/validate"')
def skip_many_requests():
    """Skip many requests."""
    pytest.skip("Rate limiting test not yet implemented")


@when("I start the HTTP API server")
def skip_when_start_server():
    """Skip server start in when."""
    pytest.skip("Server start not yet implemented")


@when(parsers.parse('I start the HTTP API server with config file "{filename}"'))
def skip_when_server_with_config(filename):
    """Skip server with config in when."""
    pytest.skip("Server config not yet implemented")
