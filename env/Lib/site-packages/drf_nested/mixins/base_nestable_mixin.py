from rest_framework import serializers


class BaseNestableMixin(serializers.ModelSerializer):
    def _get_model_pk(self):
        if isinstance(self, serializers.ListSerializer):
            model = self.child.Meta.model
        else:
            model = self.Meta.model
        return model._meta.pk.attname

    def _set_instance_from_queryset(self, validated_data, queryset):
        pk = self._get_model_pk()
        self.instance = None
        if validated_data and isinstance(validated_data, dict) and pk in validated_data:
            try:
                instance = queryset.get(pk=validated_data.get(pk))
                self.instance = instance
            except queryset.model.DoesNotExist:
                pass

    def _set_instance_from_existing(self, validated_data, instance):
        pk = self._get_model_pk()
        if validated_data and isinstance(validated_data, dict) and pk in validated_data:
            validated_data_pk = validated_data.get(pk)
            if self.instance is not None:
                model_class = instance.__class__
                if self.instance.pk != validated_data_pk:
                    try:
                        self.instance = model_class.objects.get(pk=validated_data_pk)
                    except model_class.model.DoesNotExist:
                        pass

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    class Meta:
        model = None
