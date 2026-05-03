import polars as pl
import os

def scale_dataset(input_path: str, output_path: str, target_size_mb: int):
    df = pl.read_parquet(input_path)
    current_size_mb = os.path.getsize(input_path) / (1024 * 1024)
    multiplier = int(target_size_mb // current_size_mb) + 1
    
    print(f"Scaling to {target_size_mb}MB (multiplier: {multiplier})...")
    df_large = pl.concat([df] * multiplier)
    df_large.write_parquet(output_path)
    print(f"Done: {os.path.getsize(output_path) / (1024 * 1024):.2f} MB")

if __name__ == "__main__":
    base = "data/sinan_dengue_sample_2024.parquet"
    os.makedirs("data", exist_ok=True)
    
    scale_dataset(base, "data/dataset_500mb.parquet", 500)
    scale_dataset(base, "data/dataset_1gb.parquet", 1000)
    scale_dataset(base, "data/dataset_2gb.parquet", 2000)
