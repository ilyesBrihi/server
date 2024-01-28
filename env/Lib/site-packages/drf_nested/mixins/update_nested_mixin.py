from django.db import transaction
from rest_framework.exceptions import ValidationError

from drf_nested.mixins.base_nested_mixin import BaseNestedMixin


class UpdateNestedMixin(BaseNestedMixin):
    @transaction.atomic
    def update(self, instance, validated_data):
        """
        :param instance:
        :param validated_data:
        :return:
        """
        self._errors = {}
        if self._has_nested_fields(validated_data):
            validated_data, nested_fields_data = self._get_nested_fields(
                validated_data, remove_fields=True
            )

            nested_field_types = self.extract_nested_types(nested_fields_data)

            # Updating or creating direct relations like ForeignKeys before we create initial instance
            for field in nested_field_types["direct_relations"]:
                field_name = field.get("name")
                field_data = field.get("data")
                if isinstance(field_data, dict):
                    nested_instance = self._update_or_create_direct_relations(
                        field_name, field_data
                    )
                    validated_data[field.get("original_name")] = nested_instance
                elif field_data is None:
                    validated_data[field.get("original_name")] = field_data

            model_instance = super().update(instance, validated_data)

            # Updating or creating reversed relations like the models that have the current model as ForeignKeys
            # using created initial instance
            for field in nested_field_types["reverse_relations"]:
                field_name = field.get("name")
                field_data = field.get("data")
                self._update_or_create_reverse_relation(field_name, field_data, model_instance)

            # Updating or creating generic relations using created initial instance
            for field in nested_field_types["generic_relations"]:
                field_name = field.get("name")
                field_data = field.get("data")
                self._update_or_create_generic_relation(field_name, field_data, model_instance)

            # Updating or creating many-to-many relations using created initial instance
            for field in nested_field_types["many_to_many_fields"]:
                field_name = field.get("name")
                field_data = field.get("data")
                self._update_or_create_many_to_many_field(field_name, field_data, model_instance)

            if self._errors:
                raise ValidationError(self._errors)
        else:
            model_instance = super().update(instance, validated_data)

        model_instance.refresh_from_db()

        return model_instance
