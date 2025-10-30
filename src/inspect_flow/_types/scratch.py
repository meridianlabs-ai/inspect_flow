from typing import Any, TypedDict
from pydantic import BaseModel


class MyClass(BaseModel):
    val1: int
    val2: float


class MyClassDict(TypedDict):
    val1: int
    val2: float


class WrapperDict(TypedDict):
    it: MyClassDict


def func(input: WrapperDict) -> None:
    print(input["it"])


aclass = MyClass(val1=5, val2=6.0)

WrapperDict(it=aclass)
func({"it": aclass})
