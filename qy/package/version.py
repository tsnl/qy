from dataclasses import dataclass


@dataclass
class Version:
    major: int
    minor: int
    patch: int
    revision: int
