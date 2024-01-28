from typing import Union

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

from drf_nested.mixins.base_nested_mixin import BaseNestedMixin


class CreateNestedMixin(BaseNestedMixin):
    def __init__(self, instance=None, data: Union[empty, dict] = empty, **kwargs):
        super().__init__(instance, data, **kwargs)
        if not hasattr(self.Meta, "forbidden_on_create"):
            setattr(self.Meta, "forbidden_on_create", [])

    @transaction.atomic
    def create(self, validated_data):
        """
        :param validated_data:
        :return:
        """
        self._errors = {}
        if self._has_nested_fields(validated_data):
            if any([self._is_field_forbidden(request_field) for request_field in validated_data]):
                raise ValidationError(
                    {"nested_field": [_("Nested fields are not allowed on create.")]}
                )

            validated_data, nested_fields_data = self._get_nested_fields(
                validated_data, remove_fields=True
            )

            nested_field_types = self.extract_nested_types(nested_fields_data)

            # Creating direct relations like ForeignKeys before we create initial instance
            for field in nested_field_types["direct_relations"]:
                field_name = field.get("name")
                field_data = field.get("data")
                if isinstance(field_data, dict):
                    nested_instance = self._update_or_create_direct_relations(
                        field_name, field_data
                    )
                    validated_data[field.get("original_name")] = nested_instance

            model_instance = super().create(validated_data)

            # Creating reversed relations like the models that have the current model as ForeignKeys
            # using created initial instance
            for field in nested_field_types["reverse_relations"]:
                field_name = field.get("name")
                field_data = field.get("data")
                self._update_or_create_reverse_relation(field_name, field_data, model_instance)

            # Creating generic relations using created initial instance
            for field in nested_field_types["generic_relations"]:
                field_name = field.get("name")
                field_data = field.get("data")
                self._update_or_create_generic_relation(field_name, field_data, model_instance)

            # Creating many-to-many relations using created initial instance
            for field in nested_field_types["many_to_many_fields"]:
                field_name = field.get("name")
                field_data = field.get("data")
                self._update_or_create_many_to_many_field(field_name, field_data, model_instance)

            if self._errors:
                raise ValidationError(self._errors)
        else:
            model_instance = super().create(validated_data)

        model_instance.refresh_from_db()

        return model_instance

    def _is_field_forbidden(self, field_name):
        if hasattr(self.Meta, "forbidden_on_create") and isinstance(
            self.Meta.forbidden_on_create, list
        ):
            return self.get_model_field_name(field_name) in self.Meta.forbidden_on_create
        return False

    class Meta:
        model = None
        forbidden_on_create = None
