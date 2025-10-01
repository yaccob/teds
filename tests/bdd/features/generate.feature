Feature: Generate Command Tests
  As a developer using TeDS generate command
  I want to create test specifications from JSON schemas
  So that I can quickly bootstrap test suites for my schemas

  Background:
    Given I have a working directory

  # ==========================================================================
  # Chapter 2: JSON Pointer Generation Examples
  # ==========================================================================

  Scenario: Generate tests from schema container using JSON Pointer
    Given I have a schema file "sample_schemas.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            type: object
            properties:
              name:
                type: string
            examples:
              - name: "Alice"
          Email:
            type: string
            format: email
            examples:
              - "alice@example.com"
      """
    When I run the generate command: `teds generate sample_schemas.yaml#/components/schemas`
    Then a test file "sample_schemas.tests.yaml" should be created
    And the test file should contain "sample_schemas.yaml#/components/schemas/User"
    And the test file should contain "sample_schemas.yaml#/components/schemas/Email"
    And the test file should contain examples marked with "from_examples: true"

  Scenario: Generate tests for specific schema properties using JSON Pointer
    Given I have a schema file "api_spec.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            type: object
            properties:
              name:
                type: string
                examples:
                  - "Alice"
              email:
                type: string
                format: email
                examples:
                  - "alice@example.com"
      """
    When I run the generate command: `teds generate api_spec.yaml#/components/schemas/User/properties`
    Then a test file "api_spec.tests.yaml" should be created
    And the test file should contain "api_spec.yaml#/components/schemas/User/properties/name"
    And the test file should contain "api_spec.yaml#/components/schemas/User/properties/email"

  Scenario: Generate tests for single specific schema using JSON Pointer
    Given I have a schema file "single_schema.yaml" with content:
      """yaml
      components:
        schemas:
          Email:
            type: string
            format: email
            examples:
              - "alice@example.com"
              - "bob@example.org"
      """
    When I run the generate command: `teds generate single_schema.yaml#/components/schemas`
    Then a test file "single_schema.tests.yaml" should be created
    And the test file should contain "single_schema.yaml#/components/schemas/Email"
    And the test file should contain "alice@example.com"
    And the test file should contain "bob@example.org"

  # ==========================================================================
  # Chapter 2: JSON Path Configuration Examples
  # ==========================================================================

  Scenario: Generate using JSON Path with configuration file (@file syntax)
    Given I have a schema file "sample_schemas.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            type: object
            examples:
              - name: "Alice"
          Product:
            type: object
            examples:
              - sku: "ABC123"
      """
    And I have a configuration file "config.yaml" with content:
      """yaml
      sample_schemas.yaml:
        paths: ["$.components.schemas.*"]
      """
    When I run the generate command: `teds generate @config.yaml`
    Then a test file "sample_schemas.tests.yaml" should be created
    And the test file should contain "sample_schemas.yaml#/components/schemas/User"
    And the test file should contain "sample_schemas.yaml#/components/schemas/Product"

  Scenario: Generate using direct JSON Path YAML string
    Given I have a schema file "sample_schemas.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            type: object
            examples:
              - name: "Alice"
          Email:
            type: string
            format: email
            examples:
              - "alice@example.com"
      """
    When I run the generate command: `teds generate '{"sample_schemas.yaml": {"paths": ["$.components.schemas.*"]}}'`
    Then a test file "sample_schemas.tests.yaml" should be created
    And the test file should contain "sample_schemas.yaml#/components/schemas/User"
    And the test file should contain "sample_schemas.yaml#/components/schemas/Email"

  Scenario: Generate with specific JSON Path targets
    Given I have a schema file "api.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            type: object
            examples:
              - name: "Alice"
          Product:
            type: object
            examples:
              - sku: "ABC123"
          Tag:
            type: string
            examples:
              - "important"
      """
    When I run the generate command: `teds generate '{"api.yaml": {"paths": ["$.components.schemas.User", "$.components.schemas.Product"]}}'`
    Then a test file "api.tests.yaml" should be created
    And the test file should contain "api.yaml#/components/schemas/User"
    And the test file should contain "api.yaml#/components/schemas/Product"
    And the test file should not contain "api.yaml#/components/schemas/Tag"

  Scenario: Generate with JSON Path and custom target file
    Given I have a schema file "schema.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
          examples:
            - name: "Alice"
        Product:
          type: object
          examples:
            - sku: "ABC123"
      """
    When I run the generate command: `teds generate '{"schema.yaml": {"paths": ["$[\"$defs\"].*"], "target": "custom_tests.yaml"}}'`
    Then a test file "custom_tests.yaml" should be created
    And the test file should contain "schema.yaml#/$defs/User"
    And the test file should contain "schema.yaml#/$defs/Product"

  Scenario: Generate using simple JSON Path list format
    Given I have a schema file "schema.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            type: object
            examples:
              - name: "Alice"
      $defs:
        Product:
          type: object
          examples:
            - sku: "ABC123"
      """
    When I run the generate command: `teds generate '{"schema.yaml": ["$.components.schemas.*", "$[\"$defs\"].*"]}'`
    Then a test file "schema.tests.yaml" should be created
    And the test file should contain "schema.yaml#/components/schemas/User"
    And the test file should contain "schema.yaml#/$defs/Product"

  # ==========================================================================
  # Template Variables (JSON Pointer only)
  # ==========================================================================

  Scenario: Template variables with JSON Pointer from tutorial
    Given I have a schema file "schema.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            type: object
            examples:
              - name: "Alice"
      """
    When I run the generate command: `teds generate schema.yaml#/components/schemas={base}.{pointer}.custom.yaml`
    Then a test file "schema.components~1schemas.custom.yaml" should be created
    And the test file should contain "schema.yaml#/components/schemas/User"

  # ==========================================================================
  # Pointer Sanitization Examples
  # ==========================================================================

  Scenario: JSON Pointer sanitization with plus signs
    Given I have a schema file "api.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            type: object
            examples:
              - name: "Alice"
      """
    When I run the generate command: `teds generate api.yaml#/components/schemas/User`
    Then a test file "api.tests.yaml" should be created

  Scenario: $defs pointer sanitization
    Given I have a schema file "schema.yaml" with content:
      """yaml
      $defs:
        Address:
          type: object
          examples:
            - street: "Main St"
      """
    When I run the generate command: `teds generate schema.yaml#/$defs/Address`
    Then a test file "schema.tests.yaml" should be created

  # ==========================================================================
  # From cli_essentials.feature - CLI Generation Tests
  # ==========================================================================

  Scenario: JSON Pointer with wildcard generates correct children
    Given I have a schema file "api.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            type: object
            properties:
              name:
                type: string
          Product:
            type: object
            properties:
              title:
                type: string
      """
    When I run the CLI command: `./teds.py generate api.yaml#/components/schemas`
    Then a test file "api.tests.yaml" should be created
    And the test file should contain exactly these test keys:
      """
      - "api.yaml#/components/schemas/User"
      - "api.yaml#/components/schemas/Product"
      """
    And the test file should NOT contain:
      """
      - "api.yaml#/components/schemas/User/type"
      - "api.yaml#/components/schemas/User/properties"
      - "api.yaml#/components/schemas/Product/type"
      - "api.yaml#/components/schemas/Product/properties"
      """

  Scenario: JSONPath YAML config generates exact nodes
    Given I have a schema file "schema.yaml" with content:
      """yaml
      $defs:
        AddressOneLine:
          type: object
          properties:
            street:
              type: string
        AddressTwoLines:
          type: object
          properties:
            street1:
              type: string
            street2:
              type: string
        AddressList:
          type: array
          items:
            oneOf:
              - $ref: "#/$defs/AddressOneLine"
              - $ref: "#/$defs/AddressTwoLines"
      """
    When I run the CLI command: `./teds.py generate '{"schema.yaml": ["$.[\"$defs\"].*"]}'`
    Then a test file "schema.tests.yaml" should be created
    And the test file should contain exactly these test keys:
      """
      - "schema.yaml#/$defs/AddressOneLine"
      - "schema.yaml#/$defs/AddressTwoLines"
      - "schema.yaml#/$defs/AddressList"
      """
    And the test file should NOT contain:
      """
      - "schema.yaml#/$defs/AddressOneLine/type"
      - "schema.yaml#/$defs/AddressOneLine/properties"
      - "schema.yaml#/$defs/AddressTwoLines/type"
      - "schema.yaml#/$defs/AddressTwoLines/properties"
      - "schema.yaml#/$defs/AddressList/type"
      - "schema.yaml#/$defs/AddressList/items"
      """

  Scenario: JSON Pointer exact reference generates only that reference
    Given I have a schema file "simple.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
          properties:
            name:
              type: string
      """
    When I run the CLI command: `./teds.py generate simple.yaml#/$defs/User`
    Then a test file "simple.tests.yaml" should be created
    And the test file should contain exactly these test keys:
      """
      - "simple.yaml#/$defs/User/type"
      - "simple.yaml#/$defs/User/properties"
      """
    And the test file should NOT contain:
      """
      - "simple.yaml#/$defs/User/properties/name"
      """

  Scenario: Root pointer generates top-level elements
    Given I have a schema file "root.yaml" with content:
      """yaml
      type: object
      properties:
        id:
          type: string
        name:
          type: string
      """
    When I run the CLI command: `./teds.py generate root.yaml#/`
    Then a test file "root.tests.yaml" should be created
    And the test file should contain exactly these test keys:
      """
      - "root.yaml#/type"
      - "root.yaml#/properties"
      """
    And the test file should NOT contain:
      """
      - "root.yaml#/properties/id"
      - "root.yaml#/properties/name"
      """

  Scenario: Relative path with JSON Pointer
    Given I have a subdirectory "models"
    And I have a schema file "models/user.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
      """
    When I run the CLI command: `./teds.py generate models/user.yaml#/$defs`
    Then a test file "models/user.tests.yaml" should be created
    And the test file should contain exactly these test keys:
      """
      - "user.yaml#/$defs/User"
      """

  Scenario: Error handling for missing schema file
    When I run the CLI command: `./teds.py generate missing.yaml#/components/schemas`
    Then the command should fail with exit code 2
    And the error output should match "Failed to load schema.*missing\.yaml.*No such file or directory.*"

  Scenario: Default pointer behavior (no fragment)
    Given I have a schema file "default.yaml" with content:
      """yaml
      type: object
      properties:
        id:
          type: string
      """
    When I run the CLI command: `./teds.py generate default.yaml`
    Then a test file "default.tests.yaml" should be created
    And the test file should contain exactly these test keys:
      """
      - "default.yaml#/type"
      - "default.yaml#/properties"
      """

  # ==========================================================================
  # From json_pointer_tests.feature - JSON Pointer Generation Tests
  # ==========================================================================

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
            .["$defs"].Product.examples[0]:
              payload:
                title: Laptop
                price: 999.99
              from_examples: true
            .["$defs"].Product.examples[1]:
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
    When I run the generate command: `teds generate schema.yaml#/$defs/Item=custom.tests.yaml`
    Then a test file "custom.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        schema.yaml#/$defs/Item/type:
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

  # ==========================================================================
  # From jsonpath_tests.feature - JSONPath YAML Configuration Tests
  # ==========================================================================

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
        paths: ["$.['$defs'].User.properties"]
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
        paths: ["$.['$defs'].*"]
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

  Scenario: Escaping of path elements with special characters works in output
    Given I have a schema file "api.yaml" with content:
      """yaml
      "/Slashes/to/escape":
        "~Tildes~to~escape":
          properties:
            name:
              type: string
            email:
              type: string
        "Dots.not.to.escape":
          properties:
            title:
              type: string
            price:
              type: number
      """
    And I have a configuration file "escape_config.yaml" with content:
      """yaml
      api.yaml:
        paths: ["$.['/Slashes/to/escape']", "$.['/Slashes/to/escape'].*"]
      """
    When I run the generate command: `teds generate @escape_config.yaml`
    Then a test file "api.tests.yaml" should be created with content:
      """yaml
      version: "1.0.0"
      tests:
        api.yaml#/~1Slashes~1to~1escape:
          valid: null
          invalid: null
        api.yaml#/~1Slashes~1to~1escape/~0Tildes~0to~0escape:
          valid: null
          invalid: null
        api.yaml#/~1Slashes~1to~1escape/Dots.not.to.escape:
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
        paths: ["$.['$defs'].User"]
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
        paths: ["$.['$defs'].User.allOf[0]"]
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
        simple.yaml#:
          valid: null
          invalid: null
      """
    And the result should not contain "simple.yaml#/properties"

  # ==========================================================================
  # Template Variable Tests
  # ==========================================================================

  Scenario: Template variable {base} should work
    Given I have a schema file "template.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            type: object
            properties:
              name:
                type: string
      """
    When I run the generate command: `teds generate template.yaml#/components/schemas={base}.test.yaml`
    Then a test file "template.test.yaml" should be created

  Scenario: Template variable {file} should work
    Given I have a schema file "template.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            type: object
      """
    When I run the generate command: `teds generate template.yaml#/components/schemas={file}.test.yaml`
    Then a test file "template.yaml.test.yaml" should be created

  Scenario: Template variable {ext} should work
    Given I have a schema file "template.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            type: object
      """
    When I run the generate command: `teds generate template.yaml#/components/schemas=test.{ext}.tests.yaml`
    Then a test file "test.yaml.tests.yaml" should be created

  Scenario: Template variable {pointer} should work
    Given I have a schema file "template.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            type: object
      """
    When I run the generate command: `teds generate template.yaml#/components/schemas={pointer}.test.yaml`
    Then a test file "components~1schemas.test.yaml" should be created

  Scenario: Template variable combination {base}.{pointer} should work
    Given I have a schema file "template.yaml" with content:
      """yaml
      components:
        schemas:
          User:
            type: object
      """
    When I run the generate command: `teds generate template.yaml#/components/schemas={base}.{pointer}.custom.yaml`
    Then a test file "template.components~1schemas.custom.yaml" should be created

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
        paths: ["$.['$defs'].Base", "$.['$defs'].Extended.allOf[1]"]
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
        paths: ["$.['$defs'].User"]
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
        paths: ["$.['$defs'].User"]
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
        paths: ["$.['$defs'].Item", "$.['$defs'].Item"]
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
        paths: ["$.['$defs'].Product"]
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

  # ==========================================================================
  # YAML Config Template Variable Tests
  # ==========================================================================

  Scenario: YAML Config template variable {file} should work
    Given I have a schema file "template.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
      """
    And I have a configuration file "config.yaml" with content:
      """yaml
      template.yaml:
        paths: ["$.['$defs'].User"]
        target: "{file}_tests.yaml"
      """
    When I run the generate command: `teds generate @config.yaml`
    Then a test file "template.yaml_tests.yaml" should be created

  Scenario: YAML Config template variable {ext} should work
    Given I have a schema file "template.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
      """
    And I have a configuration file "config.yaml" with content:
      """yaml
      template.yaml:
        paths: ["$.['$defs'].User"]
        target: "test_{ext}_spec.yaml"
      """
    When I run the generate command: `teds generate @config.yaml`
    Then a test file "test_yaml_spec.yaml" should be created

  Scenario: YAML Config template variable {dir} should work
    Given I have a subdirectory "models"
    And I have a schema file "models/template.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
      """
    And I have a configuration file "config.yaml" with content:
      """yaml
      models/template.yaml:
        paths: ["$.['$defs'].User"]
        target: "{dir}_tests.yaml"
      """
    When I run the generate command: `teds generate @config.yaml`
    Then a test file "models_tests.yaml" should be created

  Scenario: YAML Config template variable {base} should continue working
    Given I have a schema file "template.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
      """
    And I have a configuration file "config.yaml" with content:
      """yaml
      template.yaml:
        paths: ["$.['$defs'].User"]
        target: "{base}_tests.yaml"
      """
    When I run the generate command: `teds generate @config.yaml`
    Then a test file "template_tests.yaml" should be created

  Scenario: YAML Config template variable combination should work
    Given I have a schema file "template.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
      """
    And I have a configuration file "config.yaml" with content:
      """yaml
      template.yaml:
        paths: ["$.['$defs'].User"]
        target: "{base}_{ext}_tests.yaml"
      """
    When I run the generate command: `teds generate @config.yaml`
    Then a test file "template_yaml_tests.yaml" should be created

  # ==========================================================================
  # Path Resolution Tests
  # ==========================================================================

  Scenario: YAML Config should handle schema file and test file in cwd correctly
    Given I have a schema file "api.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
          properties:
            name:
              type: string
      """
    And I have a configuration file "config.yaml" with content:
      """yaml
      api.yaml:
        paths: ["$.['$defs'].User"]
        target: "api_tests.yaml"
      """
    When I run the generate command: `teds generate @config.yaml`
    Then a test file "api_tests.yaml" should be created
    And the test file should contain "api.yaml#/$defs/User"

  Scenario: YAML Config should handle schema file and test file in subdirectory correctly
    Given I have a subdirectory "schemas"
    And I have a schema file "schemas/api.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
          properties:
            name:
              type: string
      """
    And I have a configuration file "config.yaml" with content:
      """yaml
      schemas/api.yaml:
        paths: ["$.['$defs'].User"]
        target: "schemas/api_tests.yaml"
      """
    When I run the generate command: `teds generate @config.yaml`
    Then a test file "schemas/api_tests.yaml" should be created
    And the test file should contain "api.yaml#/$defs/User"

  Scenario: YAML Config should handle schema file in subdirectory and test file in cwd correctly
    Given I have a subdirectory "schemas"
    And I have a schema file "schemas/api.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
          properties:
            name:
              type: string
      """
    And I have a configuration file "config.yaml" with content:
      """yaml
      schemas/api.yaml:
        paths: ["$.['$defs'].User"]
        target: "api_tests.yaml"
      """
    When I run the generate command: `teds generate @config.yaml`
    Then a test file "api_tests.yaml" should be created
    And the test file should contain "schemas/api.yaml#/$defs/User"

  Scenario: YAML Config should handle schema file in cwd and test file in subdirectory correctly
    Given I have a subdirectory "tests"
    And I have a schema file "api.yaml" with content:
      """yaml
      $defs:
        User:
          type: object
          properties:
            name:
              type: string
      """
    And I have a configuration file "config.yaml" with content:
      """yaml
      api.yaml:
        paths: ["$.['$defs'].User"]
        target: "tests/api_tests.yaml"
      """
    When I run the generate command: `teds generate @config.yaml`
    Then a test file "tests/api_tests.yaml" should be created
    And the test file should contain "../api.yaml#/$defs/User"

  Scenario: YAML Config path resolution should work with template variables
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
    And I have a configuration file "config.yaml" with content:
      """yaml
      models/user.yaml:
        paths: ["$.['$defs'].User"]
        target: "{dir}_{base}_tests.yaml"
      """
    When I run the generate command: `teds generate @config.yaml`
    Then a test file "models_user_tests.yaml" should be created
    And the test file should contain "models/user.yaml#/$defs/User"

  # ==========================================================================
  # Status Message Tests
  # ==========================================================================

  Scenario: Generate command outputs status message to stderr
    Given I have a subdirectory "models"
    Given I have a schema file "models/simple.yaml" with content:
      """yaml
      type: string
      examples:
        - "test"
      """
    When I run the generate command: `teds generate models/simple.yaml#`
    Then the command should succeed
    And the error output should match "^Generating models/simple.tests.yaml\n$"

  # ==========================================================================
  # Template Path Resolution Relative to CWD Tests
  # ==========================================================================

  Scenario: Template path should resolve relative to current working directory, not schema directory
    Given I have a subdirectory "agriculture"
    And I have a schema file "agriculture/agriculture.yaml" with content:
      """yaml
      $defs:
        Crop:
          type: object
          properties:
            name:
              type: string
            season:
              type: string
      """
    And I have a subdirectory "teds"
    When I run the generate command from cwd: `teds generate agriculture/agriculture.yaml#/$defs=teds/{base}.yaml`
    Then a test file "teds/agriculture.yaml" should be created in cwd
    And the test file should contain "agriculture/agriculture.yaml#/$defs/Crop"

  Scenario: Template path with nested directories should resolve relative to cwd
    Given I have a subdirectory "models/user"
    And I have a schema file "models/user/profile.yaml" with content:
      """yaml
      $defs:
        UserProfile:
          type: object
          properties:
            name:
              type: string
      """
    And I have a subdirectory "tests/specs"
    When I run the generate command from cwd: `teds generate models/user/profile.yaml#/$defs=tests/specs/{base}_spec.yaml`
    Then a test file "tests/specs/profile_spec.yaml" should be created in cwd
    And the test file should contain "models/user/profile.yaml#/$defs/UserProfile"

  Scenario: Template path without subdirectory should work in cwd
    Given I have a schema file "simple.yaml" with content:
      """yaml
      $defs:
        SimpleType:
          type: string
      """
    When I run the generate command from cwd: `teds generate simple.yaml#/$defs={base}_output.yaml`
    Then a test file "simple_output.yaml" should be created in cwd
    And the test file should contain "simple.yaml#/$defs/SimpleType"

  Scenario: Template path with absolute target path should work
    Given I have a subdirectory "source"
    And I have a schema file "source/data.yaml" with content:
      """yaml
      $defs:
        DataModel:
          type: object
      """
    And I have a subdirectory "output"
    When I run the generate command from cwd: `teds generate source/data.yaml#/$defs=output/{base}.test.yaml`
    Then a test file "output/data.test.yaml" should be created in cwd
    And the test file should contain "source/data.yaml#/$defs/DataModel"
