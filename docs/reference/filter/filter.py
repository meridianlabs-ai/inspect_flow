import subprocess
from typing import cast

from griffe import Module
import griffe
import panflute as pf  # type: ignore

from parse import DocParseOptions, parse_docs
from render import render_docs
from commands import make_command_docs


def main():
    # create options
    module = cast(Module, griffe.load("inspect_flow"))
    sha = (
        subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True)
        .stdout.decode()
        .strip()
    )
    source_url = f"https://github.com/meridianlabs-ai/inspect_flow/blob/{sha}/src"
    parse_options = DocParseOptions(module=module, source_url=source_url)

    # python api -- convert h3 into reference
    def python_api(elem: pf.Element, doc: pf.Doc):
        if isinstance(elem, pf.Header) and elem.level == 3:
            title = pf.stringify(doc.metadata["title"])
            if title.startswith("inspect_flow"):
                if title.startswith("inspect_flow."):
                    # get target object
                    module = title.removeprefix("inspect_flow.")
                    object = f"{module}.{pf.stringify(elem.content)}"
                else:
                    object = pf.stringify(elem.content)

                # parse docs
                docs = parse_docs(object, parse_options)

                # render docs
                return render_docs(elem, docs)
            
    # click cli
    def click_cli(elem: pf.Element, doc: pf.Doc):
        if isinstance(elem, pf.Doc):
            title = pf.stringify(doc.metadata["title"])
            if title.startswith("flow "):
                command = title.split(" ")[1]
                docs = "\n".join(list(make_command_docs(command)))
                doc.content.append(pf.RawBlock(docs, "markdown"))

    return pf.run_filters([python_api, click_cli])


if __name__ == "__main__":
    main()
