"""Automated architecture-boundary tests (standard pytest suite).

These encode the frozen layering rules so violations fail CI, not review.
"""

import ast
import inspect
from pathlib import Path

import app.application.ports as ports_module
import app.infrastructure.repositories as repo_pkg
from app.application.ports import (
    IAIRecommendationRepository,
    IAuditLogRepository,
    IConversationMessageRepository,
    ISafetyFlagRepository,
    IServiceRequestRepository,
    IStaffDecisionRepository,
    IStaffUserRepository,
    ITriageAnswerRepository,
    IUserSessionRepository,
)
from app.infrastructure.repositories import (
    SQLAlchemyAIRecommendationRepository,
    SQLAlchemyAuditLogRepository,
    SQLAlchemyConversationMessageRepository,
    SQLAlchemySafetyFlagRepository,
    SQLAlchemyServiceRequestRepository,
    SQLAlchemyStaffDecisionRepository,
    SQLAlchemyStaffUserRepository,
    SQLAlchemyTriageAnswerRepository,
    SQLAlchemyUserSessionRepository,
)

PORT_TO_ADAPTER = {
    IUserSessionRepository: SQLAlchemyUserSessionRepository,
    IServiceRequestRepository: SQLAlchemyServiceRequestRepository,
    IConversationMessageRepository: SQLAlchemyConversationMessageRepository,
    ITriageAnswerRepository: SQLAlchemyTriageAnswerRepository,
    ISafetyFlagRepository: SQLAlchemySafetyFlagRepository,
    IAIRecommendationRepository: SQLAlchemyAIRecommendationRepository,
    IStaffUserRepository: SQLAlchemyStaffUserRepository,
    IStaffDecisionRepository: SQLAlchemyStaffDecisionRepository,
    IAuditLogRepository: SQLAlchemyAuditLogRepository,
}


def _imports_of(directory: str) -> list[tuple[str, str]]:
    """(file, imported module) pairs for every .py file under directory."""
    found = []
    for path in sorted(Path(directory).rglob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found.append((str(path), alias.name))
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.append((str(path), node.module))
    return found


def test_domain_cannot_import_infrastructure():
    """Domain stays dependency-free of infrastructure, application, and api."""
    violations = [
        (f, m)
        for f, m in _imports_of("app/domain")
        if m.startswith(("app.infrastructure", "app.application", "app.api"))
    ]
    assert violations == []


def test_application_cannot_import_concrete_adapters():
    """The application layer depends on ports, never on infrastructure."""
    violations = [
        (f, m) for f, m in _imports_of("app/application") if m.startswith("app.infrastructure")
    ]
    assert violations == []


def test_repositories_cannot_import_fastapi():
    """Repository adapters are HTTP-free."""
    violations = [
        (f, m)
        for f, m in _imports_of("app/infrastructure/repositories")
        if m == "fastapi" or m.startswith("fastapi.")
    ]
    assert violations == []


def test_repositories_cannot_construct_engines_or_sessions():
    """Adapters receive an AsyncSession; they never build engines/factories."""
    forbidden = {"create_async_engine", "async_sessionmaker", "create_engine", "sessionmaker"}
    violations = []
    for path in sorted(Path("app/infrastructure/repositories").rglob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", getattr(node.func, "attr", ""))
                if name in forbidden:
                    violations.append(f"{path.name}:{node.lineno}: {name}()")
    assert violations == []


def test_ports_do_not_expose_orm_types():
    """Frozen ports import nothing from infrastructure; annotations are
    domain entities only."""
    source = inspect.getsource(ports_module)
    assert "app.infrastructure" not in source
    assert "Mapped" not in source
    assert "Model" not in source


def test_every_adapter_satisfies_its_frozen_port():
    """Each concrete adapter subclasses its port and implements every
    abstract method (not abstract itself)."""
    for port, adapter in PORT_TO_ADAPTER.items():
        assert issubclass(adapter, port), f"{adapter.__name__} does not implement {port.__name__}"
        assert not inspect.isabstract(adapter), f"{adapter.__name__} has unimplemented methods"
        for method_name in getattr(port, "__abstractmethods__", set()):
            impl = getattr(adapter, method_name, None)
            assert impl is not None and not getattr(impl, "__isabstractmethod__", False), (
                f"{adapter.__name__}.{method_name} is not concretely implemented"
            )


def test_adapter_package_exports_all_nine():
    """The repositories package exports exactly the nine adapters."""
    assert len(repo_pkg.__all__) == 9
