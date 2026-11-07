# 從 Breeze2（InternVL 多模態）抽出純文字的 Llama 權重，讓 vLLM 用 LlamaForCausalLM 載入。
import json, shutil, sys, glob, os
from safetensors.torch import load_file, save_file
src = glob.glob(os.path.expanduser("~/.cache/huggingface/hub/models--MediaTek-Research--Llama-Breeze2-8B-Instruct/snapshots/*"))[0]
dst = os.path.expanduser("~/BehaviorModeling/models/breeze2-8b-llm")
cfg = json.load(open(f"{src}/config.json"))["llm_config"]
cfg["architectures"] = ["LlamaForCausalLM"]; cfg["torch_dtype"] = "bfloat16"
json.dump(cfg, open(f"{dst}/config.json", "w"), indent=2)
wm = {}
for i, f in enumerate(sorted(glob.glob(f"{src}/model-*.safetensors"))):
    sd = {k[len("language_model."):]: v for k, v in load_file(f).items() if k.startswith("language_model.")}
    if sd:
        name = f"model-{i:05d}.safetensors"; save_file(sd, f"{dst}/{name}", metadata={"format": "pt"})
        wm.update({k: name for k in sd}); print(name, len(sd), flush=True)
json.dump({"metadata": {}, "weight_map": wm}, open(f"{dst}/model.safetensors.index.json", "w"))
for f in ["tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "generation_config.json"]:
    shutil.copy(f"{src}/{f}", dst)
print("tensors:", len(wm))
