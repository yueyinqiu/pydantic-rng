# pydantic-rng

A simple library for generating random, valid Pydantic models.

This tool helps you quickly create mock data for testing, prototyping, and demonstration purposes by generating random values that conform to your Pydantic model schemas. It supports a wide range of types and validation constraints.

## ✨ Features

* **Type-aware Generation**: Generates appropriate data for common Python types (`str`, `int`, `float`, `bool`, `list`, `dict`, `set`, etc.).
* **pydantic Integration**: Works seamlessly with Pydantic's `BaseModel` for recursive data generation.
* **Constraint Support**: Respects a wide variety of Pydantic validation constraints from the `annotated_types` library, including `MinLen`, `MaxLen`, `Ge`, `Gt`, `Le`, `Lt`, and `MultipleOf`.
* **Configurable**: Customize the behavior of the random generator with global settings for things like numeric and string ranges, and the probability of generating `None` for optional fields.

## 🚀 Installation

Install the package (usually as a dev dependency):

```bash
uv add --dev pydantic-rng
```

## Generate Basic Class RNG

```python
from pydantic import BaseModel
from pydantic_rng import PydanticRandom

class User(BaseModel):
    user_id: int
    name: str
    is_active: bool
    email: str | None = None

random_user = PydanticRandom().generate(User)
print(random_user.model_dump_json(indent=2))
```


Or, more usually...

```python
from typing import Annotated

from tqdm.rich import trange # requires `rich` as well
from pydantic import BaseModel, Field
from pydantic_rng import PydanticRandom

N = 1_000_000

class World(BaseModel):
    radius: Annotated[float, Field(gt=0, lt=360)]
    moons: list[str]

# set seed for consistency across runs
# also configure 
rng = PydanticRandom(seed=42).configure_rng(
    # max length of moon names
    max_sequence_length=10,
)

with open("random-data.jsonl", "w") as f:
    for _ in trange(N):
        item = generate(World)
        f.write(item.model_dump_json() + "\n")
```
