from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field

from pydantic_rng import PydanticRandom

# --- Test Models ---


class SimpleModel(BaseModel):
    x: int
    y: float
    z: str


class DefaultModel(BaseModel):
    a: int = 42
    b: str = "hello"
    c: bool = True


class OptionalModel(BaseModel):
    maybe: Optional[int]
    text: Optional[str] = None


class CollectionModel(BaseModel):
    nums: List[int]
    mapping: Dict[str, float]
    tags: Set[str]


class ConstrainedModel(BaseModel):
    score: int = Field(..., ge=0, le=100)
    name: str = Field(..., min_length=3, max_length=10)


class NestedInner(BaseModel):
    name: str
    value: float


class NestedOuter(BaseModel):
    id: int
    inner: NestedInner
    extras: List[NestedInner]


# --- Tests ---


def test_basic_model_reproducibility():
    rng1 = PydanticRandom(seed=123)
    rng2 = PydanticRandom(seed=123)

    m1 = rng1.generate(SimpleModel)
    m2 = rng2.generate(SimpleModel)

    assert m1 == m2  # identical with same seed
    assert isinstance(m1, SimpleModel)


def test_default_model_preserves_defaults():
    # use default
    rng = PydanticRandom(seed=42).configure_rng(
        default_chance=1.0,
    )
    m = rng.generate(DefaultModel)

    # default fields should remain the same unless overridden by your generator
    assert m.a == 42
    assert m.b == "hello"
    assert m.c is True


def test_optionals_can_be_none_or_value():
    rng = PydanticRandom(seed=5)
    m = rng.generate(OptionalModel)
    assert isinstance(m, OptionalModel)
    # both None and non-None are valid; just ensure no errors
    assert m.maybe is None or isinstance(m.maybe, int)


def test_collections_generate_values():
    rng = PydanticRandom(seed=7)
    m = rng.generate(CollectionModel)
    assert isinstance(m.nums, list)
    assert isinstance(m.mapping, dict)
    assert isinstance(m.tags, set)


def test_constrained_fields_respect_bounds():
    rng = PydanticRandom(seed=8)
    m = rng.generate(ConstrainedModel)
    assert 0 <= m.score <= 100
    assert 3 <= len(m.name) <= 10


def test_nested_models_generate_properly():
    rng = PydanticRandom(seed=9)
    m = rng.generate(NestedOuter)
    assert isinstance(m.inner, NestedInner)
    assert all(isinstance(e, NestedInner) for e in m.extras)
    assert isinstance(m.id, int)


def test_deterministic_sequence():
    rng = PydanticRandom(seed=99)
    a1 = rng.generate(SimpleModel)
    a2 = rng.generate(SimpleModel)

    rng2 = PydanticRandom(seed=99)
    b1 = rng2.generate(SimpleModel)
    b2 = rng2.generate(SimpleModel)

    assert a1 == b1
    assert a2 == b2
