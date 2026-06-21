# D3 Kaggle QLoRA Run Instructions

## Exact Kaggle paths now used by the notebook

The notebook now first looks for these exact files:

```text
/kaggle/input/datasets/aayaehab/finetune-qa/finetune_qa.jsonl
/kaggle/input/datasets/aayaehab/d3-or-final-zero-shot-vs-tuned/d3_or_final_zero_shot_vs_tuned.csv
```

So on Kaggle, make sure both datasets are attached to the notebook and that these paths exist before running all cells.

You can test quickly in a Kaggle code cell:

```python
from pathlib import Path
print(Path('/kaggle/input/datasets/aayaehab/finetune-qa/finetune_qa.jsonl').exists())
print(Path('/kaggle/input/datasets/aayaehab/d3-or-final-zero-shot-vs-tuned/d3_or_final_zero_shot_vs_tuned.csv').exists())
```

Both should print `True`.


Notebook to upload/run:

`notebooks/D3_07_Kaggle_QLoRA_Tuning.ipynb`

This notebook is for making the PEFT/QLoRA row truly available instead of `N/A - adapter not trained`.

## 1. Prepare files before Kaggle
### Ready-made upload ZIP

I also prepared a small upload ZIP here:

```text
kaggle_upload/d3_qlora_kaggle_input.zip
```

Upload this ZIP to Kaggle as a Dataset if you do not want to upload the full project.


You need the tuning file:

`data/tuning/finetune_qa.jsonl`

Best option: upload a small Kaggle Dataset containing at least this structure:

```text
climate_evidence_graphrag_agent/
  data/
    tuning/
      finetune_qa.jsonl
  reports/
    tables/
      d3_or_final_zero_shot_vs_tuned.csv   optional but useful
```

You can also upload the full project folder if it is not too large.

## 2. Create Kaggle notebook

1. Open Kaggle.
2. Create a new Notebook.
3. Import/upload `D3_07_Kaggle_QLoRA_Tuning.ipynb`.
4. In the right-side notebook settings:
   - Accelerator: GPU
   - Internet: On
5. Add your project/tuning Dataset under **Add Input**.

## 3. Run the notebook

Run all cells from top to bottom.

Expected successful outputs:

```text
/kaggle/working/outputs/qlora_adapter/
/kaggle/working/outputs/d3_or_final_zero_shot_vs_tuned.csv
/kaggle/working/outputs/d3_tuning_latency.csv
/kaggle/working/outputs/d3_qlora_generation_details.csv
/kaggle/working/outputs/qlora_training_summary.json
/kaggle/working/d3_qlora_outputs.zip
```

Download:

`/kaggle/working/d3_qlora_outputs.zip`

## 4. Copy outputs back into the local repo

After downloading and unzipping, copy:

```text
outputs/d3_or_final_zero_shot_vs_tuned.csv
```

to:

```text
reports/tables/d3_or_final_zero_shot_vs_tuned.csv
```

Copy:

```text
outputs/d3_tuning_latency.csv
```

to:

```text
reports/tables/d3_tuning_latency.csv
```

Copy:

```text
outputs/qlora_adapter/
```

to either:

```text
models/qlora_adapter/
```

or keep it as:

```text
outputs/qlora_adapter/
```

## 5. After copying back

Rerun locally:

```powershell
cd "D:\BUID\Year 4 2025 - 2026\third semester\Special Topics in AI\Project\climate_evidence_graphrag_agent"
.\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=3600 notebooks\D3_04_Aaya_online_graphrag_adaptation_v2.ipynb
.\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 notebooks\D3_06_Final_Demo_Tuning_Merged_Scope.ipynb
```

Then the QLoRA row should no longer show `N/A - adapter not trained` if Kaggle training completed.

## 6. What to say in the report

If Kaggle training succeeds:

> We trained a small QLoRA/PEFT adapter on 15 evidence-grounded climate QA rows using Kaggle GPU. Because the dataset is small, the adapter is treated as a feasibility and formatting demonstration, not a fully robust domain model. We compare zero-shot and tuned outputs using lightweight answer-overlap/provenance proxy metrics and report latency.

If the tuned score is not better:

> The tuned adapter did not consistently outperform zero-shot because the dataset has only 15 rows. This is expected for a very small PEFT run. The value of this step is to demonstrate a reproducible PEFT/QLoRA pipeline and identify the need for a larger supervised QA set.

Do not claim a strong model improvement unless the generated metrics actually show it.



## Why `/kaggle/working` appears

Kaggle mounts uploaded datasets under `/kaggle/input`, but that folder is read-only. The notebook now copies the two required input files into a writable runtime folder:

```text
/kaggle/working/climate_evidence_graphrag_agent_runtime/data/tuning/finetune_qa.jsonl
/kaggle/working/climate_evidence_graphrag_agent_runtime/reports/tables/d3_or_final_zero_shot_vs_tuned.csv
```

So after the locate/copy cell runs, later cells can safely use normal project-style paths under `/kaggle/working`.

If you see this error:

```text
Missing required tuning file: /kaggle/working/data/tuning/finetune_qa.jsonl
```

then you are probably running the wrong notebook or an old cell. Use:

```text
notebooks/D3_07_Kaggle_QLoRA_Tuning.ipynb
```

not the local validation notebook `D3_06_Final_Demo_Tuning_Merged_Scope.ipynb`.

