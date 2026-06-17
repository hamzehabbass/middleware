from jinja2 import Environment, TemplateSyntaxError
from middleware import HTML_TEMPLATE

env = Environment()
try:
    env.parse(HTML_TEMPLATE)
    print('TEMPLATE_OK')
except TemplateSyntaxError as e:
    print('TEMPLATE_SYNTAX_ERROR')
    print(str(e))
    try:
        print('LINE:', e.lineno)
        lines = HTML_TEMPLATE.splitlines()
        start = max(0, e.lineno - 5)
        end = min(len(lines), e.lineno + 5)
        for i in range(start, end):
            print(f"{i+1}: {lines[i]}")
    except Exception:
        pass
