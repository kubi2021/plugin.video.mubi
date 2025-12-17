import gzip
import hashlib
import json
import shutil
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_repo(input_file='films.json'):
    if not os.path.exists(input_file):
        logger.error(f"Input file {input_file} not found.")
        return

    # 1. Compress to .gz
    gz_file = f"{input_file}.gz"
    logger.info(f"Compressing {input_file} to {gz_file}...")
    with open(input_file, 'rb') as f_in:
        with gzip.open(gz_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    # 2. Calculate MD5 of the .gz file
    logger.info(f"Calculating MD5 for {gz_file}...")
    with open(gz_file, "rb") as f:
        file_hash = hashlib.md5()
        while chunk := f.read(8192):
            file_hash.update(chunk)
    
    md5_digest = file_hash.hexdigest()
    
    # 3. Save MD5 to .md5 file
    md5_file = f"{gz_file}.md5"
    with open(md5_file, "w") as f:
        f.write(md5_digest)
    
    logger.info(f"Generated {md5_file}: {md5_digest}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate GZIP and MD5 for repository files")
    parser.add_argument('--file', default='films.json', help="Input JSON file to process")
    
    args = parser.parse_args()
    generate_repo(args.file)
