# This script uses the OpenAI Batch API to process multiple input files asynchronously.
# It uploads each file, submits a batch request, and periodically checks for completion.
# Once done, it saves the results to a timestamped output folder.

# Load necessary libraries
import os
import time
import glob
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

# --- SETUP FOLDERS ---
# Create a unique folder for this specific run based on current time
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
run_output_dir = os.path.join("output", f"run_{timestamp}")
os.makedirs(run_output_dir, exist_ok=True)

# Get all jsonl files in your input folder
batch_files = sorted(glob.glob("batch_input/*.jsonl"))

print(f"🚀 Starting run. Results will be saved to: {run_output_dir}")

# --- LOOP THROUGH FILES ---
for file_path in batch_files:
    file_name = os.path.basename(file_path)
    print(f"\n--- Processing: {file_name} ---")

    # Upload File
    uploaded_file = client.files.create(
        file=open(file_path, "rb"),
        purpose="batch"
    )

    # Submit Batch
    batch_request = client.batches.create(
        input_file_id=uploaded_file.id,
        endpoint="/v1/responses",
        completion_window="24h",
        metadata={"description": f"Batch run for {file_name}"}
    )
    
    batch_id = batch_request.id
    print(f"Submitted Batch ID: {batch_id}")

    # --- WAIT FOR COMPLETION ---
    while True:
        batch = client.batches.retrieve(batch_id)
        status = batch.status
        print(f"Status: {status} | Completed: {batch.request_counts.completed}/{batch.request_counts.total}")

        if status in ["completed", "failed", "expired", "cancelled"]:
            print(f"\nBatch ended with status: {status}")
            
            # --- 4. SAVE RESULTS ---
            # If it completed, save the output. If it failed, save the error file if it exists.
            file_to_download = batch.output_file_id or batch.error_file_id
            
            if file_to_download:
                file_response = client.files.content(file_to_download)
                save_path = os.path.join(run_output_dir, f"results_{file_name}")
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(file_response.text)
                print(f"Saved results to: {save_path}")
            else:
                print("No output file generated for this batch.")
            
            break # Move to next file in batch_files
        
        # Wait 60 seconds before checking the status again
        time.sleep(60)

print("\n✅ All batches in the folder have been processed.")