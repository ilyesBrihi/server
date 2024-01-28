from rest_framework.exceptions import ValidationError
from rest_framework.serializers import as_serializer_error


class NestedListExceptionHandler:
    def __init__(self, field_name, serializer_instance):
        self.field_name = field_name
        self.serializer_instance = serializer_instance

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, ValidationError):
            error = exc_val if exc_val else ValidationError()
            if self.field_name not in self.serializer_instance._errors:
                self.serializer_instance._errors.update(
                    {self.field_name: [as_serializer_error(error)]}
                )
            else:
                self.serializer_instance._errors[self.field_name].append(as_serializer_error(error))
        elif exc_val:
            raise exc_val
        return True


class NestedInstanceExceptionHandler:
    def __init__(self, field_name, serializer_instance):
        self.field_name = field_name
        self.serializer_instance = serializer_instance

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            if issubclass(exc_type, ValidationError):
                error = exc_val if exc_val else ValidationError()
                self.serializer_instance._errors.update(
                    {self.field_name: as_serializer_error(error)}
                )
            elif exc_val:
                raise exc_val
        return True
