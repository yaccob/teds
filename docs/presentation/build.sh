#!/bin/bash

# Build script for TeDS Reveal.js presentation
# Requires: asciidoctor, asciidoctor-revealjs

set -e

echo "🎯 Building TeDS Presentation..."

# Check if asciidoctor-revealjs is available
if ! command -v asciidoctor-revealjs &> /dev/null; then
    echo "❌ Error: asciidoctor-revealjs not found"
    echo "💡 Install with: gem install asciidoctor-revealjs"
    exit 1
fi

# Check if asciidoctor-diagram is available
if ! ruby -e "require 'asciidoctor-diagram'" &> /dev/null; then
    echo "❌ Error: asciidoctor-diagram not found"
    echo "💡 Install with: gem install asciidoctor-diagram"
    exit 1
fi

# Check if PlantUML is available (Java-based)
if ! command -v plantuml &> /dev/null && ! command -v java &> /dev/null; then
    echo "⚠️  Warning: PlantUML not found, diagrams will be rendered using online service"
    echo "💡 For offline rendering, install: brew install plantuml (or apt-get install plantuml)"
fi

# Build the presentation
echo "📝 Converting index.adoc to Reveal.js presentation..."

asciidoctor-revealjs \
    -r asciidoctor-diagram \
    -a revealjsdir=https://cdn.jsdelivr.net/npm/reveal.js@4.3.1 \
    -a revealjs_theme=moon \
    -a revealjs_transition=convex \
    -a source-highlighter=highlightjs \
    -a highlightjs-theme=monokai-sublime \
    -a icons=font \
    -a sectids \
    -a linkattrs \
    -a experimental \
    -a allow-uri-read \
    -a diagram-svg-type=inline \
    index.adoc

echo "✅ Presentation built successfully!"
echo "📁 Output: index.html"
echo "🌐 Open in browser or serve with:"
echo "   python -m http.server 8000"
echo "   then visit: http://localhost:8000/index.html"

# Optional: Open in default browser (uncomment if desired)
# if command -v open &> /dev/null; then
#     open index.html
# elif command -v xdg-open &> /dev/null; then
#     xdg-open index.html
# fi

echo ""
echo "📋 Next steps:"
echo "   1. Review the presentation in your browser"
echo "   2. Add images to images/ directory"
echo "   3. Customize content in index.adoc"
echo "   4. Test speaker notes (press 'S' during presentation)"
