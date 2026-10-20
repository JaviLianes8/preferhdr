"""The error raised for invalid input and for values no header field can carry."""

from __future__ import annotations


class PreferError(ValueError):
    """A header value breaks the grammar, or a value cannot be written safely.

    ``position`` is the character offset inside the field value and ``field`` the index
    of that value among the ones passed to ``parse``; either is ``None`` when it does not
    apply (for example when building). ``str(error)`` is the message followed by where it
    was found. It is a ``ValueError``, so existing ``except ValueError`` code catches it,
    and it survives pickling. Messages quote at most 40 characters of the input.

    >>> from preferhdr import parse
    >>> try:
    ...     parse(["a", "b, =1"], strict=True)
    ... except PreferError as error:
    ...     print(error.message, error.position, error.field)
    ...     print(error)
    expected a token 3 1
    expected a token at position 3 of field 1
    """

    def __init__(self, message: str, position: int | None = None, field: int | None = None):
        self.message = message
        self.position = position
        self.field = field
        where = ""
        if position is not None:
            where = f" at position {position}"
            if field is not None:
                where += f" of field {field}"
        super().__init__(message + where)

    def __reduce__(self) -> tuple[type[PreferError], tuple[str, int | None, int | None]]:
        return (type(self), (self.message, self.position, self.field))
