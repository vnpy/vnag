import unittest

from vnag.local import generate_function_schema


def sample_tool(
    path: str,
    expected_occurrences: int | None = None,
    replace_all: bool = True,
    alt_value: int | str = 1,
) -> str:
    return path


class LocalSchemaTestCase(unittest.TestCase):
    def test_optional_type_generates_nullable_schema(self) -> None:
        schema: dict = generate_function_schema(sample_tool)
        properties: dict = schema["properties"]

        self.assertEqual(properties["path"], {"type": "string"})
        self.assertEqual(properties["replace_all"], {"type": "boolean"})
        self.assertEqual(
            properties["expected_occurrences"],
            {"type": "integer", "nullable": True},
        )
        self.assertEqual(properties["alt_value"], {"type": "string"})
        self.assertEqual(schema["required"], ["path"])


if __name__ == "__main__":
    unittest.main()
