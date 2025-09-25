Feature: Verify Command Tests
  As a developer using TeDS verify command
  I want to validate my JSON schemas against test specifications
  So that I can ensure my schemas meet the required validation rules

  Background:
    Given I have a working directory

  # ==========================================================================
  # Chapter 1: First Test Specification
  # ==========================================================================

  Scenario: Basic email schema validation from tutorial Chapter 1
    Given I have a schema file "user_email.yaml" with content:
      """yaml
      type: string
      format: email
      """
    And I have a test specification file "user_email.tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        user_email.yaml#:
          valid:
            simple_email:
              description: "Basic valid email"
              payload: "alice@example.com"
            email_with_subdomain:
              description: "Email with subdomain"
              payload: "bob@mail.company.com"
          invalid:
            missing_at:
              description: "Email without @ symbol"
              payload: "alice.example.com"
            missing_domain:
              description: "Email without domain"
              payload: "alice@"
      """
    When I run the verify command: `teds verify user_email.tests.yaml`
    Then the command should complete with validation errors
    And the output should contain "simple_email" with result "SUCCESS"
    And the output should contain "email_with_subdomain" with result "SUCCESS"
    And the output should contain "missing_domain" with result "ERROR"

  Scenario: Improved email schema with pattern from tutorial Chapter 1
    Given I have a schema file "user_email_improved.yaml" with content:
      """yaml
      type: string
      format: email
      pattern: '^[^@]+@[^@]+\.[^@]+$'
      """
    And I have a test specification file "user_email_improved.tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        user_email_improved.yaml#:
          invalid:
            missing_at:
              description: "Email without @ symbol should be rejected"
              payload: "alice.example.com"
      """
    When I run the verify command: `teds verify user_email_improved.tests.yaml`
    Then the command should succeed
    And the output should contain "missing_at" with result "SUCCESS"

  # ==========================================================================
  # Chapter 3: Complex Schema Testing Examples
  # ==========================================================================

  Scenario: Test object schema with additionalProperties from tutorial
    Given I have a schema file "user_object.yaml" with content:
      """yaml
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
        email:
          type: string
          format: email
      """
    And I have a test specification file "user_object.tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        user_object.yaml#:
          valid:
            complete_user:
              description: "User with all required fields"
              payload:
                id: "3fa85f64-5717-4562-b3fc-2c963f66afa6"
                name: "Alice Example"
                email: "alice@example.com"
          invalid:
            missing_email:
              description: "Missing required email field"
              payload:
                id: "3fa85f64-5717-4562-b3fc-2c963f66afa6"
                name: "Alice Example"
            extra_field:
              description: "Additional property not allowed"
              payload:
                id: "3fa85f64-5717-4562-b3fc-2c963f66afa6"
                name: "Alice Example"
                email: "alice@example.com"
                age: 25
      """
    When I run the verify command: `teds verify user_object.tests.yaml`
    Then the command should succeed
    And the output should contain "complete_user" with result "SUCCESS"
    And the output should contain "missing_email" with result "SUCCESS"
    And the output should contain "extra_field" with result "SUCCESS"

  Scenario: Test boundary conditions for numeric constraints
    Given I have a schema file "age.yaml" with content:
      """yaml
      type: integer
      minimum: 0
      maximum: 150
      """
    And I have a test specification file "age.tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        age.yaml#:
          valid:
            minimum_age:
              description: "Minimum valid age"
              payload: 0
            maximum_age:
              description: "Maximum valid age"
              payload: 150
            typical_age:
              description: "Typical age"
              payload: 25
          invalid:
            negative_age:
              description: "Below minimum"
              payload: -1
            too_old:
              description: "Above maximum"
              payload: 151
            not_integer:
              description: "Not an integer"
              payload: 25.5
      """
    When I run the verify command: `teds verify age.tests.yaml`
    Then the command should succeed
    And the output should contain "minimum_age" with result "SUCCESS"
    And the output should contain "maximum_age" with result "SUCCESS"
    And the output should contain "negative_age" with result "SUCCESS"
    And the output should contain "too_old" with result "SUCCESS"
    And the output should contain "not_integer" with result "SUCCESS"

  Scenario: Test enum constraints from tutorial
    Given I have a schema file "status.yaml" with content:
      """yaml
      type: string
      enum: ["draft", "published", "archived"]
      """
    And I have a test specification file "status.tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        status.yaml#:
          valid:
            draft_status:
              payload: "draft"
            published_status:
              payload: "published"
            archived_status:
              payload: "archived"
          invalid:
            wrong_case:
              description: "Wrong case should be rejected"
              payload: "Draft"
            unknown_status:
              description: "Status not in enum"
              payload: "deleted"
            empty_string:
              description: "Empty string not in enum"
              payload: ""
      """
    When I run the verify command: `teds verify status.tests.yaml`
    Then the command should succeed
    And the output should contain "draft_status" with result "SUCCESS"
    And the output should contain "published_status" with result "SUCCESS"
    And the output should contain "archived_status" with result "SUCCESS"
    And the output should contain "wrong_case" with result "SUCCESS"
    And the output should contain "unknown_status" with result "SUCCESS"

  # ==========================================================================
  # Chapter 4: Complex Schema Compositions
  # ==========================================================================

  Scenario: Test oneOf composition from tutorial
    Given I have a schema file "contact.yaml" with content:
      """yaml
      oneOf:
        - type: object
          required: [email]
          properties:
            email:
              type: string
              format: email
        - type: object
          required: [phone]
          properties:
            phone:
              type: string
              pattern: '^\+[1-9]\d{1,14}$'
      """
    And I have a test specification file "contact.tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        contact.yaml#:
          valid:
            email_contact:
              description: "Contact with email only"
              payload:
                email: "alice@example.com"
            phone_contact:
              description: "Contact with phone only"
              payload:
                phone: "+1234567890"
          invalid:
            both_fields:
              description: "Both email and phone (should fail oneOf)"
              payload:
                email: "alice@example.com"
                phone: "+1234567890"
            neither_field:
              description: "Neither email nor phone"
              payload:
                name: "Alice"
      """
    When I run the verify command: `teds verify contact.tests.yaml`
    Then the command should succeed
    And the output should contain "email_contact" with result "SUCCESS"
    And the output should contain "phone_contact" with result "SUCCESS"
    And the output should contain "both_fields" with result "SUCCESS"
    And the output should contain "neither_field" with result "SUCCESS"

  # ==========================================================================
  # Chapter 6: Advanced Features
  # ==========================================================================

  Scenario: In-place updates from tutorial
    Given I have a schema file "dummy.yaml" with content:
      """yaml
      type: string
      """
    And I have a test specification file "my_tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        dummy.yaml#:
          valid:
            test_case:
              payload: "test"
      """
    When I run the verify command: `teds verify my_tests.yaml --in-place`
    Then the command should succeed
    And the file "my_tests.yaml" should be updated with results
    And the file should contain "result: SUCCESS"

  Scenario: Parse payload feature from tutorial
    Given I have a schema file "user_schema.yaml" with content:
      """yaml
      type: object
      required: [id, name, email]
      properties:
        id:
          type: string
        name:
          type: string
        email:
          type: string
          format: email
      """
    And I have a test specification file "parse_tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        user_schema.yaml#:
          valid:
            complex_from_string:
              description: "User from JSON string"
              parse_payload: true
              payload: '{"id":"123","name":"Alice","email":"alice@example.com"}'
      """
    When I run the verify command: `teds verify parse_tests.yaml`
    Then the command should succeed
    And the output should contain "complex_from_string" with result "SUCCESS"

  # ==========================================================================
  # Key-as-Payload Feature from Chapter 2
  # ==========================================================================

  Scenario: Key-as-payload parsing from tutorial
    Given I have a schema file "user_age.yaml" with content:
      """yaml
      type: integer
      minimum: 0
      maximum: 150
      """
    And I have a test specification file "age_key_payload.tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        user_age.yaml#:
          valid:
            "25": {description: "Valid adult age"}
            "0": {description: "Minimum age"}
            "150": {description: "Maximum realistic age"}
          invalid:
            "-1": {}
            "151": {}
            '"not-a-number"': {}
            "null": {}
            "25.5": {}
      """
    When I run the verify command: `teds verify age_key_payload.tests.yaml`
    Then the command should succeed
    And the output should contain valid test for number 25
    And the output should contain valid test for number 0
    And the output should contain valid test for number 150
    And the output should contain invalid test for number -1
    And the output should contain invalid test for number 151
    And the output should contain invalid test for string "not-a-number"
    And the output should contain invalid test for null value
    And the output should contain invalid test for float 25.5

  # ==========================================================================
  # Output Level Filtering from Chapter 5
  # ==========================================================================

  Scenario: Output level error filtering
    Given I have a test specification file "error_tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        non_existent_schema.yaml#:
          valid:
            test_case:
              payload: "test"
      """
    When I run the verify command: `teds verify error_tests.yaml --output-level error`
    Then the command should fail
    And the output should contain error information
    And the output should not contain "SUCCESS" entries

  Scenario: Output level all shows everything
    Given I have a schema file "dummy.yaml" with content:
      """yaml
      type: string
      """
    And I have a test specification file "all_tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        dummy.yaml#:
          valid:
            test_case:
              payload: "test"
      """
    When I run the verify command: `teds verify all_tests.yaml --output-level all`
    Then the command should succeed
    And the output should contain "SUCCESS"
    And the output should show detailed information

  # ==========================================================================
  # Roundtrip Workflow from Chapter 9
  # ==========================================================================

  Scenario: Roundtrip workflow with output reuse
    Given I have a schema file "dummy.yaml" with content:
      """yaml
      type: string
      """
    And I have a test specification file "original.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        dummy.yaml#:
          valid:
            test_case:
              payload: "test"
      """
    When I run the verify command: `teds verify original.yaml --output-level all`
    Then the command should succeed
    And the output should contain "SUCCESS"
    When I run the verify command: `teds verify original.yaml --in-place`
    Then the command should succeed
    And the file "original.yaml" should contain results

  # ==========================================================================
  # Multiple Files from Chapter 6
  # ==========================================================================

  Scenario: Verify multiple specifications
    Given I have a schema file "dummy_user.yaml" with content:
      """yaml
      type: string
      """
    And I have a schema file "dummy_product.yaml" with content:
      """yaml
      type: string
      """
    And I have a test specification file "user.tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        dummy_user.yaml#:
          valid:
            test_case:
              payload: "test"
      """
    And I have a test specification file "product.tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        dummy_product.yaml#:
          valid:
            test_case:
              payload: "test"
      """
    When I run the verify command: `teds verify user.tests.yaml product.tests.yaml`
    Then the command should succeed
    And the output should contain results from both files

  # ==========================================================================
  # Status Message Tests
  # ==========================================================================

  Scenario: Verify command outputs status message to stderr
    Given I have a schema file "simple.yaml" with content:
      """yaml
      type: string
      """
    And I have a test specification file "simple.tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        simple.yaml#:
          valid:
            test_case:
              payload: "test"
      """
    When I run the verify command: `teds verify simple.tests.yaml`
    Then the command should succeed
    And the error output should match "^Verifying simple.tests.yaml.*"

  Scenario: Verify command with in-place update outputs status message to stderr
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
    When I run the verify command: `teds verify models/simple.tests.yaml --in-place`
    Then the command should succeed
    And the error output should match "^Updating models/simple.tests.yaml\n$"
