from dataclasses import dataclass


@dataclass
class Version:
    major: int
    minor: int = 0
    patch: int = 0
    revision: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}.{self.revision}"

    @staticmethod
    def from_components(components_iterable):
        assert Version.min_component_count <= len(components_iterable) <= Version.max_component_count
        components = list(components_iterable)
        major = components[0] if len(components) >= 1 else 0
        minor = components[1] if len(components) >= 2 else 0
        patch = components[2] if len(components) >= 3 else 0
        revision = components[3] if len(components) >= 4 else 0
        return Version(major, minor, patch, revision)

    @classmethod
    @property
    def max_component_count(cls):
        return 4

    @classmethod
    @property
    def min_component_count(cls):
        return 1

