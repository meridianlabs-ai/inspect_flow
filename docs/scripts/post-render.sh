#!/bin/bash

# Post-render script to generate llms-full.txt and individual .html.md files.
# Follows the inspect-ai approach: renders each .qmd to GFM markdown, concatenates
# into llms-full.txt, and places individual .html.md files alongside HTML output.

files=(
    "index"
    "flow_concepts"
    "defaults"
    "matrix"
    "run"
    "store"
    "advanced"
    "reference/index"
    "reference/inspect_flow"
    "reference/inspect_flow.api"
    "reference/flow_config"
    "reference/flow_run"
    "reference/flow_store"
)

if [ "$QUARTO_PROJECT_RENDER_ALL" = "1" ]; then
    llms_full="_site/llms-full.txt"
    rm -f "${llms_full}"
    mv _quarto.yml _quarto.yml.bak
    for file in "${files[@]}"; do
        echo "llms: ${file}.qmd"
        quarto render "${file}.qmd" --to gfm-raw_html --quiet --no-execute
        output_file="${file}.md"
        cat "${output_file}" >> "${llms_full}"
        echo "" >> "${llms_full}"
        mv "${output_file}" "_site/${file}.html.md"
    done
    mv _quarto.yml.bak _quarto.yml
fi
