from pydantic import BaseModel

from pydantic_rng import PydanticRandom

# ----------------------------
# TEST MODELS
# ----------------------------


class SmallModel(BaseModel):
    field1: int
    field2: int


def test_chain_flow():
    a = PydanticRandom()
    a.configure_rng(numeric_max=12)
    assert a.numeric_max == 12

    b = PydanticRandom().configure_rng(max_sequence_length=20)
    assert b.max_sequence_length == 20


def test_same_seed():
    a = PydanticRandom(seed=12).generate(SmallModel)
    b = PydanticRandom(seed=12).generate(SmallModel)
    assert a == b


def test_different_no_seed():
    rng = PydanticRandom()
    a = rng.generate(SmallModel)
    b = rng.generate(SmallModel)
    assert a != b


def test_same_seed_progressive():
    rng1 = PydanticRandom(seed=12)
    rng2 = PydanticRandom(seed=12)
    a1, b1 = rng1.generate(SmallModel), rng1.generate(SmallModel)
    a2, b2 = rng2.generate(SmallModel), rng2.generate(SmallModel)

    # The first pair differ (each call advances RNG)
    assert a1 != b1

    # But the *sequence* is deterministic across "runs"
    assert a1 == a2
    assert b1 == b2
