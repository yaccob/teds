Feature: Template Integer Payload Handling
  As a developer using TeDS reports
  I want templates to handle integer payloads correctly
  So that report generation doesn't fail with type errors

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
