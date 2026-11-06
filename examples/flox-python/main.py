"""Import the generated client without calling an LLM."""

from importlib.metadata import version

import baml_client
from baml_client import b

installed = version("baml-py")
assert hasattr(b, "ExtractResume"), "generated client is missing ExtractResume"
assert baml_client.__version__ == installed, (baml_client.__version__, installed)
print(f"ok baml_py {installed}")
