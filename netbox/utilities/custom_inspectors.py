from django.contrib.postgres.fields import JSONField
from drf_yasg import openapi
from drf_yasg.inspectors import FieldInspector, NotHandled, PaginatorInspector, SwaggerAutoSchema
from drf_yasg.utils import get_serializer_ref_name
from rest_framework.fields import ChoiceField
from rest_framework.relations import ManyRelatedField

from utilities.api import ChoiceField, SerializedPKRelatedField, WritableNestedSerializer


class NetBoxSwaggerAutoSchema(SwaggerAutoSchema):
    writable_serializers = {}

    def get_request_serializer(self):
        serializer = super().get_request_serializer()

        if serializer is not None and self.method in self.implicit_body_methods:
            properties = {}
            for child_name, child in serializer.fields.items():
                if isinstance(child, (ChoiceField, WritableNestedSerializer)):
                    properties[child_name] = None
                elif isinstance(child, ManyRelatedField) and isinstance(child.child_relation, SerializedPKRelatedField):
                    properties[child_name] = None

            if properties:
                if type(serializer) not in self.writable_serializers:
                    writable_name = 'Writable' + type(serializer).__name__
                    meta_class = getattr(type(serializer), 'Meta', None)
                    if meta_class:
                        ref_name = 'Writable' + get_serializer_ref_name(serializer)
                        writable_meta = type('Meta', (meta_class,), {'ref_name': ref_name})
                        properties['Meta'] = writable_meta

                    self.writable_serializers[type(serializer)] = type(writable_name, (type(serializer),), properties)

                writable_class = self.writable_serializers[type(serializer)]
                serializer = writable_class()

        return serializer


class SerializedPKRelatedFieldInspector(FieldInspector):
    def field_to_swagger_object(self, field, swagger_object_type, use_references, **kwargs):
        SwaggerType, ChildSwaggerType = self._get_partial_types(field, swagger_object_type, use_references, **kwargs)
        if isinstance(field, SerializedPKRelatedField):
            return self.probe_field_inspectors(field.serializer(), ChildSwaggerType, use_references)

        return NotHandled


class NullableBooleanFieldInspector(FieldInspector):
    def process_result(self, result, method_name, obj, **kwargs):

        if isinstance(result, openapi.Schema) and isinstance(obj, ChoiceField) and result.type == 'boolean':
            keys = obj.choices.keys()
            if set(keys) == {None, True, False}:
                result['x-nullable'] = True
                result.type = 'boolean'

        return result


class JSONFieldInspector(FieldInspector):
    """Required because by default, Swagger sees a JSONField as a string and not dict
    """
    def process_result(self, result, method_name, obj, **kwargs):
        if isinstance(result, openapi.Schema) and isinstance(obj, JSONField):
            result.type = 'dict'
        return result


class NullablePaginatorInspector(PaginatorInspector):
    def process_result(self, result, method_name, obj, **kwargs):
        if method_name == 'get_paginated_response' and isinstance(result, openapi.Schema):
            next = result.properties['next']
            if isinstance(next, openapi.Schema):
                next['x-nullable'] = True
            previous = result.properties['previous']
            if isinstance(previous, openapi.Schema):
                previous['x-nullable'] = True

        return result
