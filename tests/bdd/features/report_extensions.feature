Feature: Report File Extensions
  As a developer using TeDS report generation
  I want the generated report files to have appropriate extensions based on template type
  So that the files are properly recognized by editors and tools

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

  Scenario: AsciiDoc template generates .adoc extension by default
    When I run the command "verify test.yaml --report comprehensive.adoc"
    Then the command should succeed
    And a file "test.report.adoc" should be created
    And the file "test.report.adoc" should contain AsciiDoc content

  Scenario: HTML template generates .html extension by default
    When I run the command "verify test.yaml --report summary.html"
    Then the command should succeed
    And a file "test.report.html" should be created
    And the file "test.report.html" should contain HTML content

  Scenario: Markdown template generates .md extension by default
    When I run the command "verify test.yaml --report summary.md"
    Then the command should succeed
    And a file "test.report.md" should be created
    And the file "test.report.md" should contain Markdown content
