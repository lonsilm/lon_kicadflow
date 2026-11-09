"""Read KiCad S-expressions with byte-safe character spans; never writes designs.

Stdlib only. Spans refer to the decoded Python string, not UTF-8 byte offsets.
Unknown quoted escapes are preserved. This is a syntax reader, not KiCad's
semantic validator or a geometry engine.
"""
from dataclasses import dataclass, field


@dataclass
class Node:
    start: int
    end: int
    value: str | None = None
    children: list = field(default_factory=list)

    @property
    def tag(self):
        return self.children[0].value if self.children else None

    def named(self, tag):
        return [n for n in self.children if n.tag == tag]

    def first(self, tag):
        return next((n for n in self.children if n.tag == tag), None)

    def atom(self, index=1, default=None):
        return self.children[index].value if len(self.children) > index else default


def parse(text):
    """Parse exactly one expression and reject truncated/unbalanced input."""
    n = len(text)
    pos = 0

    def whitespace():
        nonlocal pos
        while pos < n:
            if text[pos].isspace() or text[pos] == '\ufeff':
                pos += 1
            elif text[pos] == ';':
                end = text.find('\n', pos)
                pos = n if end < 0 else end + 1
            else:
                break

    def item():
        nonlocal pos
        whitespace()
        start = pos
        if pos >= n:
            raise ValueError('Unexpected end of S-expression')
        if text[pos] == '(':
            pos += 1
            kids = []
            while True:
                whitespace()
                if pos >= n:
                    raise ValueError(f'Unclosed list at character {start}')
                if text[pos] == ')':
                    pos += 1
                    return Node(start, pos, children=kids)
                kids.append(item())
        if text[pos] == ')':
            raise ValueError(f'Unexpected closing parenthesis at {pos}')
        if text[pos] == '"':
            pos += 1
            chars = []
            escapes = {'n': '\n', 'r': '\r', 't': '\t', '"': '"', '\\': '\\'}
            while pos < n:
                c = text[pos]
                pos += 1
                if c == '"':
                    return Node(start, pos, value=''.join(chars))
                if c == '\\':
                    if pos >= n:
                        raise ValueError('Unfinished string escape')
                    nxt = text[pos]
                    pos += 1
                    chars.append(escapes.get(nxt, '\\' + nxt))
                else:
                    chars.append(c)
            raise ValueError(f'Unclosed string at character {start}')
        while pos < n and not text[pos].isspace() and text[pos] not in '();':
            pos += 1
        if pos == start:
            raise ValueError(f'Invalid token at {pos}')
        return Node(start, pos, value=text[start:pos])

    root = item()
    whitespace()
    if pos != n:
        raise ValueError(f'Trailing expression at {pos}')
    return root


def quote(value):
    """Quote a string for newly created KiCad source text."""
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t') + '"'
