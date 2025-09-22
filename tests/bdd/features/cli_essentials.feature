Feature: Essential CLI Functionality Tests
  As a developer using TeDS from the command line
  I want the core CLI commands to work correctly
  So that I can generate test specifications reliably

  Background:
    Given I have a working directory

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
    Then a test file "api.components+schemas.tests.yaml" should be created
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
    Then a test file "simple.$defs+User.tests.yaml" should be created
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
    Then a test file "models/user.$defs.tests.yaml" should be created
    And the test file should contain exactly these test keys:
      """
      - "user.yaml#/$defs/User"
      """

  Scenario: Error handling for missing schema file
    When I run the CLI command: `./teds.py generate missing.yaml#/components/schemas`
    Then the command should fail with exit code 2
    And the error output should contain "Failed to resolve parent schema ref"

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
