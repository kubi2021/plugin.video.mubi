#!/usr/bin/env python3
"""
Schema Validation Script for Mubi JSON files.

Usage:
    python backend/validate_schema.py --path database/v1/films.json --version 1

This script validates films.json or series.json against the JSON schema.
Used in CI workflows to ensure schema compliance before deployment.
"""

import argparse
import json
import sys
import os
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema package not installed. Run: pip install jsonschema")
    sys.exit(1)


def load_schema(version: int) -> dict:
    """Load the JSON schema for a given version."""
    schema_path = Path(__file__).parent / "schemas" / f"v{version}_schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    with open(schema_path, 'r') as f:
        return json.load(f)


def validate_film(film: dict, schema: dict) -> list:
    """
    Validate a single film against the schema.
    Returns a list of error messages (empty if valid).
    """
    errors = []
    validator = jsonschema.Draft7Validator(schema)
    
    for error in validator.iter_errors(film):
        path = " -> ".join(str(p) for p in error.path) if error.path else "(root)"
        errors.append(f"[{path}] {error.message}")
    
    return errors


def validate_database(data: dict, schema: dict, strict: bool = False) -> tuple:
    """
    Validate the entire database file.
    
    Args:
        data: The parsed JSON data (with meta and items)
        schema: The JSON schema for individual films
        strict: If True, fail on first error. If False, collect all errors.
    
    Returns:
        Tuple of (is_valid: bool, errors: list, stats: dict)
    """
    all_errors = []
    stats = {
        "total_items": 0,
        "valid_items": 0,
        "invalid_items": 0
    }
    
    items = data.get("items", [])
    stats["total_items"] = len(items)
    
    for idx, film in enumerate(items):
        errors = validate_film(film, schema)
        
        if errors:
            stats["invalid_items"] += 1
            film_id = film.get("mubi_id", f"index_{idx}")
            film_title = film.get("title", "Unknown")
            
            for error in errors:
                all_errors.append(f"Film {film_id} ({film_title}): {error}")
            
            if strict:
                break
        else:
            stats["valid_items"] += 1
    
    is_valid = len(all_errors) == 0
    return is_valid, all_errors, stats


def main():
    parser = argparse.ArgumentParser(description="Validate Mubi JSON against schema")
    parser.add_argument("--path", required=True, help="Path to films.json or series.json")
    parser.add_argument("--version", type=int, default=1, help="Schema version to validate against")
    parser.add_argument("--strict", action="store_true", help="Fail on first error")
    parser.add_argument("--max-errors", type=int, default=20, help="Maximum errors to display")
    
    args = parser.parse_args()
    
    # Load the JSON file
    if not os.path.exists(args.path):
        print(f"ERROR: File not found: {args.path}")
        sys.exit(1)
    
    print(f"Loading {args.path}...")
    with open(args.path, 'r') as f:
        data = json.load(f)
    
    # Check meta version
    meta = data.get("meta", {})
    file_version = meta.get("version", 1)
    version_label = meta.get("version_label", f"{file_version}.0")
    
    print(f"File version: {file_version} (label: {version_label})")
    print(f"Validating against schema v{args.version}...")
    
    if file_version != args.version:
        print(f"WARNING: File version ({file_version}) differs from requested schema version ({args.version})")
    
    # Load schema and validate
    try:
        schema = load_schema(args.version)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    is_valid, errors, stats = validate_database(data, schema, strict=args.strict)
    
    # Print results
    print(f"\n{'='*60}")
    print(f"VALIDATION RESULTS")
    print(f"{'='*60}")
    print(f"Total items: {stats['total_items']}")
    print(f"Valid items: {stats['valid_items']}")
    print(f"Invalid items: {stats['invalid_items']}")
    
    if errors:
        print(f"\n{'='*60}")
        print(f"ERRORS (showing first {min(len(errors), args.max_errors)}):")
        print(f"{'='*60}")
        for error in errors[:args.max_errors]:
            print(f"  ❌ {error}")
        
        if len(errors) > args.max_errors:
            print(f"\n  ... and {len(errors) - args.max_errors} more errors")
        
        print(f"\n{'='*60}")
        print("VALIDATION FAILED")
        print(f"{'='*60}")
        sys.exit(1)
    else:
        print(f"\n{'='*60}")
        print("✅ VALIDATION PASSED")
        print(f"{'='*60}")
        sys.exit(0)


if __name__ == "__main__":
    main()
