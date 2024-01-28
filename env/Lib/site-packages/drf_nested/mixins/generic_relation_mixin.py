from typing import Union

from rest_framework.fields import empty

from drf_nested.mixins.base_nestable_mixin import BaseNestableMixin


class GenericRelationMixin(BaseNestableMixin):
    generic_relation_fields = ["content_type", "content_type_id", "object_id"]

    def _set_generic_relation_fields(self, value: bool):
        """
        Generic relations should an ability to be created on connected model `create`.
        In case `content_type` or/and `object_id` are required, the validation would fail.
        To prevent that, those fields `required` values are set to false,
        only to be validated on `create`/`update`.
        """
        for field in self.generic_relation_fields:
            if self.fields.get(field) is not None:
                self.fields[field].required = value

    def _patched_method(self, method, *args):
        self._set_generic_relation_fields(True)
        result = method(*args)
        self._set_generic_relation_fields(False)
        return result

    def __init__(self, instance=None, data: Union[empty, dict] = empty, **kwargs):
        super().__init__(instance, data, **kwargs)
        self._set_generic_relation_fields(False)

    def create(self, validated_data):
        return self._patched_method(super().create, validated_data)

    def update(self, instance, validated_data):
        return self._patched_method(super().update, instance, validated_data)
