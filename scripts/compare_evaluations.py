import csv
import sys
import os

def load_csv(path):
    data = {}
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return {}
    
    with open(path, 'r', encoding='utf-8-sig') as f:
        # Check first line to detect format
        first_line = f.readline()
        f.seek(0)
        
        if first_line.startswith("Metric,Film_1"):
            # Transposed Format
            print(f"  Detected Transposed CSV: {path}")
            reader = csv.reader(f)
            rows = list(reader)
            
            # Find mubi_id row
            mubi_id_row = None
            for r in rows:
                if r[0] == 'mubi_id':
                    mubi_id_row = r
                    break
            
            if not mubi_id_row:
                print("  Could not find mubi_id row in transposed file")
                return {}
            
            # Initialize objects with mubi_id
            # mubi_id_row[1:] are the IDs for Film_1, Film_2, etc.
            # We map col_index -> mubi_id
            col_map = {}
            for i, mid in enumerate(mubi_id_row[1:], start=1):
                if mid:
                    data[mid] = {'mubi_id': mid}
                    col_map[i] = mid
            
            # Populate other fields
            for r in rows:
                key = r[0]
                if key == 'Metric' or key == 'mubi_id': 
                    continue
                
                # Normalize keys if needed
                if key == 'tmdb_id' or key == 'match_id':
                    key = 'tmdb_id' # standardized
                
                for i, val in enumerate(r[1:], start=1):
                    if i in col_map:
                        mid = col_map[i]
                        data[mid][key] = val
                        
        else:
            # Standard Format
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print(f"  Empty CSV: {path}")
                return {}
            
            # Detect ID column
            id_col = 'mubi_id'
            if 'mubi_id' not in reader.fieldnames:
                # Try alternatives
                candidates = [c for c in reader.fieldnames if 'mubi' in c.lower() and 'id' in c.lower()]
                if candidates:
                    id_col = candidates[0]
                else:
                    print(f"  ID Column not found in keys: {reader.fieldnames}")
                    return {}
                    
            for row in reader:
                mid = row[id_col]
                data[mid] = row
                # clean up tmdb_id if present
                if 'tmdb_id' in row:
                    pass # already there
                elif 'match_id' in row:
                    data[mid]['tmdb_id'] = row['match_id']

    return data

def compare(old_path, new_path):
    print(f"Comparing:")
    print(f"  Old: {old_path}")
    print(f"  New: {new_path}")
    
    old_data = load_csv(old_path)
    new_data = load_csv(new_path)
    
    if not old_data or not new_data:
        return

    stats = {
        "fixed": [],      # Old: No Match -> New: Match
        "regressed": [],  # Old: Match -> New: No Match
        "changed": [],    # Match ID changed
        "still_failed": [], # Both No Match
        "new_items": [],  # Added to dataset
        "removed_items": [], # Removed from dataset
        "stable": []      # Match ID identical
    }
    
    # Analyze
    all_ids = set(old_data.keys()) | set(new_data.keys())
    
    for mid in all_ids:
        old = old_data.get(mid)
        new = new_data.get(mid)
        
        if not old:
            stats["new_items"].append(mid)
            continue
        if not new:
            stats["removed_items"].append(mid)
            continue
            
        old_tmdb = old.get("tmdb_id")
        new_tmdb = new.get("tmdb_id")
        
        old_success = old_tmdb and old_tmdb != "NO MATCH"
        new_success = new_tmdb and new_tmdb != "NO MATCH"
        
        if not old_success and new_success:
            stats["fixed"].append((mid, old.get("mubi_title"), new_tmdb))
        elif old_success and not new_success:
            stats["regressed"].append((mid, old.get("mubi_title"), old_tmdb))
        elif not old_success and not new_success:
            stats["still_failed"].append((mid, new.get("mubi_title")))
        elif old_success and new_success:
            if old_tmdb != new_tmdb:
                stats["changed"].append((mid, new.get("mubi_title"), old_tmdb, new_tmdb))
            else:
                stats["stable"].append(mid)
                
    # Report
    print(f"\nResults Breakdown:")
    print(f"  Total Items Analyzed: {len(all_ids)}")
    print(f"  Start Failures: {len([x for x in old_data.values() if x.get('tmdb_id') == 'NO MATCH'])}")
    print(f"  End Failures:   {len([x for x in new_data.values() if x.get('tmdb_id') == 'NO MATCH'])}")
    print(f"  Stable Matches: {len(stats['stable'])}")
    
    print(f"\nIMPROVEMENTS (Fixed: {len(stats['fixed'])}):")
    for item in stats["fixed"][:10]: # Sample
        print(f"  - [{item[0]}] {item[1]} -> Found {item[2]}")
    if len(stats["fixed"]) > 10: print(f"    ... and {len(stats['fixed'])-10} more.")

    print(f"\nREGRESSIONS (Broken: {len(stats['regressed'])}):")
    for item in stats["regressed"]:
        print(f"  - [{item[0]}] {item[1]} (Was {item[2]} -> Now NO MATCH)")

    print(f"\nCHANGED MATCHES ({len(stats['changed'])}):")
    for item in stats["changed"]:
        print(f"  - [{item[0]}] {item[1]} (Was {item[2]} -> Now {item[3]})")
        
    print(f"\nREMAINING FAILURES ({len(stats['still_failed'])}):")
    for item in stats["still_failed"]:
        print(f"  - [{item[0]}] {item[1]}")

if __name__ == "__main__":
    compare("evaluation_results Run 1.csv", "evaluation_results.csv")
