from dataclasses import dataclass

@dataclass(frozen=True)
class TestCase:
    __test__ = False
    id: str
    name: str
    layer: str
    tags: tuple[str, ...] = ()

class TestRegistry:
    __test__ = False
    def __init__(self):
        self._tests: dict[str, TestCase] = {}

    def register(self, case: TestCase):
        self._tests[case.id] = case

    def list(self):
        return list(self._tests.values())

    def by_tag(self, tag: str):
        return [t for t in self._tests.values() if tag in t.tags]
