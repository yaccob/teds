Feature: CLI Argument Parsing
  As a developer using TeDS from the command line
  I want argument parsing to work correctly with all valid combinations
  So that I can use all CLI features without errors

  Background:
    Given I have a working directory
    And I have a schema file "schema.yaml" with content:
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

  Scenario: Verify with output-level and report options should work
    When I run the command "verify --output-level all --report comprehensive.adoc test.yaml"
    Then the command should succeed
    And a file "test.report.adoc" should be created

  Scenario: Verify with output-level error and report options should work
    When I run the command "verify --output-level error --report summary.html test.yaml"
    Then the command should succeed
    And a file "test.report.html" should be created

  Scenario: Verify with multiple output levels and report should work
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
            examples:
              - alice@example.com
              - not-an-email
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
            examples:
              - id: "3fa85f64-5717-4562-b3fc-2c963f66afa6"
                name: "Alice Example"
                email: "alice@example.com"
              - id: "not-a-uuid"
                name: "bob"
                email: "x"
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
    When I run the command "verify --output-level all --report comprehensive.adoc sample_tests.yaml"
    Then the command should succeed
    And a file "sample_tests.report.adoc" should be created

  Scenario: Output-level warning with report should work fine
    When I run the command "verify --output-level warning --report comprehensive.adoc test.yaml"
    Then the command should succeed
    And a file "test.report.adoc" should be created

  Scenario: Output-level all without report should work fine
    When I run the command "verify --output-level all test.yaml"
    Then the command should succeed
