import warnings


def _suppress_upstream_warnings() -> None:
    """Supprime les avertissements amont inoffensifs avant l'import des modules de test.

    - anyio.abc.BlockingPortal alias (starlette.testclient via anyio >=4.9)
    - LangChainPendingDeprecationWarning (langgraph via langchain-core)
    """
    warnings.filterwarnings(
        "ignore",
        message=r".*anyio\.abc\.BlockingPortal.*",
    )
    warnings.filterwarnings(
        "ignore",
        message=r".*allowed_objects.*",
    )


_suppress_upstream_warnings()


def pytest_configure(config):
    """Register the 'network' marker to avoid unknown-marker warnings."""
    config.addinivalue_line(
        "markers",
        'network: test requires network access (run offline with `-m "not network"`)',
    )
