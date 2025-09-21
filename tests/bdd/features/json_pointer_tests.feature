Feature: JSON Pointer CLI Generation Tests
  As a developer using TeDS with JSON Pointer syntax
  I want to generate tests using the CLI with JSON Pointer references
  So that I can quickly create test specifications for schema validation

  Background:
    Given I have a working directory

  Scenario: Generate tests with schema examples integration
    Given I have a schema file "product.yaml" with content:
      """yaml
      $defs:
        Product:
          type: object
          properties:
            title:
              type: string
            price:
              type: number
          examples:
            - title: Laptop
              price: 999.99
            - title: Mouse
              price: 29.99
      """
    When I run the generate command: `teds generate product.yaml#/$defs`
    Then a test file "product.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        product.yaml#/$defs/Product:
          valid:
            example_0:
              payload:
                title: Laptop
                price: 999.99
              from_examples: true
            example_1:
              payload:
                title: Mouse
                price: 29.99
              from_examples: true
          invalid: null
      """

  Scenario: Generate tests with relative path resolution
    Given I have a subdirectory "models"
    And I have a schema file "models/user.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
          properties:
            id:
              type: string
      """
    When I run the generate command: `teds generate models/user.yaml#/$defs`
    Then a test file "models/user.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        user.yaml#/$defs/User:
          valid: null
          invalid: null
      """

  Scenario: Generate tests with explicit target file specification
    Given I have a schema file "schema.yaml" with content:
      """yaml
      $defs:
        Item:
          type: string
      """
    When I run the generate command: `teds generate schema.yaml#/$defs/Item --output custom.tests.yaml`
    Then a test file "custom.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        schema.yaml#/$defs/Item:
          valid: null
          invalid: null
      """

  Scenario: JSON Pointer backward compatibility with legacy schemas
    Given I have a schema file "legacy.yaml" with content:
      """yaml
      definitions:
        User:
          properties:
            name:
              type: string
      """
    When I run the generate command: `teds generate legacy.yaml#/definitions`
    Then a test file "legacy.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        legacy.yaml#/definitions/User:
          valid: null
          invalid: null
      """

  Scenario: Merge with existing test specifications
    Given I have a schema file "user.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
      """
    And I have an existing test file "user.tests.yaml" with content:
      """yaml
      version: "1.0.0"
      tests:
        user.yaml#/$defs/User:
          valid:
            existing_test:
              payload: {name: "John"}
          invalid: null
      """
    When I run the generate command: `teds generate user.yaml#/$defs`
    Then the test file "user.tests.yaml" should be updated with content:
      """yaml
      version: "1.0.0"
      tests:
        user.yaml#/$defs/User:
          valid:
            existing_test:
              payload: {name: "John"}
          invalid: null
      """

  Scenario: Handle empty schema gracefully
    Given I have a schema file "empty.yaml" with content:
      """yaml
      {}
      """
    When I run the generate command: `teds generate empty.yaml#/`
    Then a test file "empty.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests: {}
      """
