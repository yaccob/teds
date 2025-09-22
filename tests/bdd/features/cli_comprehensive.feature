Feature: TeDS CLI Comprehensive Testing
  As a developer using TeDS
  I want to use all CLI commands effectively
  So that I can verify schemas and generate test specifications

  Background:
    Given I have a temporary workspace

  # === VERIFY COMMAND SCENARIOS ===


  Scenario: Verify with warning output level shows format divergence
    Given I have a schema file "schema.yaml" with content:
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
    Given I have a test specification file "spec.yaml" with content:
      """
      version: "1.0.0"
      tests:
        missing_schema.yaml#/test:
          valid: []
      """
    When I run teds verify "spec.yaml"
    Then the command should exit with code 2
    And the error output should mention "missing_schema.yaml"

  # === GENERATE COMMAND SCENARIOS ===

  Scenario: Generate single reference creates test file
    Given I have a schema file "user.yaml" with content:
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
    And a test file "user.components+schemas+User.tests.yaml" should be created
    And the test file should contain valid YAML content

  Scenario: Generate with omitted target defaults to schema directory
    Given I have a schema file "simple.yaml" with content:
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
    When I run teds generate "nonexistent.yaml#/path"
    Then the command should exit with code 2
    And the error output should mention "nonexistent.yaml"

  # === YAML CONFIGURATION SCENARIOS ===

  Scenario: Generate with JSON configuration string
    Given I have a schema file "api.yaml" with content:
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
    Given I have a schema file "model.yaml" with content:
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

  # === VERSIONING SCENARIOS ===

  Scenario: Version command shows tool and spec version information
    When I run teds --version
    Then the command should exit with code 0
    And the output should contain "teds"
    And the output should contain "spec supported:"
    And the output should contain semantic version format

  Scenario: Verify rejects unsupported major version
    Given I have a test specification file "spec.yaml" with content:
      """
      version: "2.0.0"
      tests:
        dummy.yaml#/: {}
      """
    When I run teds verify "spec.yaml" in-place
    Then the command should exit with code 2
    And the specification file should remain unchanged

  # === ERROR HANDLING SCENARIOS ===

  Scenario: Invalid YAML syntax is properly reported
    Given I have a file "bad.yaml" with content:
      """
      invalid: yaml: syntax here
      """
    When I run teds verify "bad.yaml"
    Then the command should exit with code 2
    And the error output should mention YAML parsing issues

  # === GENERATED FILE VALIDATION SCENARIOS ===

  Scenario: Generated files are validatable
    Given I have a schema file "validatable.yaml" with content:
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
