# app.py
import streamlit as st
import tempfile
import zipfile
import io
import os
import yaml
from gen import generate_tml  # Import your function

def process_schema(schema_text, schema_name):
    """
    Wrapper function that calls your existing generator
    
    Args:
        schema_text (str): The input schema text
        schema_name (str): Name of the schema
    Returns:
        dict: Dictionary of filename: content pairs
    """
    try:
        # Call your function directly with the text and name
        result_files = generate_tml(schema_text, schema_name)
        print(f"Generated TML to {result_files.keys()}")
        
        # If generate_tml returns a dict, return it directly
        if isinstance(result_files, dict):
            return result_files
        else:
            # If generate_tml creates files on disk, read them back
            output_files = {}
            # Assuming files are created in the current directory
            # Adjust the directory path if your function creates files elsewhere
            current_dir = os.getcwd()
            for filename in os.listdir(current_dir):
                if filename.startswith(f"{schema_name}_"):  # Adjust pattern as needed
                    with open(os.path.join(current_dir, filename), 'r') as f:
                        output_files[filename] = f.read()
            return output_files
                
    except Exception as e:
        raise Exception(f"Error in generate_tml: {str(e)}")

def create_zip_file(files_dict):
    """
    Create a zip file from dictionary of files
    
    Args:
        files_dict (dict): Dictionary of filename: content pairs
    Returns:
        bytes: Zip file content as bytes
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in files_dict.items():
            if isinstance(content, str):
                try:
                    content = yaml.safe_load(content)
                except yaml.YAMLError:
                    pass  # Keep original content if it's not valid YAML

            # Dump the content as formatted YAML
            formatted_content = yaml.dump(content, sort_keys=False, indent=2)

            # Convert to bytes and write to zip
            zip_file.writestr(filename, formatted_content.encode('utf-8'))
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def main():
    st.set_page_config(
        page_title="Schema Processor",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("Schema Processing Tool")
    st.markdown("""
        This tool processes database schema and generates multiple output files.
        
        1. Enter a name for your schema
        2. Paste your schema in the text area
        3. Click 'Process Schema'
        4. Download the generated files
    """)
    
    # Create two columns for schema name and spacer
    col1, col2 = st.columns([1, 2])
    
    # Schema name input in the first column
    with col1:
        schema_name = st.text_input(
            "Schema Name",
            placeholder="my_schema",
            help="Enter a name for your schema (used for generated files)"
        )
    
    # Input text area for schema (full width)
    schema_input = st.text_area(
        "Paste your schema here",
        height=300,
        placeholder="CREATE TABLE..."
    )
    
    if st.button("Process Schema", type="primary"):
        # Validate inputs
        if not schema_name.strip():
            st.error("Please enter a schema name")
            return
            
        if not schema_input.strip():
            st.error("Please enter a schema to process")
            return
            
        try:
            with st.spinner("Processing schema..."):
                # Process the schema
                processed_files = process_schema(schema_input, schema_name)
                
                # Create zip file
                zip_content = create_zip_file(processed_files)
                
                # Offer download button
                st.download_button(
                    label="Download Processed Files",
                    data=zip_content,
                    file_name=f"{schema_name}_processed.zip",
                    mime="application/zip"
                )
                
                # Show success message
                st.success("Schema processed successfully! Click above to download the files.")
                
                # Preview section
                with st.expander("Preview Generated Files"):
                    for filename, content in processed_files.items():
                         # Format content as YAML for preview
                        if not isinstance(content, str):
                            formatted_content = yaml.dump(
                                content,
                                sort_keys=False,
                                indent=2,
                            )
                        else:
                            # If content is already a string, try to parse and re-format it
                            try:
                                parsed_content = yaml.safe_load(content)
                                formatted_content = yaml.dump(
                                    parsed_content,
                                    sort_keys=False,
                                    indent=2,
                                )
                            except yaml.YAMLError:
                                formatted_content = content
                        
                        st.text_area(
                            f"Preview of {filename}",
                            value=formatted_content,
                            height=150
                        )
                        
        except Exception as e:
            st.error(f"An error occurred while processing: {str(e)}")
            
if __name__ == "__main__":
    main()