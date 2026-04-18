"""Smoke test — ensures pytest discovery works after monorepo migration."""


def test_pipelines_package_imports() -> None:
    import pipelines

    assert pipelines is not None


def test_connectors_subpackage_imports() -> None:
    from pipelines import connectors

    assert connectors is not None
