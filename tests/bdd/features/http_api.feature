Feature: HTTP API Local Server
  As a developer using TeDS HTTP API
  I want to run a local web server for schema validation
  So that I can use TeDS functionality through a web interface

  Background:
    Given I have a working directory
    And the HTTP API server is not running

  # ==========================================================================
  # File System API Endpoints
  # ==========================================================================

  Scenario: List directory contents via API
    Given I have a directory structure:
      """
      test_dir/
      test_dir/schema.yaml
      test_dir/test.tests.yaml
      test_dir/subdir/
      test_dir/subdir/nested.yaml
      """
    And the HTTP API server is running with root "test_dir"
    When I request GET "/api/files"
    Then the response should contain file "schema.yaml"
    And the response should contain file "test.tests.yaml"
    And the response should contain directory "subdir"
    And the response should have status code 200

  Scenario: Read file content via API
    Given I have a file "schema.yaml" with content:
      """yaml
      type: string
      format: email
      """
    And the HTTP API server is running
    When I request GET "/api/files/schema.yaml"
    Then the response should contain the file content
    And the response should have content-type "application/x-yaml"
    And the response should have status code 200

  Scenario: Write file content via API
    Given the HTTP API server is running
    When I request PUT "/api/files/new_schema.yaml" with content:
      """yaml
      type: integer
      minimum: 0
      """
    Then the file "new_schema.yaml" should be created
    And the file content should match the request body
    And the response should have status code 201

  Scenario: Update existing file via API
    Given I have a file "existing.yaml" with content:
      """yaml
      type: string
      """
    And the HTTP API server is running
    When I request PUT "/api/files/existing.yaml" with content:
      """yaml
      type: string
      format: email
      """
    Then the file "existing.yaml" should be updated
    And the file content should match the new content
    And the response should have status code 200

  Scenario: Delete file via API
    Given I have a file "to_delete.yaml" with content:
      """yaml
      type: string
      """
    And the HTTP API server is running
    When I request DELETE "/api/files/to_delete.yaml"
    Then the file "to_delete.yaml" should not exist
    And the response should have status code 204

  Scenario: Access file outside root directory should be forbidden
    Given the HTTP API server is running with root "safe_dir"
    When I request GET "/api/files/../../../etc/passwd"
    Then the response should have status code 403
    And the response should contain "Access denied"
    And the response should not contain any file content from "/etc/passwd"

  # ==========================================================================
  # Schema Validation API
  # ==========================================================================

  Scenario: Validate test specification via API
    Given I have a schema file "user.yaml" with content:
      """yaml
      type: object
      required: [name, email]
      properties:
        name:
          type: string
        email:
          type: string
          format: email
      """
    And I have a test specification file "user.tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        user.yaml#:
          valid:
            valid_user:
              payload:
                name: "Alice"
                email: "alice@example.com"
          invalid:
            missing_email:
              payload:
                name: "Alice"
      """
    And the HTTP API server is running
    When I request POST "/api/validate" with test specification "user.tests.yaml"
    Then the response should contain validation results
    And the response should show "valid_user" as SUCCESS
    And the response should show "missing_email" as SUCCESS
    And the response should have status code 200

  Scenario: Validate invalid test specification format
    Given the HTTP API server is running
    When I request POST "/api/validate" with invalid YAML content:
      """
      invalid: yaml: content
      missing: quotes
      """
    Then the response should have status code 400
    And the response should contain "Invalid YAML format"

  Scenario: Validate with non-existent schema reference
    Given the HTTP API server is running
    When I request POST "/api/validate" with content:
      """yaml
      version: "1.0.0"
      tests:
        non_existent.yaml#:
          valid:
            test_case:
              payload: "test"
      """
    Then the response should have status code 422
    And the response should contain validation errors
    And the response should mention "non_existent.yaml"

  # NOTE: Real-time file watching features moved to web_ide.feature
  # Focus on HTTP API functionality first

  # ==========================================================================
  # Static File Serving
  # ==========================================================================

  Scenario: Serve static schema files
    Given I have a schema file "api_schema.yaml" with content:
      """yaml
      type: object
      properties:
        id:
          type: string
      """
    And the HTTP API server is running
    When I request GET "/static/api_schema.yaml"
    Then the response should contain the schema content
    And the response should have content-type "application/x-yaml"
    And the response should have status code 200
