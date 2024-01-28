from typing import Optional

from rest_framework import serializers
from rest_framework.fields import empty


class ThroughMixin(serializers.ModelSerializer):
    connect_to_model: Optional[bool] = None
    related_name: Optional[str] = None
    should_use_related_model_pk: bool = False

    def __init__(self, instance=None, data=empty, **kwargs):
        if "connect_to_model" in kwargs:
            self.connect_to_model = kwargs.pop("connect_to_model")
        if "related_name" in kwargs:
            self.related_name = kwargs.pop("related_name")
        if "should_use_related_model_pk" in kwargs:
            self.should_use_related_model_pk = kwargs.pop("should_use_related_model_pk")

        super().__init__(instance, data, **kwargs)
