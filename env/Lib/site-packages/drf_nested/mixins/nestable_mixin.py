from typing import Optional

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty

from drf_nested.mixins.base_nestable_mixin import BaseNestableMixin
from drf_nested.utils.queryset_to_instance import nested_update, nested_validate


class NestableMixin(BaseNestableMixin):
    write_source: Optional[str] = None
    preserve_provided: bool = False
    allow_create: bool = True
    allow_update: bool = True

    def __init__(self, instance=None, data=empty, **kwargs):
        if "write_source" in kwargs:
            self.write_source = kwargs.pop("write_source")
        if "preserve_provided" in kwargs:
            self.preserve_provided = kwargs.pop("preserve_provided")
        if "allow_create" in kwargs:
            self.allow_create = kwargs.pop("allow_create")
        if "allow_update" in kwargs:
            self.allow_update = kwargs.pop("allow_update")

        super().__init__(instance, data, **kwargs)

    @nested_validate
    def validate(self, data):
        return super().validate(data)

    def create(self, validated_data):
        if not self.allow_create:
            raise ValidationError({"non_field_errors": [_("Create is forbidden")]})
        return super().create(validated_data)

    @nested_update
    def update(self, instance, validated_data):
        if not self.allow_update:
            raise ValidationError({"non_field_errors": [_("Update is forbidden")]})
        return super().update(instance, validated_data)
