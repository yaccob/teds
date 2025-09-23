# TeDS Presentation

This directory contains a Reveal.js presentation about TeDS (Test-Driven Schema Development) built with AsciiDoctor.

## Structure

```
docs/presentation/
├── index.adoc          # Main presentation source
├── images/            # Images and diagrams
├── assets/            # Additional assets (videos, etc.)
├── css/               # Custom CSS styles
├── README.md          # This file
└── build.sh           # Build script
```

## Requirements

To build the presentation, you need:

- **AsciiDoctor**: `gem install asciidoctor`
- **AsciiDoctor Reveal.js**: `gem install asciidoctor-revealjs`
- **Optional**: PlantUML for diagrams

### Installation

```bash
# Install AsciiDoctor and Reveal.js backend
gem install asciidoctor asciidoctor-revealjs

# For diagrams (optional)
# Install PlantUML: https://plantuml.com/starting
```

## Building the Presentation

### Quick Build

```bash
# Build HTML presentation
asciidoctor-revealjs index.adoc

# This creates index.html - open in browser
```

### Advanced Build

```bash
# Build with custom options
asciidoctor-revealjs \
  -a revealjsdir=https://cdn.jsdelivr.net/npm/reveal.js@4.3.1 \
  -a revealjs_theme=white \
  -a source-highlighter=highlightjs \
  index.adoc

# Build with local Reveal.js (faster, offline)
# First download Reveal.js to ./reveal.js/
asciidoctor-revealjs \
  -a revealjsdir=reveal.js \
  index.adoc
```

### Using the Build Script

```bash
chmod +x build.sh
./build.sh
```

## Presentation Content

### Target Audience
- Developers working with JSON Schema
- DevOps teams implementing schema validation
- Technical leads evaluating schema tools
- API designers and architects

### Duration
45-60 minutes including:
- 35-40 minutes presentation
- 10-15 minutes Q&A and discussion
- 5-10 minutes for demo and interaction

### Key Sections

1. **Introduction** (5 min)
   - Problem statement
   - TeDS overview

2. **Benefits & Value** (10 min)
   - Why use TeDS
   - ROI for organizations

3. **Core Features** (15 min)
   - Test specifications
   - Generation and validation
   - Architecture overview

4. **Getting Started** (10 min)
   - Installation
   - First test example

5. **Advanced Use Cases** (5 min)
   - Complex scenarios
   - CI/CD integration

6. **Demo** (10-15 min)
   - Live demonstration
   - Interactive examples

7. **Q&A** (10-15 min)
   - Questions and discussion

## Customization

### Themes
Available Reveal.js themes:
- `white` (default)
- `black`
- `moon`
- `sky`
- `beige`
- `simple`
- `serif`

Change theme in `index.adoc`:
```
:revealjs_theme: black
```

### Custom CSS
Add custom styles in `css/custom.css` and reference in `index.adoc`:
```
:revealjs_customcss: css/custom.css
```

### Images and Diagrams
- Place images in `images/` directory
- Use PlantUML for diagrams (embedded in AsciiDoc)
- Reference with `:imagesdir: images`

## Tips for Presenting

### Navigation
- **Arrow keys**: Navigate slides
- **Space**: Next slide
- **Esc**: Slide overview
- **F**: Fullscreen
- **S**: Speaker notes (opens new window)

### Speaker Notes
Each slide can have speaker notes:
```asciidoc
[.notes]
--
These are speaker notes that won't appear on the slide
but will show in speaker view (press 'S')
--
```

### Slide Fragments
Create step-by-step reveals:
```asciidoc
[%step]
* First point
* Second point
* Third point
```

## Live Demo Preparation

### Demo Scenarios
The presentation includes placeholders for live demos:

1. **Schema Creation**: Creating a user/product schema with examples
2. **Test Generation**: Generating test specifications
3. **Validation**: Running tests and generating reports

### Demo Setup
Before presenting:
1. Prepare demo schemas in a clean directory
2. Test the demo flow completely
3. Have backup screenshots in `images/demo-*` files
4. Consider recorded demo as backup

## Deployment

### Local Presentation
```bash
# Build and serve locally
asciidoctor-revealjs index.adoc
python -m http.server 8000
# Open http://localhost:8000/index.html
```

### GitHub Pages
1. Build presentation: `./build.sh`
2. Commit `index.html` to repository
3. Enable GitHub Pages on the repository
4. Presentation available at `https://username.github.io/repo/docs/presentation/`

### PDF Export
Reveal.js supports PDF export:
1. Add `?print-pdf` to URL
2. Print to PDF from browser
3. Choose "Save as PDF" with appropriate settings

## Troubleshooting

### Common Issues

**AsciiDoctor not found**
```bash
gem install asciidoctor
```

**Reveal.js backend not found**
```bash
gem install asciidoctor-revealjs
```

**PlantUML diagrams not rendering**
- Install PlantUML: https://plantuml.com/starting
- Ensure Java is installed
- Check PlantUML is in PATH

**Presentation doesn't load properly**
- Check browser console for errors
- Verify Reveal.js CDN URL is accessible
- Try with local Reveal.js installation

### Support
- AsciiDoctor documentation: https://docs.asciidoctor.org/
- Reveal.js documentation: https://revealjs.com/
- AsciiDoctor Reveal.js: https://docs.asciidoctor.org/reveal.js-converter/
