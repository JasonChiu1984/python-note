"""在 CPython 3.14 或更新版本執行 3.14 語言與標準函式庫示範。"""

import annotationlib
import asyncio
import operator
import warnings
from html import escape
from string.templatelib import Template


def render_text_template(template: Template) -> str:
    """將插值放入 HTML 文字內容，不用於屬性、URL 或 script。"""
    parts = [template.strings[0]]
    for field, tail in zip(template.interpolations, template.strings[1:], strict=True):
        if field.conversion is not None or field.format_spec:
            raise ValueError("此教學 renderer 只接受無轉換和格式規格的插值")
        parts.extend((escape(str(field.value)), tail))
    return "".join(parts)


def template_string() -> None:
    name = "<AHU01>"
    template = t"<p>{name}</p>"
    assert isinstance(template, Template)
    assert template.interpolations[0].value == name
    assert render_text_template(template) == "<p>&lt;AHU01&gt;</p>"


def deferred_annotations() -> None:
    def parse() -> Reading:
        return Reading()

    assert annotationlib.get_annotations(parse, format=annotationlib.Format.STRING) == {
        "return": "Reading"
    }
    pending = annotationlib.get_annotations(parse, format=annotationlib.Format.FORWARDREF)
    assert isinstance(pending["return"], annotationlib.ForwardRef)

    class Reading:
        pass

    assert annotationlib.get_annotations(parse)["return"] is Reading
    assert isinstance(parse(), Reading)


def exception_syntax() -> None:
    try:
        raise ValueError("bad reading")
    except ValueError, TypeError:
        pass
    else:
        raise AssertionError("多種例外捕捉應匹配 ValueError")

    source = "def cleanup():\n    try:\n        raise ValueError\n    finally:\n        return 0\n"
    with warnings.catch_warnings(record=True) as messages:
        warnings.simplefilter("always", SyntaxWarning)
        compile(source, "<finally demo>", "exec")
    assert any(message.category is SyntaxWarning for message in messages)


def zstandard_round_trip() -> None:
    from compression import zstd

    payload = b"AHU01,T10,24.5\n" * 32
    compressed = zstd.compress(payload)
    assert zstd.decompress(compressed) == payload


def strict_map_and_none() -> None:
    assert list(map(operator.add, [1, 2], [10, 20], strict=True)) == [11, 22]
    try:
        list(map(operator.add, [1], [10, 20], strict=True))
    except ValueError:
        pass
    else:
        raise AssertionError("長度不等的輸入應回報 ValueError")
    assert list(filter(operator.is_not_none, [0, None, 24.5])) == [0, 24.5]


def async_introspection() -> None:
    async def inspect_task() -> None:
        running = asyncio.current_task()
        assert running is not None
        graph = asyncio.capture_call_graph()
        assert graph is not None and graph.future is running

    asyncio.run(inspect_task())


if __name__ == "__main__":
    for demo in (
        template_string,
        deferred_annotations,
        exception_syntax,
        zstandard_round_trip,
        strict_map_and_none,
        async_introspection,
    ):
        try:
            demo()
        except ModuleNotFoundError as exc:
            if demo is not zstandard_round_trip or exc.name != "_zstd":
                raise
            print("SKIP zstandard_round_trip: CPython 建置缺少 _zstd")
        else:
            print(f"PASS {demo.__name__}")
