from pydantic import ValidationError


def _format_validation_error(error: ValidationError) -> str:
    buffer_messages = []
    for error_value in error.errors():
        loc = error_value["loc"]
        msg = error_value["msg"]

        if loc:
            location = ".".join(str(el) for el in loc)
            message = f"{location}: {msg}"
        else:
            message = msg

        buffer_messages.append(message)

    return "\n".join(buffer_messages)
