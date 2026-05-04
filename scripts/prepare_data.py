import polars as pl
import os
import io
import math

def scale_dataset(input_path: str, output_path: str, target_size_mb: int):
    # Detect format based on extension
    if input_path.endswith(".parquet"):
        df = pl.read_parquet(input_path)
    else:
        df = pl.read_csv(input_path, null_values=["NA"], infer_schema_length=10000)
    
    # Accurate estimation: measure bytes-per-row in the TARGET format
    # Using a larger sample for more stable estimation
    sample_n = min(20000, len(df))
    test_buf = io.BytesIO()
    if output_path.endswith(".parquet"):
        df.head(sample_n).write_parquet(test_buf)
    else:
        df.head(sample_n).write_csv(test_buf)
    
    bytes_per_row = len(test_buf.getvalue()) / sample_n
    
    # Use math.ceil and a 2% buffer to strictly guarantee "greater than" target
    target_rows = int(math.ceil((target_size_mb * 1024 * 1024) / bytes_per_row) * 1.02)
    
    print(f"Target: >{target_size_mb}MB. Estimated rows needed (with 2% buffer): {target_rows:,}")
    
    ratio = target_rows / len(df)
    
    if ratio <= 1.0:
        df_final = df.head(target_rows)
    else:
        full_repeats = int(ratio)
        remainder_rows = target_rows - (len(df) * full_repeats)
        
        parts = [df] * full_repeats
        if remainder_rows > 0:
            parts.append(df.head(remainder_rows))
        
        df_final = pl.concat(parts)
    
    if output_path.endswith(".parquet"):
        df_final.write_parquet(output_path)
    else:
        df_final.write_csv(output_path)
        
    actual_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Done: {actual_size:.2f} MB ({len(df_final):,} rows)")

if __name__ == "__main__":
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
    
    base = os.path.join(PROJECT_ROOT, "data/sinan_dengue_sample_2024.csv")
    data_dir = os.path.join(PROJECT_ROOT, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    if not os.path.exists(base):
        print(f"Error: Base file {base} not found.")
    else:
        # Generate the requested CSV datasets, ensuring they are strictly over the target
        scale_dataset(base, os.path.join(data_dir, "dataset_500mb.csv"), 500)
        scale_dataset(base, os.path.join(data_dir, "dataset_1gb.csv"), 1000)
        scale_dataset(base, os.path.join(data_dir, "dataset_2gb.csv"), 2000)
