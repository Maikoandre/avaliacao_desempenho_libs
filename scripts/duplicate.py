import polars as pl
import os

def scale_dataset(input_path: str, output_path: str, target_size_mb: int = 1000):
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return

    # Load data
    df = pl.read_parquet(input_path)
    
    # Calc multiplier
    current_size_mb = os.path.getsize(input_path) / (1024 * 1024)
    multiplier = int(target_size_mb // current_size_mb) + 1
    
    print(f"Current size: {current_size_mb:.2f} MB. Multiplier: {multiplier}")
    
    # Duplicate
    df_large = pl.concat([df] * multiplier)
    
    # Save
    df_large.write_parquet(output_path)
    
    new_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"New size: {new_size_mb:.2f} MB. Saved to: {output_path}")

if __name__ == "__main__":
    in_file = "data/sinan_dengue_sample_2024.parquet"
    out_file = "data/sinan_dengue_500mb.parquet"
    scale_dataset(in_file, out_file)
