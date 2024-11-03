# Schema to TML Web Converter

## Overview
A web application that converts database schema diagrams into ThoughtSpot Modeling Language (TML) files. Built with Streamlit for easy access by non-technical users.

### Purpose
- Automates the conversion of database schemas into TML format
- Provides a simple web interface for users who don't want to use command line
- Generates both table and worksheet TMLs in a single operation

## Project Structure
```
project/
├── app.py              # Main Streamlit web application
├── gen.py              # Core TML generation logic
└── requirements.txt    # Project dependencies
```

## Key Components

### Web Interface (`app.py`)
- Built with Streamlit
- Accepts two inputs:
  - Schema Name (used for naming generated files)
  - Schema Definition (ER diagram text)
- Provides instant preview of generated TMLs
- Offers download of all files in a ZIP

### Generator Module (`gen.py`)
Main function: `generate_tml(erdiagram, worksheet)`
- Inputs:
  - `erdiagram`: ER diagram text
  - `worksheet`: Name for the worksheet/schema
- Processing steps:
  1. Parses ER diagram using `parse_erdiagram_tailored`
  2. Generates individual table TMLs
  3. Generates worksheet TML combining tables and joins
- Returns dictionary of generated files

## Dependencies
```
streamlit    # Web interface
pyyaml      # TML formatting
```

## Key Implementation Details

### Data Flow
1. User inputs schema text and name
2. `process_schema` calls `generate_tml`
3. Results formatted using `yaml.dump`
4. Files bundled into ZIP for download

### File Handling
- All processing happens in memory (no temp files)
- YAML formatting settings:
  - Block style formatting
  - 2-space indentation
  - Preserved key order
  - Unicode support

## Deployment
Currently deployed on Streamlit Cloud
- URL: https://generate-tml-ui.streamlit.app/
- Auto-deploys from main branch https://github.com/db42/generate-tml-ui

## Local Development
1. Clone repository
2. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
3. Run locally:
   ```bash
   streamlit run app.py
   ```

## Notes to Future Self
- Main processing logic is in `gen.py` - check this first for any modifications
- Web interface is intentionally simple to reduce user friction
- YAML formatting is handled during ZIP creation and preview
- No file system operations in core logic - everything stays in memory

## Future Improvements
Potential enhancements:
- [ ] Add validation for schema input
- [ ] Provide template schemas as examples
- [ ] Add error details in UI for invalid schemas
- [ ] Support for different schema formats
- [ ] Add preview of parsed schema before generation
