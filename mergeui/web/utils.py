import typing as t
import pydantic as pd
import fastapi as fa

BaseValidationError = t.Union[pd.ValidationError, ValueError, AssertionError]


def pretty_error(error: t.Union[Exception, str]) -> str:
    if isinstance(error, pd.ValidationError):
        errs = error.errors()
        if errs:
            first_err = errs[0]
            loc = ','.join(first_err.get('loc', []))
            if first_err.get('type') in ['missing', 'string_too_short']:
                return f"{loc}: Field required"
            return f"{loc}: {first_err.get('msg')}"
        return str(error)
    return str(error)


def api_error(error: t.Union[Exception, str]) -> fa.exceptions.RequestValidationError:
    if isinstance(error, pd.ValidationError):
        return fa.exceptions.RequestValidationError(error.errors())
    return fa.exceptions.RequestValidationError(pretty_error(error))
