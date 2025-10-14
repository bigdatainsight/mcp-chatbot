import pytest
from google.genai import types
from src.mcp_chatbot.adapter.tool_schema_converter import convert_schema


class TestConvertSchema:
    
    def test_simple_string_property(self):
        """Test schema with single string property"""
        schema = {
            'type': 'object',
            'properties': {'path': {'type': 'string'}},
            'required': ['path']
        }
        result = convert_schema(schema)
        
        assert result.type == types.Type.OBJECT
        assert 'path' in result.properties
        assert result.properties['path'].type == types.Type.STRING
        assert result.required == ['path']

    def test_multiple_properties_with_descriptions(self):
        """Test schema with multiple properties including descriptions"""
        schema = {
            'type': 'object',
            'properties': {
                'path': {'type': 'string'},
                'tail': {'type': 'number', 'description': 'If provided, returns only the last N lines of the file'},
                'head': {'type': 'number', 'description': 'If provided, returns only the first N lines of the file'}
            },
            'required': ['path']
        }
        result = convert_schema(schema)
        
        assert result.type == types.Type.OBJECT
        assert len(result.properties) == 3
        assert result.properties['path'].type == types.Type.STRING
        assert result.properties['tail'].type == types.Type.NUMBER
        assert result.properties['head'].type == types.Type.NUMBER
        assert result.properties['tail'].description == 'If provided, returns only the last N lines of the file'
        assert result.required == ['path']

    def test_array_property(self):
        """Test schema with array property"""
        schema = {
            'type': 'object',
            'properties': {
                'paths': {
                    'type': 'array',
                    'items': {'type': 'string'}
                }
            },
            'required': ['paths']
        }
        result = convert_schema(schema)
        
        assert result.type == types.Type.OBJECT
        assert result.properties['paths'].type == types.Type.ARRAY
        assert result.properties['paths'].items.type == types.Type.STRING
        assert result.required == ['paths']

    def test_nested_object_in_array(self):
        """Test schema with array containing objects"""
        schema = {
            'type': 'object',
            'properties': {
                'edits': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'oldText': {'type': 'string', 'description': 'Text to search for - must match exactly'},
                            'newText': {'type': 'string', 'description': 'Text to replace with'}
                        }
                    }
                }
            },
            'required': ['edits']
        }
        result = convert_schema(schema)
        
        assert result.type == types.Type.OBJECT
        assert result.properties['edits'].type == types.Type.ARRAY
        assert result.properties['edits'].items.type == types.Type.OBJECT

    def test_boolean_with_default(self):
        """Test schema with boolean property having default value"""
        schema = {
            'type': 'object',
            'properties': {
                'dryRun': {
                    'type': 'boolean',
                    'default': False,
                    'description': 'Preview changes using git-style diff format'
                }
            }
        }
        result = convert_schema(schema)
        
        assert result.type == types.Type.OBJECT
        assert result.properties['dryRun'].type == types.Type.BOOLEAN
        assert result.properties['dryRun'].description == 'Preview changes using git-style diff format'

    def test_enum_property(self):
        """Test schema with enum property"""
        schema = {
            'type': 'object',
            'properties': {
                'sortBy': {
                    'type': 'string',
                    'enum': ['name', 'size'],
                    'default': 'name',
                    'description': 'Sort entries by name or size'
                }
            },
            'required': ['path']
        }
        result = convert_schema(schema)
        
        assert result.type == types.Type.OBJECT
        assert result.properties['sortBy'].type == types.Type.STRING
        assert result.properties['sortBy'].description == 'Sort entries by name or size'

    def test_integer_property(self):
        """Test schema with integer property"""
        schema = {
            'properties': {
                'max_results': {
                    'default': 5,
                    'title': 'Max Results',
                    'type': 'integer'
                }
            },
            'type': 'object'
        }
        result = convert_schema(schema)
        
        assert result.type == types.Type.OBJECT
        assert result.properties['max_results'].type == types.Type.INTEGER

    def test_empty_schema(self):
        """Test empty schema"""
        schema = {
            'type': 'object',
            'properties': {},
            'required': []
        }
        result = convert_schema(schema)
        
        assert result.type == types.Type.OBJECT
        assert len(result.properties) == 0
        assert result.required == []

    def test_non_dict_input(self):
        """Test with non-dictionary input"""
        result = convert_schema("invalid")
        
        assert result.type == types.Type.OBJECT
        assert result.properties is None or len(result.properties) == 0

    def test_missing_properties(self):
        """Test schema without properties field"""
        schema = {
            'type': 'object',
            'required': ['path']
        }
        result = convert_schema(schema)
        
        assert result.type == types.Type.OBJECT
        assert result.required == ['path']

    def test_unknown_type_defaults_to_string(self):
        """Test that unknown types default to STRING"""
        schema = {
            'type': 'object',
            'properties': {
                'unknown_field': {'type': 'unknown_type'}
            }
        }
        result = convert_schema(schema)
        
        assert result.properties['unknown_field'].type == types.Type.STRING

    def test_array_without_items_gets_default_string_items(self):
        """Test that array without items field gets default string items"""
        schema = {
            'type': 'object',
            'properties': {
                'query': {'type': 'array'}
            }
        }
        result = convert_schema(schema)
        
        assert result.properties['query'].type == types.Type.ARRAY
        assert result.properties['query'].items.type == types.Type.STRING