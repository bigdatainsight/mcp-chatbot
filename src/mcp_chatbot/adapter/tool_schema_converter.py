from google.genai import types


def convert_schema(mcpInputSchema: dict) -> types.Schema:
    """Convert MCP tool schema to Gemini schema format."""
    if not isinstance(mcpInputSchema, dict):
        return types.Schema(type=types.Type.OBJECT)

    properties = {}
    if 'properties' in mcpInputSchema:
        for prop_name, prop_def in mcpInputSchema['properties'].items():
            prop_type_str = prop_def.get('type', 'string').upper()
            prop_type = getattr(types.Type, prop_type_str, types.Type.STRING)

            prop_schema = types.Schema(
                type=prop_type,
                description=prop_def.get('description', '')
            )

            # Handle array types with items
            if prop_type == types.Type.ARRAY:
                if 'items' in prop_def:
                    items_type_str = prop_def['items'].get('type', 'string').upper()
                    items_type = getattr(types.Type, items_type_str, types.Type.STRING)
                    prop_schema.items = types.Schema(type=items_type)
                else:
                    # Default to string items if not specified
                    prop_schema.items = types.Schema(type=types.Type.STRING)

            properties[prop_name] = prop_schema

    return types.Schema(
        type=types.Type.OBJECT,
        properties=properties,
        required=mcpInputSchema.get('required', [])
    )