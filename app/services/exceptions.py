class AppError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class IngestionError(AppError):
    pass


class UnsupportedFileTypeError(IngestionError):
    def __init__(self, filename: str) -> None:
        super().__init__(
            f"Unsupported file type for '{filename}'. Use PDF, Markdown, or plain text.",
            status_code=415,
        )


class EmptyDocumentError(IngestionError):
    def __init__(self) -> None:
        super().__init__("The document contains no extractable text.", status_code=400)


class ExtractionError(IngestionError):
    def __init__(self, message: str = "Failed to extract text from the document.") -> None:
        super().__init__(message, status_code=422)


class PersistenceError(IngestionError):
    def __init__(self) -> None:
        super().__init__("Failed to store the document in the database.", status_code=500)


class EmbeddingError(AppError):
    def __init__(self, message: str = "Failed to generate embeddings.") -> None:
        super().__init__(message, status_code=503)


class LlmError(AppError):
    def __init__(self, message: str = "The language model is unavailable.") -> None:
        super().__init__(message, status_code=503)


class ConversationNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__("Conversation was not found.", status_code=404)
