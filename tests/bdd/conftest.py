"""Shared pytest configuration for BDD tests."""


def pytest_bdd_step_error(
    request, feature, scenario, step, step_func, step_func_args, exception
):
    """Handle BDD step errors with better debugging information."""
    print(f"\nBDD Step Error in {feature.filename}:")
    print(f"Scenario: {scenario.name}")
    print(f"Step: {step.name}")
    print(f"Exception: {exception}")


def pytest_configure(config):
    """Configure pytest for BDD testing."""
    config.addinivalue_line("markers", "bdd: mark test as a BDD scenario")
