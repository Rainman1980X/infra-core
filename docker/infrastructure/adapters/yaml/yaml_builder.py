from typing import Any, Dict, List, Optional

from ruamel.yaml import YAML
from ruamel.yaml.compat import StringIO

from infrastructure.adapters.yaml.yaml_node import YAMLNode
from infrastructure.adapters.yaml.yaml_value import YamlValue


class FluentYAMLBuilder:
    """Fluent API Builder for constructing properly formatted YAML structures using ruamel.yaml."""

    def __init__(self, root_name: Optional[str] = None):
        self.root = YAMLNode(root_name) if root_name else None
        self.current = self.root

    def add_child(self, name: str, value: Any = None, stay: bool = False) -> "FluentYAMLBuilder":
        """Adds a child node and ensures that a root node exists if missing."""
        if self.root is None:
            self.root = YAMLNode(name, value)  # First child becomes the root
            self.current = self.root
        else:
            new_child = self.current.add_child(name, value)
            if not stay:
                self.current = new_child
        return self

    def navigate_to(self, path: List[str]) -> "FluentYAMLBuilder":
        """Navigate to a specific entry by path."""
        node = self.root
        traversed_path = []  # Hält den erfolgreichen Navigationspfad

        for key in path:
            child = node.find_child(key)
            if child:  # Wenn ein Kind gefunden wurde, navigiere weiter
                node = child
                traversed_path.append(key)  # Füge den Schlüssel dem navigierten Pfad hinzu
            else:
                # Gebe detaillierte Fehlermeldung zu dem Punkt aus, an dem der Fehler auftritt
                raise KeyError(
                    f"Path not found at segment '{key}' after traversing: {'/'.join(traversed_path)}"
                )

        self.current = node  # Aktualisiere den aktuellen Knoten
        return self

    def navigate_to_recursively(self, name: str) -> "FluentYAMLBuilder":
        """Recursively find a node by its name, starting from the root."""

        def recursive_search(node, name_rc):
            if node.name == name_rc:
                return node
            for child in node.children:
                result_rc = recursive_search(child, name)
                if result_rc:
                    return result_rc
            return None

        result = recursive_search(self.root, name)
        if not result:
            raise KeyError(f"Node '{name}' not found in the tree.")
        self.current = result
        return self

    def delete_current(self) -> "FluentYAMLBuilder":
        """Deletes the current node and its subtree."""
        if self.current.parent:
            parent = self.current.parent
            parent.remove_child(self.current.name)
            self.current = parent
        else:
            raise ValueError("Cannot delete root node")
        return self

    def insert_at_current(self, name: str, value: Any = None) -> "FluentYAMLBuilder":
        """Inserts a new node at the current position."""
        self.current.add_child(name, value)
        return self

    def find_entry(self, name: str) -> Optional[Dict[str, Any]]:
        """Finds an entry by name and returns its dictionary representation."""
        for child in self.root.children:
            if child.name == name:
                return self.to_dict(child)
        return None

    def find_all_entries(self) -> List[Dict[str, Any]]:
        """Returns all entries as a list of dictionaries."""
        return [self.to_dict(child) for child in self.root.children]

    def up(self) -> "FluentYAMLBuilder":
        """Moves up one level in the tree if a parent exists."""
        if self.current.parent:
            self.current = self.current.parent
        return self

    def build(self):
        """Constructs the YAML dictionary, ensuring scalar values are stored correctly."""
        return self.to_dict()

    def to_dict(self, node: Optional[YAMLNode] = None) -> Dict[str, Any]:
        """Converts the tree structure into a correctly formatted dictionary for YAML export."""
        if node is None:
            node = self.root

        result = {}

        #  Check if value is a list (CommentedSeq) and return it directly
        if isinstance(node.value, list):
            return {node.name: node.value}  # Lists should be returned as is

        # Check if value has a `to_dict()` method before calling it
        if node.value and hasattr(node.value, "to_dict"):
            return {node.name: node.value.to_dict()}

        for child in node.children:
            child_dict = self.to_dict(child)
            key, value = next(iter(child_dict.items()))

            if key in result:
                if isinstance(result[key], list):
                    result[key].append(value)
                else:
                    result[key] = [result[key], value]
            else:
                result[key] = value

        return {node.name: result} if result else {node.name: {}}

    def to_yaml(self) -> str:
        """Generates a YAML representation of the tree structure with proper formatting."""
        yaml = YAML()
        yaml.default_flow_style = False
        yaml.indent(mapping=2, sequence=4, offset=2)

        output = StringIO()
        yaml.dump(self.to_dict(), output)
        return output.getvalue()

    def load_from_string(self, yaml_content: str) -> "FluentYAMLBuilder":
        """Parses a YAML-formatted string and builds a corresponding tree structure using add_child()."""
        yaml = YAML()
        data = yaml.load(yaml_content) or {}  # Ensure at least an empty dictionary

        if not isinstance(data, dict):
            raise ValueError("Invalid YAML format, expected a dictionary with a root key.")

        # Extract the first root key dynamically
        root_key = next(iter(data.keys()))
        if self.root is None:
            # Set root only if it doesn't exist yet
            self.add_child(root_key, stay=True)
        else:
            # Abort if the existing root doesn't match the YAML root
            if self.root.name != root_key:
                raise ValueError(f"Root mismatch! Expected '{self.root.name}', but found '{root_key}' in YAML.")

        # Insert only the contents under the existing root
        self._parse_dict_to_tree(data[root_key])

        return self

    def _parse_dict_to_tree(self,  data: Any):
        """Recursively converts a YAML dictionary or list into a tree structure using add_child()."""
        if isinstance(data, dict):
            for key, value in data.items():
                self.add_child(key, stay=True)  # Navigate into child
                self._parse_dict_to_tree(value)
                self.up()  # Move back up after processing the child
        elif isinstance(data, list):
            self.current.value = data  # Preserve lists as values
        else:
            self.current.value = YamlValue(data)  # Store scalar values

