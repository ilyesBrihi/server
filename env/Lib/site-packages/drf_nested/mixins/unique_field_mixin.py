from typing import List

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.validators import UniqueValidator

from drf_nested.utils import nested_unique_validate


class UniqueFieldMixin(serializers.ModelSerializer):
    """
    Extracts unique validators for every field.
    The validators are being run on `create`/`update` instead of `is_valid`
    """

    def __init__(self, instance=None, data=empty, **kwargs):
        self.Meta.unique_validators = []
        super().__init__(instance, data, **kwargs)

    def add_validator(self, field_name):
        if self.Meta.unique_validators is None:
            self.Meta.unique_validators = []
        self.Meta.unique_validators.append(field_name)

    @property
    def unique_validators(self):
        return self.Meta.unique_validators if self.Meta.unique_validators is not None else []

    def _is_unique_validator(self, validator):
        return isinstance(validator, UniqueValidator)

    def _has_unique_validator(self, field_serializer):
        for validator in field_serializer.validators:
            if self._is_unique_validator(validator):
                return True
        return None

    def get_fields(self):
        fields = super().get_fields()
        for field_name, field_serializer in fields.items():
            if self._has_unique_validator(field_serializer):
                self.add_validator(field_name)
            field_serializer.validators = [
                validator
                for validator in field_serializer.validators
                if not self._is_unique_validator(validator)
            ]
        return fields

    @nested_unique_validate
    def _validate_unique(self, validated_data):
        for field in self.unique_validators:
            unique_validator = UniqueValidator(self.Meta.model.objects.all())
            if field not in validated_data:
                continue
            call_args = [validated_data[field]]
            if hasattr(unique_validator, "set_context"):
                unique_validator.set_context(self.fields[field])
            else:
                call_args.append(self.fields[field])

            try:
                unique_validator(*call_args)
            except ValidationError as exc:
                raise ValidationError({field: exc.detail})

    def create(self, validated_data):
        self._validate_unique(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._validate_unique(validated_data)
        return super().update(instance, validated_data)

    class Meta:
        model = None
        unique_validators: List[str] = None
