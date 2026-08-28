"""Domain-level errors.

These carry no notion of HTTP; ``api/routes`` maps each one to a status code
via a FastAPI exception handler.
"""

from __future__ import annotations


class CarouselNotFound(Exception):
    def __init__(self, cid: str) -> None:
        super().__init__(f"Carrossel não encontrado: {cid}")
        self.cid = cid


class GenerationInProgress(Exception):
    def __init__(self, message: str = "Geração já em andamento.") -> None:
        super().__init__(message)


class NoPlanYet(Exception):
    def __init__(self, message: str = "Nenhum plano para esta operação.") -> None:
        super().__init__(message)


class InvalidSlideSelection(Exception):
    def __init__(self, message: str = "Nenhum slide válido selecionado.") -> None:
        super().__init__(message)


class NoSlidesGenerated(Exception):
    def __init__(self, message: str = "Nenhum slide gerado ainda.") -> None:
        super().__init__(message)


class PlanningFailed(Exception):
    """Raised when the text AI provider fails to plan/revise a carousel."""


class UnsupportedMediaType(Exception):
    def __init__(self, message: str = "Tipo de arquivo não suportado.") -> None:
        super().__init__(message)
