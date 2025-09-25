Feature: Reports and CLI Tests
  As a developer using TeDS for comprehensive testing workflows
  I want to generate reports and access CLI functionality
  So that I can document validation results and use all TeDS features effectively

  Background:
    Given I have a working directory

  # ==========================================================================
  # Chapter 5: Report Generation
  # ==========================================================================

  Scenario: Generate HTML report from tutorial
    Given I have a schema file "dummy.yaml" with content:
      """yaml
      type: string
      """
    And I have a test specification file "sample_tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        dummy.yaml#:
          valid:
            test_case:
              payload: "test"
      """
    When I run the verify command: `teds verify sample_tests.yaml --report default.html`
    Then the command should succeed
    And a file "sample_tests.report.html" should be created
    And the HTML file should contain "SUCCESS"

  Scenario: Generate Markdown report from tutorial
    Given I have a schema file "dummy.yaml" with content:
      """yaml
      type: string
      """
    And I have a test specification file "sample_tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        dummy.yaml#:
          valid:
            test_case:
              payload: "test"
      """
    When I run the verify command: `teds verify sample_tests.yaml --report default.md`
    Then the command should succeed
    And a file "sample_tests.report.md" should be created
    And the Markdown file should contain "## Table of Contents"

  Scenario: Custom output filename for reports
    Given I have a schema file "dummy.yaml" with content:
      """yaml
      type: string
      """
    And I have a test specification file "tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        dummy.yaml#:
          valid:
            test_case:
              payload: "test"
      """
    When I run the verify command: `teds verify tests.yaml --report default.html=my_report.html`
    Then the command should succeed
    And a file "my_report.html" should be created

  # ==========================================================================
  # From cli_argument_parsing.feature - CLI Argument Parsing Tests
  # ==========================================================================

  Scenario: Verify with output-level and report options should work
    Given I have a schema file "schema.yaml" with content:
      """yaml
      type: string
      """
    And I have a testspec file "test.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        schema.yaml#:
          valid:
            example1:
              payload: "valid data"
      """
    When I run the command "verify --output-level all --report default.adoc test.yaml"
    Then the command should succeed
    And a file "test.report.adoc" should be created

  Scenario: Verify with output-level error and report options should work
    Given I have a schema file "schema.yaml" with content:
      """yaml
      type: string
      """
    And I have a testspec file "test.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        schema.yaml#:
          valid:
            example1:
              payload: "valid data"
      """
    When I run the command "verify --output-level error --report summary.html test.yaml"
    Then the command should succeed
    And a file "test.report.html" should be created

  Scenario: Verify with multiple output levels and report should work
    Given I have a schema file "schema.yaml" with content:
      """yaml
      type: string
      """
    And I have a testspec file "test.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        schema.yaml#:
          valid:
            example1:
              payload: "valid data"
      """
    When I run the command "verify --output-level warning --report summary.md test.yaml"
    Then the command should succeed
    And a file "test.report.md" should be created

  Scenario: Output-level all with report should work with real demo data
    Given I have a schema file "sample_schemas.yaml" with content:
      """yaml
      asyncapi: "3.0.0"
      info:
        title: Sample Schemas for Validator
        version: "1.0.0"
      components:
        schemas:
          Email:
            type: string
            format: email
          User:
            type: object
            additionalProperties: false
            required: [id, name, email]
            properties:
              id:
                type: string
                format: uuid
              name:
                type: string
                minLength: 1
                pattern: '^[A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)*$'
              email:
                $ref: '#/components/schemas/Email'
      """
    And I have a testspec file "sample_tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        sample_schemas.yaml#/components/schemas/Email:
          valid:
            good email:
              description: simple valid email
              payload: alice@example.com
          invalid:
            "not an email":
              description: not a valid email address
              payload: "not-an-email"
        sample_schemas.yaml#/components/schemas/User:
          valid:
            minimal valid user:
              description: strict object with required fields
              payload:
                id: "3fa85f64-5717-4562-b3fc-2c963f66afa6"
                name: "Alice Example"
                email: "alice@example.com"
            parse as JSON string:
              description: payload provided as JSON string
              parse_payload: true
              payload: "{\"id\":\"3fa85f64-5717-4562-b3fc-2c963f66afa6\",\"name\":\"Bob Builder\",\"email\":\"bob@example.com\"}"
          invalid:
            bad uuid:
              description: id is not a valid UUID
              payload:
                id: "not-a-uuid"
                name: "Alice Example"
                email: "alice@example.com"
      """
    When I run the command "verify --output-level all --report default.adoc sample_tests.yaml"
    Then the command should complete with validation errors
    And a file "sample_tests.report.adoc" should be created

  Scenario: Output-level warning with report should work fine
    Given I have a schema file "schema.yaml" with content:
      """yaml
      type: string
      """
    And I have a testspec file "test.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        schema.yaml#:
          valid:
            example1:
              payload: "valid data"
      """
    When I run the command "verify --output-level warning --report default.adoc test.yaml"
    Then the command should succeed
    And a file "test.report.adoc" should be created

  Scenario: Output-level all without report should work fine
    Given I have a schema file "schema.yaml" with content:
      """yaml
      type: string
      """
    And I have a testspec file "test.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        schema.yaml#:
          valid:
            example1:
              payload: "valid data"
      """
    When I run the command "verify --output-level all test.yaml"
    Then the command should succeed

  # ==========================================================================
  # From report_extensions.feature - Report File Extensions Tests
  # ==========================================================================

  Scenario: AsciiDoc template generates .adoc extension by default
    Given I have a schema file "schema.yaml" with content:
      """yaml
      type: string
      """
    And I have a testspec file "test.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        schema.yaml#:
          valid:
            example1:
              payload: "valid data"
      """
    When I run the command "verify test.yaml --report default.adoc"
    Then the command should succeed
    And a file "test.report.adoc" should be created
    And the file "test.report.adoc" should contain AsciiDoc content

  Scenario: HTML template generates .html extension by default
    Given I have a schema file "schema.yaml" with content:
      """yaml
      type: string
      """
    And I have a testspec file "test.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        schema.yaml#:
          valid:
            example1:
              payload: "valid data"
      """
    When I run the command "verify test.yaml --report summary.html"
    Then the command should succeed
    And a file "test.report.html" should be created
    And the file "test.report.html" should contain HTML content

  Scenario: Markdown template generates .md extension by default
    Given I have a schema file "schema.yaml" with content:
      """yaml
      type: string
      """
    And I have a testspec file "test.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        schema.yaml#:
          valid:
            example1:
              payload: "valid data"
      """
    When I run the command "verify test.yaml --report summary.md"
    Then the command should succeed
    And a file "test.report.md" should be created
    And the file "test.report.md" should contain Markdown content

  # ==========================================================================
  # From cli_comprehensive.feature - CLI Comprehensive Tests
  # ==========================================================================

  Scenario: Verify with warning output level shows format divergence
    Given I have a temporary workspace
    And I have a schema file "schema.yaml" with content:
      """
      components:
        schemas:
          Email:
            type: string
            format: email
            examples:
              - alice@example.com
              - not-an-email
      """
    And I have a test specification file "spec.yaml" with content:
      """
      version: "1.0.0"
      tests:
        schema.yaml#/components/schemas/Email:
          valid:
            valid_email:
              payload: alice@example.com
            questionable_email:
              payload: not-an-email
          invalid:
            explicit_invalid:
              payload: not-an-email
      """
    When I run teds verify "spec.yaml" with output level "warning"
    Then the command should exit with code 1
    And the output should exactly match:
      """
      version: 1.0.0
      tests:
        schema.yaml#/components/schemas/Email:
          valid:
            .components.schemas.Email.examples[1]:
              payload: not-an-email
              result: WARNING
              from_examples: true
              warnings:
              - generated: |
                  Relies on JSON Schema 'format' assertion (format: email).
                  Validators that *enforce* 'format' will reject this instance.
                  Consider enforcing the expected format by adding an explicit 'pattern' property to the schema.
                code: format-divergence
            questionable_email:
              payload: not-an-email
              result: WARNING
              warnings:
              - generated: |
                  Relies on JSON Schema 'format' assertion (format: email).
                  Validators that *enforce* 'format' will reject this instance.
                  Consider enforcing the expected format by adding an explicit 'pattern' property to the schema.
                code: format-divergence
          invalid:
            explicit_invalid:
              payload: not-an-email
              result: ERROR
              message: |
                UNEXPECTEDLY VALID
                A validator that *ignores* 'format' accepted this instance, while a strict validator (enforcing 'format') might reject it as desired (format: email).
                Consider enforcing the expected format by adding an explicit 'pattern' property to the schema.
      """

  Scenario: CLI reports missing schema file error
    Given I have a temporary workspace
    And I have a test specification file "spec.yaml" with content:
      """
      version: "1.0.0"
      tests:
        missing_schema.yaml#/test:
          valid: []
      """
    When I run teds verify "spec.yaml"
    Then the command should exit with code 2
    And the error output should mention "missing_schema.yaml"

  Scenario: Generate single reference creates test file
    Given I have a temporary workspace
    And I have a schema file "user.yaml" with content:
      """
      components:
        schemas:
          User:
            type: object
            properties:
              name:
                type: string
                examples: ["John"]
              email:
                type: string
                format: email
      """
    When I run teds generate "user.yaml#/components/schemas/User"
    Then the command should exit with code 0
    And a test file "user.tests.yaml" should be created
    And the test file should contain valid YAML content

  Scenario: Generate with omitted target defaults to schema directory
    Given I have a temporary workspace
    And I have a schema file "simple.yaml" with content:
      """
      type: object
      properties:
        name:
          type: string
      """
    When I run teds generate "simple.yaml#/"
    Then the command should exit with code 0
    And a test file "simple.tests.yaml" should be created

  Scenario: Generate reports missing schema file
    Given I have a temporary workspace
    When I run teds generate "nonexistent.yaml#/path"
    Then the command should exit with code 2
    And the error output should mention "nonexistent.yaml"

  Scenario: Generate with JSON configuration string
    Given I have a temporary workspace
    And I have a schema file "api.yaml" with content:
      """
      components:
        schemas:
          User:
            type: object
            properties:
              name:
                type: string
      """
    When I run teds generate with JSON config '{"api.yaml": {"paths": ["$.components.schemas.User"], "target": "api.tests.yaml"}}'
    Then the command should exit with code 0
    And a test file "api.tests.yaml" should be created

  Scenario: Generate with file-based YAML configuration
    Given I have a temporary workspace
    And I have a schema file "model.yaml" with content:
      """
      definitions:
        Person:
          type: object
      """
    And I have a config file "generate.yaml" with content:
      """
      model.yaml:
        paths:
          - "$.definitions.Person"
        target: "model.tests.yaml"
      """
    When I run teds generate "@generate.yaml"
    Then the command should exit with code 0
    And a test file "model.tests.yaml" should be created

  Scenario: Version command shows tool and spec version information
    When I run teds --version
    Then the command should exit with code 0
    And the output should contain "teds"
    And the output should contain "spec supported:"
    And the output should contain semantic version format

  Scenario: Verify rejects unsupported major version
    Given I have a temporary workspace
    And I have a test specification file "spec.yaml" with content:
      """
      version: "2.0.0"
      tests:
        dummy.yaml#/: {}
      """
    When I run teds verify "spec.yaml" in-place
    Then the command should exit with code 2
    And the specification file should remain unchanged

  Scenario: Invalid YAML syntax is properly reported
    Given I have a temporary workspace
    And I have a file "bad.yaml" with content:
      """
      invalid: yaml: syntax here
      """
    When I run teds verify "bad.yaml"
    Then the command should exit with code 2
    And the error output should mention YAML parsing issues

  Scenario: Generated files are validatable
    Given I have a temporary workspace
    And I have a schema file "validatable.yaml" with content:
      """
      type: object
      properties:
        name:
          type: string
        age:
          type: integer
      """
    When I run teds generate "validatable.yaml#/"
    Then the command should exit with code 0
    And a test file "validatable.tests.yaml" should be created
    And the generated file should be validatable with teds verify

  # ==========================================================================
  # From template_integer_handling.feature - Template Integer Handling Tests
  # ==========================================================================

  Scenario: Generate comprehensive report with integer payloads
    Given I have a test spec with integer payloads
    When I generate a comprehensive AsciiDoc report
    Then the report should be generated successfully
    And the report should contain formatted integer values

  Scenario: Template truncate filter works with mixed payload types
    Given I have a test spec with mixed payload types including integers
    When I generate a comprehensive AsciiDoc report
    Then the report should handle all payload types correctly
    And no "object of type 'int' has no len()" error should occur

  # ==========================================================================
  # Status Message Tests
  # ==========================================================================

  Scenario: Report generation outputs status message to stderr
    Given I have a subdirectory "models"
    Given I have a schema file "models/simple.yaml" with content:
      """yaml
      type: string
      """
    And I have a test specification file "models/simple.tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        simple.yaml#:
          valid:
            test_case:
              payload: "test"
      """
    When I run the verify command: `teds verify models/simple.tests.yaml --report default.html`
    Then the command should succeed
    And the error output should match "^Generating report models/simple.tests.report.html\n$"
