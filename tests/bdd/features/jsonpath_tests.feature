Feature: JSONPath YAML Configuration Tests
  As a developer using TeDS with JSONPath expressions
  I want to generate tests using YAML configuration with precise JSONPath selectors
  So that I can create tests for exactly the schema elements I need

  Background:
    Given I have a working directory

  Scenario: JSONPath should select the exact node, not its children
    Given I have a schema file "schema.yaml" with content:
      """yaml
      $defs:
        User:
          properties:
            name:
              type: string
            email:
              type: string
      """
    And I have a configuration file "config.yaml" with content:
      """yaml
      schema.yaml:
        paths: ["$.$defs.User.properties"]
      """
    When I run the generate command: `teds generate @config.yaml`
    Then a test file "schema.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        schema.yaml#/$defs/User/properties:
          valid: null
          invalid: null
      """
    And the result should not contain "schema.yaml#/$defs/User/properties/name"
    And the result should not contain "schema.yaml#/$defs/User/properties/email"

  Scenario: JSONPath with wildcards should expand only at the wildcard level
    Given I have a schema file "api.yaml" with content:
      """yaml
      $defs:
        User:
          properties:
            name:
              type: string
            email:
              type: string
        Product:
          properties:
            title:
              type: string
            price:
              type: number
      """
    And I have a configuration file "wildcard_config.yaml" with content:
      """yaml
      api.yaml:
        paths: ["$.$defs.*"]
      """
    When I run the generate command: `teds generate @wildcard_config.yaml`
    Then a test file "api.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        api.yaml#/$defs/User:
          valid: null
          invalid: null
        api.yaml#/$defs/Product:
          valid: null
          invalid: null
      """
    And the result should not contain property-level references

  Scenario: Generate tests for exact JSONPath reference (not children)
    Given I have a schema file "user.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
          properties:
            name:
              type: string
            email:
              type: string
      """
    And I have a configuration file "user_config.yaml" with content:
      """yaml
      user.yaml:
        paths: ["$.$defs.User"]
      """
    When I run the generate command: `teds generate @user_config.yaml`
    Then a test file "user.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        user.yaml#/$defs/User:
          valid: null
          invalid: null
      """
    And the test should target exactly the User definition, not its properties

  Scenario: Nested JSONPath expressions should select precise paths
    Given I have a schema file "complex.yaml" with content:
      """yaml
      $defs:
        User:
          allOf:
            - properties:
                name:
                  type: string
            - properties:
                email:
                  type: string
      """
    And I have a configuration file "complex_config.yaml" with content:
      """yaml
      complex.yaml:
        paths: ["$.$defs.User.allOf[0]"]
      """
    When I run the generate command: `teds generate @complex_config.yaml`
    Then a test file "complex.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        complex.yaml#/$defs/User/allOf/0:
          valid: null
          invalid: null
      """
    And the result should not contain "complex.yaml#/$defs/User/allOf/0/properties"

  Scenario: Root level JSONPath should select root without expansion
    Given I have a schema file "simple.yaml" with content:
      """yaml
      type: object
      properties:
        id:
          type: string
        name:
          type: string
      """
    And I have a configuration file "root_config.yaml" with content:
      """yaml
      simple.yaml:
        paths: ["$"]
      """
    When I run the generate command: `teds generate @root_config.yaml`
    Then a test file "simple.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        simple.yaml#/:
          valid: null
          invalid: null
      """
    And the result should not contain "simple.yaml#/properties"
    And the result should not contain "simple.yaml#/type"

  Scenario: Array index selection should be exact
    Given I have a schema file "array.yaml" with content:
      """yaml
      items:
        - type: string
        - type: number
        - type: boolean
      """
    And I have a configuration file "array_config.yaml" with content:
      """yaml
      array.yaml:
        paths: ["$.items[1]"]
      """
    When I run the generate command: `teds generate @array_config.yaml`
    Then a test file "array.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        array.yaml#/items/1:
          valid: null
          invalid: null
      """

  Scenario: Multiple specific paths should not create children
    Given I have a schema file "multi.yaml" with content:
      """yaml
      $defs:
        Base:
          type: string
        Extended:
          allOf:
            - $ref: "#/$defs/Base"
            - properties:
                extra:
                  type: number
      """
    And I have a configuration file "multi_config.yaml" with content:
      """yaml
      multi.yaml:
        paths: ["$.$defs.Base", "$.$defs.Extended.allOf[1]"]
      """
    When I run the generate command: `teds generate @multi_config.yaml`
    Then a test file "multi.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        multi.yaml#/$defs/Base:
          valid: null
          invalid: null
        multi.yaml#/$defs/Extended/allOf/1:
          valid: null
          invalid: null
      """
    And no child nodes should be automatically included

  Scenario: Complex nested wildcard should expand only at wildcard level
    Given I have a schema file "nested.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            properties:
              profile:
                properties:
                  name:
                    type: string
                  age:
                    type: number
          Product:
            properties:
              details:
                properties:
                  title:
                    type: string
                  price:
                    type: number
      """
    And I have a configuration file "nested_config.yaml" with content:
      """yaml
      nested.yaml:
        paths: ["$.components.schemas.*.properties"]
      """
    When I run the generate command: `teds generate @nested_config.yaml`
    Then a test file "nested.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        nested.yaml#/components/schemas/User/properties:
          valid: null
          invalid: null
        nested.yaml#/components/schemas/Product/properties:
          valid: null
          invalid: null
      """
    And the result should not contain deeper nested properties

  Scenario: Generate tests from YAML configuration file
    Given I have a schema file "user.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
      """
    And I have a configuration file "generate.yaml" with content:
      """yaml
      user.yaml:
        paths: ["$.$defs.User"]
        target: "user_tests.yaml"
      """
    When I run the generate command: `teds generate @generate.yaml`
    Then a test file "user_tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        user.yaml#/$defs/User:
          valid: null
          invalid: null
      """

  Scenario: Generate tests with template variable substitution
    Given I have a schema file "user_model.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
      """
    And I have a configuration file "config.yaml" with content:
      """yaml
      user_model.yaml:
        paths: ["$.$defs.User"]
        target: "{base}_spec.yaml"
      """
    When I run the generate command: `teds generate @config.yaml`
    Then a test file "user_model_spec.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        user_model.yaml#/$defs/User:
          valid: null
          invalid: null
      """

  Scenario: Generate tests with conflict detection in configuration
    Given I have a schema file "schema.yaml" with content:
      """yaml
      $defs:
        Item:
          type: string
      """
    And I have a configuration file "conflict.yaml" with content:
      """yaml
      schema.yaml:
        paths: ["$.$defs.Item", "$.$defs.Item"]
      """
    When I run the generate command: `teds generate @conflict.yaml`
    Then a test file "schema.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        schema.yaml#/$defs/Item:
          valid: null
          invalid: null
      """

  Scenario: Generate tests with default target naming in subdirectories
    Given I have a subdirectory "schemas"
    And I have a schema file "schemas/product.yaml" with content:
      """yaml
      $defs:
        Product:
          type: object
      """
    And I have a configuration file "config.yaml" with content:
      """yaml
      schemas/product.yaml:
        paths: ["$.$defs.Product"]
      """
    When I run the generate command: `teds generate @config.yaml`
    Then a test file "schemas/product.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        product.yaml#/$defs/Product:
          valid: null
          invalid: null
      """
