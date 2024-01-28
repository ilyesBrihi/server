from typing import List, Tuple

from django.db.models import QuerySet
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.validators import UniqueTogetherValidator

from drf_nested.mixins.base_nestable_mixin import BaseNestableMixin
from drf_nested.utils import nested_unique_validate


class UniqueTogetherMixin(BaseNestableMixin):
    """
    Extracts unique together validators for every field.
    The validators are being run on `create`/`update` instead of `is_valid`
    """

    def __init__(self, instance=None, data=empty, **kwargs):
        self.Meta.unique_together_validators = []
        for validator in self.validators:
            if self._is_unique_together_validator(validator):
                self.add_validator(validator.fields)
        self.validators = [
            validator
            for validator in self.validators
            if not self._is_unique_together_validator(validator)
        ]
        super().__init__(instance, data, **kwargs)

    def add_validator(self, fields):
        if self.Meta.unique_together_validators is None:
            self.Meta.unique_together_validators = []
        self.Meta.unique_together_validators.append(fields)

    @property
    def unique_together_validators(self):
        return (
            self.Meta.unique_together_validators
            if self.Meta.unique_together_validators is not None
            else []
        )

    def _is_unique_together_validator(self, validator):
        return isinstance(validator, UniqueTogetherValidator)

    @nested_unique_validate
    def _validate_unique_together_instance(self, validated_data):
        for fields in self.unique_together_validators:
            unique_together_validator = UniqueTogetherValidator(
                self.Meta.model.objects.all(), fields
            )
            call_args = [validated_data]
            if hasattr(unique_together_validator, "set_context"):
                unique_together_validator.set_context(self)
            else:
                call_args.append(self)

            try:
                unique_together_validator(*call_args)
            except ValidationError as exc:
                raise ValidationError({"non_field_errors": exc.detail})

    def _validate_unique_together(self, validated_data):
        # It is possible that instance set for the nested serializer is a QuerySet
        # In that case we run validation for each item on the list individually
        if isinstance(self.instance, QuerySet):
            queryset = self.instance
            self._set_instance_from_queryset(validated_data, queryset)

            self._validate_unique_together_instance(validated_data)
            self.instance = queryset
        else:
            if self.instance is None:
                self._set_instance_from_queryset(validated_data, self.Meta.model.objects.all())
            self._validate_unique_together_instance(validated_data)

    def create(self, validated_data):
        self._validate_unique_together(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._validate_unique_together(validated_data)
        return super().update(instance, validated_data)

    class Meta:
        model = None
        unique_together_validators: List[Tuple[str]] = None
