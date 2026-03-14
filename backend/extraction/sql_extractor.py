import re

def extract_sql_entities(code: str) -> dict:
    # Guard against None input
    if code is None:
        return {"tables": [], "columns": [], "foreign_keys": [], "views": []}
    """
    Extract tables, columns, foreign_keys, and views from SQL code.
    This works by using regular expressions on common DDL statements.
    """
    entities = {
        "tables": [],
        "columns": [],
        "foreign_keys": [],
        "views": []
    }

    # Remove block comments (/* ... */)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    # Remove single-line comments (-- ...)
    code = re.sub(r"--.*?\n", "\n", code)

    # Tables: CREATE TABLE [IF NOT EXISTS] table_name
    table_pattern = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s(]+)", 
        re.IGNORECASE
    )
    for match in table_pattern.finditer(code):
        table_name = match.group(1).strip("`\"'")
        entities["tables"].append(table_name)

    # Views: CREATE VIEW [IF NOT EXISTS] view_name
    view_pattern = re.compile(
        r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s(]+)", 
        re.IGNORECASE
    )
    for match in view_pattern.finditer(code):
        view_name = match.group(1).strip("`\"'")
        entities["views"].append(view_name)

    # Process each CREATE TABLE block to extract columns and foreign keys locally
    # We'll split the script by CREATE TABLE to approximate the blocks
    table_blocks = re.split(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?", code, flags=re.IGNORECASE)
    
    for block in table_blocks[1:]: # Skip the first chunk (before any CREATE TABLE)
        # The block starts with "table_name ( ... );" ideally
        # Let's find the closing parenthesis of the CREATE TABLE.
        # This is tricky without a true parser, but we can look for the first semi-colon or robust matching.
        match = re.search(r"^([^\s(]+)\s*\((.*?)\)\s*;", block, re.IGNORECASE | re.DOTALL)
        if match:
            table_name = match.group(1).strip("`\"'")
            table_body = match.group(2)
        else:
            # Fallback if no trailing semicolon is found quickly
            match_no_semi = re.search(r"^([^\s(]+)\s*\((.*)\)", block, re.IGNORECASE | re.DOTALL)
            if match_no_semi:
                table_name = match_no_semi.group(1).strip("`\"'")
                table_body = match_no_semi.group(2)
            else:
                continue
                
        # Now looking inside table_body for columns and foreign keys
        lines = table_body.split(',')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for PRIMARY KEY, UNIQUE, FOREIGN KEY constraints directly
            if re.match(r"^(PRIMARY|UNIQUE)\s+KEY", line, re.IGNORECASE) or \
               re.match(r"^CONSTRAINT", line, re.IGNORECASE):
                # Check if it's a foreign key inline
                fk_match = re.search(r"FOREIGN\s+KEY\s*\([^)]+\)\s*REFERENCES\s+([^\s(]+)\s*\(([^)]+)\)", line, re.IGNORECASE)
                if fk_match:
                    ref_table = fk_match.group(1).strip("`\"'")
                    ref_col = fk_match.group(2).strip("`\"'")
                    entities["foreign_keys"].append(f"{ref_table}.{ref_col}")
                continue
            
            # Check for Foreign key starting word
            fk_match2 = re.match(r"^FOREIGN\s+KEY\s*\([^)]+\)\s*REFERENCES\s+([^\s(]+)\s*\(([^)]+)\)", line, re.IGNORECASE)
            if fk_match2:
                ref_table = fk_match2.group(1).strip("`\"'")
                ref_col = fk_match2.group(2).strip("`\"'")
                entities["foreign_keys"].append(f"{ref_table}.{ref_col}")
                continue
                
            # It's a column definition
            col_match = re.match(r"^([^\s]+)", line)
            if col_match:
                col_name = col_match.group(1).strip("`\"'")
                # format as table.column
                if col_name.upper() not in ["PRIMARY", "UNIQUE", "FOREIGN", "CONSTRAINT", "KEY", "CHECK"]:
                    entities["columns"].append(f"{table_name}.{col_name}")
                    
                # Look for inline REFERENCES
                inline_fk = re.search(r"REFERENCES\s+([^\s(]+)\s*\(([^)]+)\)", line, re.IGNORECASE)
                if inline_fk:
                    ref_table = inline_fk.group(1).strip("`\"'")
                    ref_col = inline_fk.group(2).strip("`\"'")
                    entities["foreign_keys"].append(f"{ref_table}.{ref_col}")

    # Remove duplicates
    entities["tables"] = list(set(entities["tables"]))
    entities["columns"] = list(set(entities["columns"]))
    entities["foreign_keys"] = list(set(entities["foreign_keys"]))
    entities["views"] = list(set(entities["views"]))
    
    return entities
