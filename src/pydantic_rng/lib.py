import logging
import random
import string
import types
from datetime import date, datetime, time
from typing import Any, Literal, Type, TypeAlias, TypeVar, Union, get_args, get_origin

from annotated_types import Ge, Gt, Le, Lt, MaxLen, MinLen, MultipleOf
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

MetadataList: TypeAlias = list[Gt | Ge | Lt | Le | MultipleOf | MinLen | MaxLen]

# -------------------
# Constants
# -------------------
CHARACTERS = list(
    set(string.ascii_letters + string.digits + string.punctuation + string.whitespace)
)
MIN_YEAR = 1000
MAX_YEAR = 2100
MIN_MONTH = 1
MAX_MONTH = 12
MIN_DAY = 1
MAX_DAY = 28
MIN_HOUR = 0
MAX_HOUR = 23
MIN_MINUTE = 0
MAX_MINUTE = 59
MIN_SECOND = 0
MAX_SECOND = 59


# -------------------
# Primitive generators
# -------------------


class PydanticRandom:
    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        if seed:
            logging.info(f"Using seed: {seed}, expect consistent results")
        else:
            logging.info("Using system standard seed, expect randomized results")
        self.seed = seed

        # defaults
        self.numeric_min = -1_000_000
        self.numeric_max = 1_000_000
        self.min_str_length = 4
        self.max_str_length = 100
        self.max_sequence_length = 100
        self.null_chance = 0.2
        self.default_chance = 0.6

    def configure_rng(
        self,
        numeric_min: int | None = None,
        numeric_max: int | None = None,
        min_str_length: int | None = None,
        max_str_length: int | None = None,
        max_sequence_length: int | None = None,
        null_chance: float | None = None,
        default_chance: float | None = None,
    ) -> "PydanticRandom":
        """Configure bounds on types. Returns `self` so chainable with constructor."""
        if numeric_min is not None:
            self.numeric_min = numeric_min
        if numeric_max is not None:
            self.numeric_max = numeric_max
        if min_str_length is not None:
            self.min_str_length = min_str_length
        if max_str_length is not None:
            self.max_str_length = max_str_length
        if max_sequence_length is not None:
            self.max_sequence_length = max_sequence_length
        if null_chance is not None:
            self.null_chance = null_chance
        if default_chance is not None:
            self.default_chance = default_chance
        return self

    def generate(self, type_: Type[T]) -> T:
        """Generate a new, randomized instance of this type.

        NOTE: We only support ascii string variants at this time.
        """
        data = {}
        logger.debug("Generating instance for model %s", type_.__name__)
        for field_name, model_field in type_.model_fields.items():
            if model_field.annotation is None:
                raise ValueError(f"{field_name} has no annotation, cannot proceed")
            if not model_field.is_required():
                if self.rng.random() < self.default_chance:
                    logger.debug("Skipping optional field %s", field_name)
                    continue
            value = self._gen_value(
                field_name=field_name,
                annotation=model_field.annotation,
                metadata=model_field.metadata,
            )
            logger.debug("Field %s generated value: %s", field_name, value)
            data[field_name] = value
        instance = type_.model_validate(data)
        logger.info("Generated instance of %s", type_.__name__)
        return instance

    def _gen_value(
        self,
        field_name: str,
        annotation: type,
        metadata: list[Any],
    ) -> Any:
        origin = get_origin(annotation)
        args = get_args(annotation)

        if annotation is bool:
            return self._gen_bool(field_name=field_name)
        elif annotation is int:
            return self._gen_numeric(
                field_name=field_name, metadata=metadata, make_int=True
            )
        elif annotation is float:
            return self._gen_numeric(
                field_name=field_name, metadata=metadata, make_int=False
            )
        elif annotation is str:
            return self._gen_textual(
                field_name=field_name, metadata=metadata, make_bytes=False
            )
        elif annotation is bytes:
            return self._gen_textual(
                field_name=field_name, metadata=metadata, make_bytes=True
            )
        elif annotation is date:
            return self._gen_date(field_name=field_name)
        elif annotation is time:
            return self._gen_time(field_name=field_name)
        elif annotation is datetime:
            v1, v2 = (
                self._gen_date(field_name=field_name),
                self._gen_time(field_name=field_name),
            )
            return datetime(v1.year, v1.month, v1.day, v2.hour, v2.minute, v2.second)
        elif origin in (Union, types.UnionType):
            non_none_args = [a for a in args if a is not type(None)]
            chosen_type = self.rng.choice(non_none_args)
            return self._gen_value(
                field_name=field_name,
                annotation=chosen_type,
                metadata=metadata,
            )
        elif origin is Literal:
            return self.rng.choice(args)
        elif origin is list:
            (elem_type,) = args or (str,)
            return [
                self._gen_value(
                    field_name=field_name, annotation=elem_type, metadata=metadata
                )
                for _ in range(self.rng.randint(1, self.max_sequence_length))
            ]
        elif origin is set:
            (elem_type,) = args or (str,)
            return {
                self._gen_value(
                    field_name=field_name, annotation=elem_type, metadata=metadata
                )
                for _ in range(self.rng.randint(1, self.max_sequence_length))
            }
        elif origin is frozenset:
            (elem_type,) = args or (str,)
            return frozenset(
                self._gen_value(
                    field_name=field_name, annotation=elem_type, metadata=metadata
                )
                for _ in range(self.rng.randint(1, self.max_sequence_length))
            )
        elif origin is dict:
            key_type, val_type = args or (str, str)
            return {
                self._gen_value(
                    field_name=field_name, annotation=key_type, metadata=metadata
                ): self._gen_value(
                    field_name=field_name, annotation=val_type, metadata=metadata
                )
                for _ in range(self.rng.randint(1, self.max_sequence_length))
            }
        elif origin is tuple:
            if len(args) == 2 and args[1] is Ellipsis:
                (elem_type, _) = args
                return tuple(
                    self._gen_value(
                        field_name=field_name, annotation=elem_type, metadata=metadata
                    )
                    for _ in range(self.rng.randint(1, self.max_sequence_length))
                )
            return tuple(
                self._gen_value(field_name=field_name, annotation=t, metadata=metadata)
                for t in args
            )
        elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return self.generate(annotation)
        else:
            logger.warning("Unhandled type: %s", annotation)
            return None

    def _gen_bool(self, field_name: str) -> bool:
        v = self.rng.random() > 0.5
        logger.debug("Generated bool: %s=%s", field_name, v)
        return v

    def _gen_numeric(
        self,
        field_name: str,
        metadata: MetadataList | None,
        make_int: bool,
    ) -> float | int:
        metadata = sorted(metadata, key=str) if metadata else []
        low, high = self.numeric_min, self.numeric_max
        for m in metadata:
            if isinstance(m, Ge) and isinstance(m.ge, (int, float)):
                if m.ge >= high:
                    raise ValueError(
                        f"Ge value ({m.ge}) cannot be greater than high bound ({high}) for {field_name}"
                    )
                low = int(m.ge)
            elif isinstance(m, Gt) and isinstance(m.gt, (int, float)):
                if m.gt > high + 1:
                    raise ValueError(
                        f"Gt value ({m.gt}) cannot be greater than high bound ({high + 1}) for {field_name}"
                    )
                low = m.gt + 1
            elif isinstance(m, Le) and isinstance(m.le, (int, float)):
                if m.le <= low:
                    raise ValueError(
                        f"Le value ({m.le}) cannot be less than than low bound ({low}) for {field_name}"
                    )
                high = m.le
            elif isinstance(m, Lt) and isinstance(m.lt, (int, float)):
                if m.lt < low - 1:
                    raise ValueError(
                        f"Lt value ({m.lt}) cannot be less than than low bound ({low - 1}) for {field_name}"
                    )
                high = m.lt - 1
            elif isinstance(m, MultipleOf) and isinstance(m.multiple_of, int):
                # this needs to be last due to requiring bounds,
                # the sort at the top ensures this
                x = m.multiple_of
                start = (int(low) + x - 1) // x
                end = int(high // x)
                if start > end:
                    raise ValueError(f"No multiples of {x} in range {low}–{high}")
                v = self.rng.randint(start, end) * x
                if make_int:
                    return int(v)
                return v
            else:
                raise ValueError(
                    f"unexpected metadata for {field_name} (dtype:{'int' if make_int else 'float'}): {m}. Currently supported metadata fields for int are: Ge, Gt, Le, Lt, MultipleOf -- we do not support AllowInfNan."
                )
        v = self.rng.uniform(low, high)
        if make_int:
            v = int(v)
        logger.debug("Generated numeric: %s=%s", field_name, v)
        return v

    def _gen_textual(
        self, field_name: str, metadata: MetadataList | None, make_bytes: bool
    ) -> str | bytes:
        metadata = sorted(metadata, key=str) if metadata else []
        low, high = self.min_str_length, self.max_str_length
        for m in metadata:
            if isinstance(m, MinLen):
                if m.min_length > high:
                    raise ValueError(
                        f"new min_length ({m.min_length}) cannot be greater than current high bound: {high}"
                    )
                low = m.min_length
            elif isinstance(m, MaxLen):
                if m.max_length < low:
                    raise ValueError(
                        f"new max_length ({m.max_length}) cannot be less than than current low bound: {low}"
                    )
                high = m.max_length
            else:
                raise ValueError(
                    f"unexpected metadata for {field_name} (dtype:string): {m}. Currently supported metadata is: MinLen, MaxLen. We do not support Pattern."
                )

        length = self.rng.randint(low, high)
        if make_bytes:
            v = bytes(self.rng.getrandbits(8) for _ in range(length))
            logger.debug("Generated bytes: %s=%s", field_name, v)
            return v
        v = "".join(self.rng.choices(CHARACTERS, k=length))
        logger.debug("Generated string: %s=%s", field_name, v)
        return v

    def _gen_date(self, field_name: str) -> date:
        y = self.rng.randint(MIN_YEAR, MAX_YEAR)
        m = self.rng.randint(MIN_MONTH, MAX_MONTH)
        if m in {4, 6, 9, 11}:
            d = self.rng.randint(MIN_DAY, 30)
        elif m == 2:
            d = self.rng.randint(MIN_DAY, 29 if y % 4 == 0 else 28)
        else:
            d = self.rng.randint(MIN_DAY, MAX_DAY)
        v = date(y, m, d)
        logger.debug("Generated date: %s=%s", field_name, v)
        return v

    def _gen_time(self, field_name: str) -> time:
        h = self.rng.randint(MIN_HOUR, MAX_HOUR)
        m = self.rng.randint(MIN_MINUTE, MAX_MINUTE)
        s = self.rng.randint(MIN_SECOND, MAX_SECOND)
        v = time(h, m, s)
        logger.debug("Generated time: %s=%s", field_name, v)
        return v
