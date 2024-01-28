from copy import deepcopy
from typing import List, Optional, Union

from django.contrib.contenttypes.models import ContentType
from django.db import models
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.serializers import ListSerializer

from drf_nested.mixins.nestable_mixin import NestableMixin
from drf_nested.mixins.through_mixin import ThroughMixin
from drf_nested.utils import NestedInstanceExceptionHandler, NestedListExceptionHandler


class BaseNestedMixin(serializers.ModelSerializer):
    """
    Base class for nested serializers.
    Provides all the needed methods and properties for manipulating nested data.
    """

    populate_nested_initial_data: bool = False

    def __init__(self, instance=None, data: Union[empty, dict, list] = empty, **kwargs):
        if "populate_nested_initial_data" in kwargs:
            self.populate_nested_initial_data = kwargs.pop("populate_nested_initial_data")

        super().__init__(instance, data, **kwargs)

        if self.populate_nested_initial_data:
            if data is not empty and not isinstance(data, list) and data is not None:
                data, nested_fields_data = self._get_nested_fields(data)

                # For all nested fields, initialize serializer with model instances
                # for further unique/unique_together checks
                for field_name, nested_data in nested_fields_data.items():
                    serializer = self.fields.get(field_name)
                    if serializer:
                        serializer_kwargs = (
                            serializer.child._kwargs
                            if "child" in serializer._kwargs
                            else serializer._kwargs
                        )
                        serializer_kwargs.update(context=self.context, data=nested_data)

                        # Initializing the new instances nested serializers
                        if issubclass(serializer.__class__, ListSerializer):
                            serializer = serializer.child.__class__
                            serializer_kwargs.update({"many": True})
                        else:
                            serializer = serializer.__class__

                        # Replacing old serializer with new one, that is populated with data
                        del self.fields[field_name]
                        new_serializer = serializer(**serializer_kwargs)
                        self.fields[field_name] = new_serializer

    def _get_field_pk_value(self, field_name: str, nested_data):
        """
        Gets primary key value from given data for given serializer field name
        :param field_name: serializer field name
        :param nested_data: dict or list containing the nested data for given serializer field name
        :return: value or list of values of primary key for the given serializer field name
        """
        pk_key = self._get_field_pk_name(field_name)
        if isinstance(nested_data, list):
            ids = []
            for item in nested_data:
                if isinstance(item, dict) and item.get(pk_key):
                    ids.append(item.get(pk_key))
            return ids
        else:
            if (
                isinstance(nested_data, dict)
                and pk_key in nested_data
                and nested_data.get(pk_key) is not None
            ):
                return nested_data.get(pk_key)
        return None

    def _get_field_pk_name(self, field_name: str) -> str:
        """
        Gets primary key field name for given serializer field name
        :param field_name: serializer field name
        :return: primary key field name
        """
        serializer = self._get_serializer_by_field_name(field_name)
        if issubclass(serializer.__class__, ListSerializer):
            model = serializer.child.Meta.model
        else:
            model = serializer.Meta.model
        return model._meta.pk.attname

    def _get_nested_fields(self, initial_data, remove_fields: bool = False):
        """
        Returns all nested fields from the initial data
        :param initial_data: data given to serializer
        :param remove_fields: indicator whether nested field should be removed from the original data source
        :return: original data (possibly cleaned of the nested fields) and nested data
        """
        attr = "pop" if remove_fields else "get"
        initial_data_copy = deepcopy(initial_data)
        nested_fields = {
            field_name: initial_data.__getattribute__(attr)(field_name)
            for field_name in initial_data_copy
            if self.get_model_field_name(field_name) in self.nested_field_names
        }
        return initial_data, nested_fields

    @property
    def nested_field_names(self):
        return [
            self.get_model_field_name(name)
            for name in [
                *self.direct_relations,
                *self.reverse_relations,
                *self.many_to_many_fields,
                *self.generic_relations,
            ]
        ]

    # Direct relations
    @property
    def _model_direct_relations(self) -> List:
        return [
            field for field in self.Meta.model._meta.fields if isinstance(field, models.ForeignKey)
        ]

    @property
    def _model_direct_relation_names(self) -> List[str]:
        return [field.name for field in self._model_direct_relations]

    @property
    def _serializer_direct_relation_names(self):
        return [
            self.get_model_field_name(field_name)
            for field_name in self._model_direct_relation_names
        ]

    @property
    def direct_relations(self) -> List[str]:
        return [
            field_name
            for field_name in self.fields
            if self.get_model_field_name(field_name) in self._serializer_direct_relation_names
            and not any(
                isinstance(self.fields.get(field_name), field_class)
                for field_class in self.direct_relation_field_classes
            )
        ]

    @property
    def direct_relation_field_classes(self):
        return [serializers.PrimaryKeyRelatedField]

    def _update_or_create_direct_relations(self, field_name, data):
        serializer = self._get_serializer_by_field_name(field_name)
        pk = data.get(self._get_field_pk_name(field_name))
        with NestedInstanceExceptionHandler(field_name, self):
            if pk is not None:
                nested_instance = serializer.Meta.model.objects.get(pk=pk)
                direct_relation = serializer.update(nested_instance, data)
            else:
                direct_relation = serializer.create(dict(data))
            return direct_relation

    # Reverse relations
    @property
    def _model_reverse_relations(self) -> List:
        return [
            field
            for field in self.Meta.model._meta.related_objects
            if not isinstance(field, models.ManyToManyRel)
        ]

    @property
    def _model_reverse_relation_names(self) -> List[str]:
        return [field.name for field in self._model_reverse_relations]

    @property
    def _serializer_reverse_relation_names(self) -> List[str]:
        return [
            self.get_model_field_name(field_name)
            for field_name in self._model_reverse_relation_names
        ]

    @property
    def reverse_relations(self) -> List[str]:
        return [
            field_name
            for field_name in self.fields
            if self.get_model_field_name(field_name) in self._serializer_reverse_relation_names
            and not (
                any(
                    isinstance(self.fields.get(field_name), field_class)
                    for field_class in self.reverse_relation_field_classes
                )
                and any(
                    isinstance(self.fields.get(field_name).child_relation, field_class)
                    for field_class in self.reverse_relation_child_field_classes
                )
            )
        ]

    @property
    def reverse_relation_field_classes(self):
        return [serializers.ManyRelatedField]

    @property
    def reverse_relation_child_field_classes(self):
        return [serializers.PrimaryKeyRelatedField]

    def _get_serializer_by_field_name(self, field_name):
        serializer = self.fields.get(field_name)
        if not serializer:
            serializer = self.fields.get(self.get_field_name_by_source(field_name))
        return serializer

    def _update_or_create_reverse_relation(self, field_name, data, model_instance):
        serializer = self._get_serializer_by_field_name(field_name)
        related_name = self.get_related_name(self.get_model_field_name(field_name))

        if issubclass(serializer.__class__, ListSerializer) and isinstance(data, list):
            serializer.child.partial = self.partial

            if self._should_be_deleted_on_update(field_name):
                # Removing connected relations that are not provided in the data
                self._delete_difference_on_update(
                    model_instance, data, serializer.child.Meta.model, field_name
                )

            # If there is an instance that can be updated by the provided data - find
            # and use provided data to update existing instance.
            # In other case we add data to the list for further creation and create all the items at once
            if hasattr(serializer.child, "initial_data"):
                serializer_initial_data = deepcopy(serializer.child.initial_data)
                for item, initial_item in zip(data, serializer.child.initial_data):
                    with NestedListExceptionHandler(field_name, self):
                        serializer.child.initial_data = initial_item
                        if not self._should_preserve_provided(serializer.child):
                            item[related_name] = model_instance
                        pk = item.get(self._get_field_pk_name(field_name))

                        if pk is not None:
                            nested_instance = serializer.child.Meta.model.objects.get(pk=pk)
                            serializer.child.update(nested_instance, item)
                        else:
                            serializer.child.create(item)

                serializer.child.initial_data = serializer_initial_data

            else:
                for item in data:
                    with NestedListExceptionHandler(field_name, self):
                        if not self._should_preserve_provided(serializer.child):
                            item[related_name] = model_instance
                        pk = item.get(self._get_field_pk_name(field_name))

                        if pk is not None:
                            nested_instance = serializer.child.Meta.model.objects.get(pk=pk)
                            serializer.child.update(nested_instance, item)
                        else:
                            serializer.child.create(item)
        else:
            with NestedInstanceExceptionHandler(field_name, self):
                pk = data.get(self._get_field_pk_name(field_name))
                if not self._should_preserve_provided(serializer):
                    data[related_name] = model_instance
                if pk is not None:
                    nested_instance = serializer.Meta.model.objects.get(pk=pk)
                    serializer.update(nested_instance, data)
                else:
                    serializer.create(dict(data))

    # Many-to-many fields
    @property
    def _model_many_to_many_fields(self) -> List:
        reverse_related_m2m = [
            field
            for field in self.Meta.model._meta.related_objects
            if isinstance(field, models.ManyToManyRel)
        ]
        regular_m2m = self.Meta.model._meta.many_to_many
        return [*regular_m2m, *reverse_related_m2m]

    @property
    def _model_many_to_many_field_names(self) -> List[str]:
        return [field.name for field in self._model_many_to_many_fields]

    @property
    def _serializer_many_to_many_field_names(self) -> List[str]:
        return [
            self.get_model_field_name(field_name)
            for field_name in self._model_many_to_many_field_names
        ]

    @property
    def many_to_many_fields(self) -> List[str]:
        return [
            field_name
            for field_name in self.fields
            if self.get_model_field_name(field_name) in self._serializer_many_to_many_field_names
            and not (
                any(
                    isinstance(self.fields.get(field_name), field_class)
                    for field_class in self.many_to_many_field_classes
                )
                and any(
                    isinstance(self.fields.get(field_name).child_relation, field_class)
                    for field_class in self.many_to_many_child_field_classes
                )
            )
        ]

    @property
    def many_to_many_field_classes(self):
        return [serializers.ManyRelatedField]

    @property
    def many_to_many_child_field_classes(self):
        return [serializers.PrimaryKeyRelatedField]

    def _update_or_create_many_to_many_field(self, field_name, data, model_instance):
        serializer = self._get_serializer_by_field_name(field_name)

        if issubclass(serializer.__class__, ListSerializer) and isinstance(data, list):
            serializer.child.partial = self.partial
            related_name = None
            should_use_related_model_pk = False
            if issubclass(serializer.child.__class__, ThroughMixin):
                related_name = serializer.child.related_name
                should_use_related_model_pk = serializer.child.should_use_related_model_pk

            if self._should_be_deleted_on_update(field_name):
                # Removing connected relations that are not provided in the data
                self._delete_difference_on_update(
                    model_instance, data, serializer.child.Meta.model, field_name
                )

            # If there is an instance that can be updated by the provided data - find
            # and use provided data to update existing instance.
            # In other case we create that item and connect all the items to the current model at once
            items_to_add = []
            if hasattr(serializer.child, "initial_data"):
                serializer_initial_data = deepcopy(serializer.child.initial_data)
                for item, initial_item in zip(data, serializer.child.initial_data):
                    serializer.child.initial_data = initial_item
                    if related_name and not self._should_preserve_provided(serializer):
                        item[related_name] = (
                            model_instance.pk if should_use_related_model_pk else model_instance
                        )
                    with NestedListExceptionHandler(field_name, self):
                        pk = item.get(self._get_field_pk_name(field_name))
                        if pk is not None:
                            nested_instance = serializer.child.Meta.model.objects.get(pk=pk)
                            nested_instance = serializer.child.update(nested_instance, item)
                        else:
                            nested_instance = serializer.child.create(dict(item))
                        if nested_instance:
                            items_to_add.append(nested_instance)
                    serializer.child.initial_data = serializer_initial_data

            else:
                for item in data:
                    with NestedListExceptionHandler(field_name, self):
                        pk = item.get(self._get_field_pk_name(field_name))
                        if related_name and not self._should_preserve_provided(serializer):
                            item[related_name] = (
                                model_instance.pk if should_use_related_model_pk else model_instance
                            )
                        if pk is not None:
                            nested_instance = serializer.child.Meta.model.objects.get(pk=pk)
                            nested_instance = serializer.child.update(nested_instance, item)
                        else:
                            nested_instance = serializer.child.create(dict(item))
                        if nested_instance:
                            items_to_add.append(nested_instance)

            if (
                not issubclass(serializer.child.__class__, ThroughMixin)
                or serializer.child.connect_to_model
            ) and not self._should_preserve_provided(serializer.child):
                model_instance.__getattribute__(self.get_model_field_name(field_name)).add(
                    *items_to_add
                )

    # Generic relations
    @property
    def _model_generic_relations(self) -> List:
        return self.Meta.model._meta.private_fields

    @property
    def _model_generic_relation_names(self) -> List[str]:
        return [field.name for field in self._model_generic_relations]

    @property
    def _serializer_generic_relation_names(self) -> List[str]:
        return [
            self.get_model_field_name(field_name)
            for field_name in self._model_generic_relation_names
        ]

    @property
    def generic_relations(self) -> List[str]:
        return [
            field_name
            for field_name in self.fields
            if self.get_model_field_name(field_name) in self._serializer_generic_relation_names
        ]

    def _update_or_create_generic_relation(self, field_name, data, model_instance):
        serializer = self._get_serializer_by_field_name(field_name)
        if issubclass(serializer.__class__, ListSerializer) and isinstance(data, list):
            serializer.child.partial = self.partial

            if self._should_be_deleted_on_update(field_name):
                # Removing connected relations that are not provided in the data
                self._delete_difference_on_update(
                    model_instance, data, serializer.child.Meta.model, field_name
                )

            for item in data:
                with NestedListExceptionHandler(field_name, self):
                    content_type = ContentType.objects.get_for_model(model_instance.__class__)
                    # Setting special for GenericRelation model fields
                    if not self._should_preserve_provided(serializer.child):
                        item.update(
                            {
                                "content_type_id": content_type.id,
                                "object_id": model_instance.id,
                            }
                        )
                    pk = item.get(self._get_field_pk_name(field_name))
                    if pk is not None:
                        nested_instance = serializer.child.Meta.model.objects.get(pk=pk)
                        serializer.child.update(nested_instance, item)
                    else:
                        serializer.child.create(dict(item))

    # Helper functions

    def _should_be_deleted_on_update(self, field_name):
        """
        Indicates if the field instances not provided in nested data should be deleted on update.
        Can be overloaded if needed.
        :param field_name: field name
        :return: if the field should be cleaned on update
        """
        return not self.partial

    def _get_field_by_name(self, field_name, list_of_fields):
        for field in list_of_fields:
            if field.name == field_name:
                return field.remote_field.name
        return None

    def _is_field_nested(self, field_name):
        return self.get_model_field_name(field_name) in self.nested_field_names

    def _has_nested_fields(self, validated_data):
        fields = [self.get_model_field_name(field_name) for field_name in validated_data]
        return any([field in self.nested_field_names for field in fields])

    def _should_preserve_provided(self, serializer):
        return isinstance(serializer, NestableMixin) and serializer.preserve_provided

    def _delete_difference_on_update(self, instance, objects, model_class, field_name):
        """
        Deletes related objects on update
        :param instance: model instance which connections to be searched for the differences
        :param objects: instances that should be preserved
        :param model_class: related model class that is used to searched for redundant instances
        :param field_name: field name that is searched for the differences
        :return: None
        """
        if isinstance(objects, list):
            objects_to_delete = list(
                set([item.pk for item in instance.__getattribute__(field_name).all()])
                - set([item.get(self._get_field_pk_name(field_name)) for item in objects])
            )

            if field_name not in self.many_to_many_fields:
                for object_id in objects_to_delete:
                    if object_id:
                        try:
                            model_class.objects.get(pk=object_id).delete()

                        except model_class.DoesNotExist:
                            pass
            else:
                for object_id in objects_to_delete:
                    if object_id:
                        try:
                            instance.__getattribute__(field_name).remove(
                                model_class.objects.get(pk=object_id)
                            )
                        except (model_class.DoesNotExist, AttributeError):
                            pass

    def get_related_name(self, field_name: str) -> Optional[str]:
        """
        Gets related model field name using serializer field name
        :param field_name: field name
        :return: related model field name
        """
        name_to_look_for = self.get_model_field_name(field_name)

        list_of_fields, related_field = None, None

        if field_name in self._model_many_to_many_field_names:
            list_of_fields = self._model_many_to_many_fields
        elif field_name in self._model_reverse_relation_names:
            list_of_fields = self._model_reverse_relations
        elif field_name in self._model_generic_relation_names:
            list_of_fields = self._model_generic_relations
        if list_of_fields is not None:
            related_field = self._get_field_by_name(name_to_look_for, list_of_fields)

        if related_field is None:
            raise ValidationError({field_name: ["No related name."]})
        return related_field

    def get_model_field_name(self, field_name) -> str:
        """
        Gets corresponding model field name using serializer field name
        :param field_name: field name
        :return: model field name
        """
        serializer = self.fields.get(field_name)
        if serializer is None:
            source = self.get_field_name_by_source(field_name)
            if source != field_name:
                return self.get_model_field_name(source)
        if issubclass(serializer.__class__, ListSerializer):
            serializer = serializer.child
        if issubclass(serializer.__class__, NestableMixin) and serializer.write_source is not None:
            return serializer.write_source
        return field_name

    def get_field_name_by_source(self, source) -> str:
        """
        Gets field name to use further based on the given serializer source
        :param source: serializer source
        :return: field name
        """
        for key, value in self.fields.items():
            actual_value = value
            if isinstance(value, ListSerializer):
                actual_value = value.child
            if actual_value.source == source:
                return key
            elif isinstance(actual_value, NestableMixin) and actual_value.write_source == source:
                return key
        return source

    def extract_nested_types(self, nested_fields_data) -> dict:
        """
        Extracts all the nested data by type, to ease the overall create/update flow
        :param nested_fields_data: nested data, taken from the original data source
        :return: nested fields, sorted by relationship type
        """
        types = {
            "direct_relations": [],
            "reverse_relations": [],
            "generic_relations": [],
            "many_to_many_fields": [],
        }
        for field_name, field_value in nested_fields_data.items():
            original_name = field_name
            model_field_name = self.get_model_field_name(field_name)

            if field_name not in self.fields:
                field_name = model_field_name

            field_by_source = self.get_field_name_by_source(original_name)
            if self.fields.get(field_by_source).read_only:
                continue

            if model_field_name in self._serializer_direct_relation_names:
                types["direct_relations"].append(
                    {
                        "name": field_name,
                        "data": field_value,
                        "original_name": original_name,
                    }
                )

            if model_field_name in self._serializer_reverse_relation_names:
                types["reverse_relations"].append(
                    {
                        "name": field_name,
                        "data": field_value,
                        "original_name": original_name,
                    }
                )

            if model_field_name in self._serializer_generic_relation_names:
                types["generic_relations"].append(
                    {
                        "name": field_name,
                        "data": field_value,
                        "original_name": original_name,
                    }
                )

            if model_field_name in self._serializer_many_to_many_field_names:
                types["many_to_many_fields"].append(
                    {
                        "name": field_name,
                        "data": field_value,
                        "original_name": original_name,
                    }
                )

        return types

    class Meta:
        model = None
